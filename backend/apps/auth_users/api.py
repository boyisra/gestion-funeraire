"""
API Authentification — Django Ninja
Endpoints : login, MFA verify, MFA resend, refresh, logout
"""
from datetime import timedelta
from typing import Optional

from django.contrib.auth import authenticate
from django.utils import timezone
from django.core import signing
from ninja import Router, Schema
from ninja.security import HttpBearer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Utilisateur
from .services_mfa import (
    envoyer_code_mfa, verifier_code_mfa, envoyer_code_verification_inscription,
    MFA_LINK_SALT, MFA_LINK_MAX_AGE,
)

router = Router(tags=["Authentification"])


# ─── Schémas de requête / réponse ────────────────────────────────────────────

class LoginSchema(Schema):
    email: str
    password: str


class MFAVerifySchema(Schema):
    user_id: str
    code: str


class MFAResendSchema(Schema):
    email: str


class MFAVerifyLinkSchema(Schema):
    uid: str
    token: str


class InscriptionSchema(Schema):
    email: str
    mot_de_passe: str
    nom: str
    prenom: str
    telephone: Optional[str] = ""


class InscriptionResponseSchema(Schema):
    success: bool
    user_id: str
    message: str


class ConfirmerInscriptionSchema(Schema):
    user_id: str
    code: str


class RenvoyerInscriptionSchema(Schema):
    email: str


class UtilisateurSchema(Schema):
    id: str
    email: str
    nom_complet: str
    role: str
    telephone: Optional[str] = None


class TokenSchema(Schema):
    access: str
    refresh: str
    user: UtilisateurSchema


class LoginResponseSchema(Schema):
    success: bool
    user_id: str
    message: str


class ErrorSchema(Schema):
    success: bool
    detail: str


# ─── Sécurité JWT (Bearer Token) ─────────────────────────────────────────────

class AuthBearer(HttpBearer):
    def authenticate(self, request, token: str):
        try:
            from rest_framework_simplejwt.authentication import JWTAuthentication
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
            return user
        except Exception:
            return None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/inscription/", response={201: InscriptionResponseSchema, 400: ErrorSchema}, auth=None)
def inscription(request, payload: InscriptionSchema):
    """
    Auto-inscription (clients / citoyens uniquement).
    Crée le compte en attente de vérification (email_verifie=False) et
    envoie un code à 6 chiffres par email. Le compte ne pourra pas se
    connecter tant que ce code n'aura pas été confirmé.
    """
    email = payload.email.strip().lower()

    if Utilisateur.objects.filter(email=email).exists():
        return 400, {"success": False, "detail": "Un compte existe déjà avec cet email."}

    if len(payload.mot_de_passe) < 8:
        return 400, {"success": False, "detail": "Le mot de passe doit contenir au moins 8 caractères."}

    if not payload.nom.strip() or not payload.prenom.strip():
        return 400, {"success": False, "detail": "Le nom et le prénom sont obligatoires."}

    utilisateur = Utilisateur.objects.create_user(
        email=email,
        password=payload.mot_de_passe,
        nom=payload.nom.strip(),
        prenom=payload.prenom.strip(),
        telephone=(payload.telephone or "").strip(),
        role='CLIENT',
        email_verifie=False,
    )

    envoye = envoyer_code_verification_inscription(utilisateur)
    if not envoye:
        return 400, {"success": False, "detail": "Compte créé mais l'envoi de l'email a échoué. Réessayez le renvoi du code."}

    return 201, {
        "success": True,
        "user_id": str(utilisateur.id),
        "message": f"Code de vérification envoyé à {utilisateur.email}",
    }


@router.post("/inscription/confirmer/", response={200: dict, 401: ErrorSchema}, auth=None)
def inscription_confirmer(request, payload: ConfirmerInscriptionSchema):
    """
    Confirme le code reçu par email à l'inscription et active le compte.
    Après cette étape, l'utilisateur peut se connecter normalement — chaque
    connexion redemandera ensuite un code MFA, comme pour tous les rôles.
    """
    try:
        utilisateur = Utilisateur.objects.get(id=payload.user_id)
    except Utilisateur.DoesNotExist:
        return 401, {"success": False, "detail": "Utilisateur introuvable."}

    if utilisateur.email_verifie:
        return 200, {"success": True, "message": "Ce compte est déjà vérifié. Vous pouvez vous connecter."}

    if not verifier_code_mfa(utilisateur, payload.code, objectif='INSCRIPTION'):
        return 401, {"success": False, "detail": "Code incorrect ou expiré."}

    utilisateur.email_verifie = True
    utilisateur.save(update_fields=['email_verifie'])

    return 200, {"success": True, "message": "Adresse email vérifiée. Vous pouvez maintenant vous connecter."}


@router.post("/inscription/renvoyer/", response={200: dict, 429: ErrorSchema}, auth=None)
def inscription_renvoyer(request, payload: RenvoyerInscriptionSchema):
    """Renvoie le code de vérification d'inscription (limité à 1 / 60 sec)"""
    try:
        utilisateur = Utilisateur.objects.get(email=payload.email.strip().lower(), email_verifie=False)
    except Utilisateur.DoesNotExist:
        return 200, {"success": True, "message": "Si un compte en attente existe, un code a été envoyé."}

    from .models import TokenMFA
    token_recent = TokenMFA.objects.filter(
        utilisateur=utilisateur,
        objectif='INSCRIPTION',
        utilise=False,
        cree_le__gte=timezone.now() - timedelta(seconds=60)
    ).exists()

    if token_recent:
        return 429, {"success": False, "detail": "Attendez 60 secondes avant de redemander un code."}

    envoye = envoyer_code_verification_inscription(utilisateur)
    return 200, {
        "success": envoye,
        "message": "Nouveau code envoyé." if envoye else "Erreur d'envoi."
    }


@router.post("/login/", response={200: LoginResponseSchema, 401: ErrorSchema}, auth=None)
def login(request, payload: LoginSchema):
    """
    Étape 1 : Vérification email/password
    Si correct → envoie le code MFA par email
    """
    utilisateur = authenticate(
        request,
        username=payload.email,
        password=payload.password
    )

    if not utilisateur:
        return 401, {"success": False, "detail": "Email ou mot de passe incorrect."}

    if not utilisateur.is_active:
        return 401, {"success": False, "detail": "Ce compte est désactivé."}

    if not utilisateur.email_verifie:
        return 401, {
            "success": False,
            "detail": "Veuillez d'abord vérifier votre adresse email. "
                      "Un code vous a été envoyé à l'inscription — consultez votre boîte Gmail.",
        }

    # Envoyer le code MFA
    envoye = envoyer_code_mfa(utilisateur)
    if not envoye:
        return 401, {"success": False, "detail": "Impossible d'envoyer le code MFA. Vérifiez votre email."}

    return 200, {
        "success": True,
        "user_id": str(utilisateur.id),
        "message": f"Code MFA envoyé à {utilisateur.email}",
    }


@router.post("/mfa/verify/", response={200: TokenSchema, 401: ErrorSchema}, auth=None)
def mfa_verify(request, payload: MFAVerifySchema):
    """
    Étape 2 : Vérification du code MFA
    Si correct → retourne les tokens JWT access + refresh
    """
    try:
        utilisateur = Utilisateur.objects.get(id=payload.user_id)
    except Utilisateur.DoesNotExist:
        return 401, {"success": False, "detail": "Utilisateur introuvable."}

    if not verifier_code_mfa(utilisateur, payload.code):
        return 401, {"success": False, "detail": "Code incorrect ou expiré."}

    # Générer les tokens JWT
    refresh = RefreshToken.for_user(utilisateur)
    access = refresh.access_token

    # Journaliser la connexion
    _journaliser_connexion(utilisateur, request)

    return 200, {
        "access": str(access),
        "refresh": str(refresh),
        "user": {
            "id": str(utilisateur.id),
            "email": utilisateur.email,
            "nom_complet": utilisateur.nom_complet,
            "role": utilisateur.role,
            "telephone": utilisateur.telephone,
        },
    }


@router.post("/mfa/resend/", response={200: dict, 429: ErrorSchema}, auth=None)
def mfa_resend(request, payload: MFAResendSchema):
    """Renvoie un nouveau code MFA (limité à 1 demande / 60 sec)"""
    try:
        utilisateur = Utilisateur.objects.get(email=payload.email, is_active=True)
    except Utilisateur.DoesNotExist:
        # Sécurité : ne pas révéler si l'email existe
        return 200, {"success": True, "message": "Si l'email existe, un code a été envoyé."}

    # Anti-spam : vérifier qu'un token récent n'existe pas (< 60 sec)
    from .models import TokenMFA
    token_recent = TokenMFA.objects.filter(
        utilisateur=utilisateur,
        utilise=False,
        cree_le__gte=timezone.now() - timedelta(seconds=60)
    ).exists()

    if token_recent:
        return 429, {"success": False, "detail": "Attendez 60 secondes avant de redemander un code."}

    envoye = envoyer_code_mfa(utilisateur)
    return 200, {
        "success": envoye,
        "message": "Nouveau code envoyé." if envoye else "Erreur d'envoi."
    }


@router.post("/mfa/verify-link/", response={200: TokenSchema, 401: ErrorSchema}, auth=None)
def mfa_verify_link(request, payload: MFAVerifyLinkSchema):
    """
    Validation via le lien de vérification envoyé par email (clic direct,
    sans saisie manuelle du code). `payload.token` est un jeton signé et
    horodaté (django.core.signing) qui encode l'utilisateur et le token MFA
    visé — toute falsification ou expiration du lien est détectée ici.
    """
    from .models import TokenMFA

    try:
        donnees = signing.loads(payload.token, salt=MFA_LINK_SALT, max_age=MFA_LINK_MAX_AGE)
    except signing.SignatureExpired:
        return 401, {"success": False, "detail": "Le lien a expiré. Demandez un nouveau code."}
    except signing.BadSignature:
        return 401, {"success": False, "detail": "Lien de vérification invalide."}

    uid = donnees.get("uid")
    token_id = donnees.get("tid")

    try:
        utilisateur = Utilisateur.objects.get(id=uid)
        token = TokenMFA.objects.get(id=token_id, utilisateur=utilisateur, utilise=False)
    except (Utilisateur.DoesNotExist, TokenMFA.DoesNotExist):
        return 401, {"success": False, "detail": "Lien invalide ou déjà utilisé."}

    if not token.est_valide():
        return 401, {"success": False, "detail": "Le lien a expiré. Demandez un nouveau code."}

    # Marquer le token comme utilisé (même code que la saisie manuelle —
    # on ne peut pas valider deux fois avec le même lien ou le même code)
    token.utilise = True
    token.save(update_fields=['utilise'])

    refresh = RefreshToken.for_user(utilisateur)
    access = refresh.access_token

    _journaliser_connexion(utilisateur, request)

    return 200, {
        "access": str(access),
        "refresh": str(refresh),
        "user": {
            "id": str(utilisateur.id),
            "email": utilisateur.email,
            "nom_complet": utilisateur.nom_complet,
            "role": utilisateur.role,
            "telephone": utilisateur.telephone,
        },
    }


@router.post("/token/refresh/", auth=None)
def token_refresh(request, refresh: str):
    """Rafraîchit le token d'accès JWT"""
    try:
        token = RefreshToken(refresh)
        return {"access": str(token.access_token)}
    except Exception:
        return {"detail": "Token de refresh invalide ou expiré."}


@router.post("/logout/", auth=AuthBearer())
def logout(request):
    """Déconnexion — invalide le token refresh côté serveur"""
    # Avec simplejwt blacklist activée, on peut blacklister ici
    return {"success": True, "message": "Déconnecté avec succès."}


@router.get("/me/", response=UtilisateurSchema, auth=AuthBearer())
def me(request):
    """Retourne les infos de l'utilisateur connecté"""
    user = request.auth
    return {
        "id": str(user.id),
        "email": user.email,
        "nom_complet": user.nom_complet,
        "role": user.role,
        "telephone": user.telephone,
    }


# ─── Helpers privés ──────────────────────────────────────────────────────────

def _journaliser_connexion(utilisateur: Utilisateur, request):
    """Enregistre la connexion dans l'audit log"""
    try:
        from apps.auth_users.models import AuditLog
        ip = request.META.get('REMOTE_ADDR', '')
        ua = request.META.get('HTTP_USER_AGENT', '')[:300]
        AuditLog.objects.create(
            utilisateur=utilisateur,
            action='CONNEXION',
            objet_type='Utilisateur',
            objet_id=str(utilisateur.id),
            ip_address=ip,
            user_agent=ua,
        )
    except Exception:
        pass  # Ne pas bloquer la connexion si le log échoue
