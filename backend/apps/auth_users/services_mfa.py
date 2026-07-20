"""
Service MFA — Génération et envoi des codes à 6 chiffres par email
"""
import random
import string
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.core import signing
from django.conf import settings

from .models import Utilisateur, TokenMFA

# Salt dédié à la signature des liens de vérification MFA — ne pas réutiliser ailleurs
MFA_LINK_SALT = "gi2-mfa-magic-link"
MFA_LINK_MAX_AGE = 600  # 10 minutes — doit correspondre à la durée de vie du code


def generer_code_mfa() -> str:
    """Génère un code aléatoire à 6 chiffres"""
    return ''.join(random.choices(string.digits, k=6))


def creer_token_mfa(utilisateur: Utilisateur, objectif: str = 'CONNEXION') -> TokenMFA:
    """
    Invalide les anciens tokens (du même objectif) et crée un nouveau code MFA
    Durée de validité : 10 minutes
    """
    # Invalider tous les tokens précédents de cet utilisateur pour ce même
    # objectif — un code d'inscription en attente n'invalide pas un code de
    # connexion en attente, et inversement.
    TokenMFA.objects.filter(
        utilisateur=utilisateur,
        objectif=objectif,
        utilise=False
    ).update(utilise=True)

    # Créer le nouveau token
    code = generer_code_mfa()
    expiration = timezone.now() + timedelta(minutes=10)

    token = TokenMFA.objects.create(
        utilisateur=utilisateur,
        code=code,
        objectif=objectif,
        expiration=expiration,
    )
    return token


def generer_lien_mfa(token: TokenMFA) -> str:
    """
    Construit un lien de vérification signé et à durée de vie limitée.
    Cliquer dessus valide automatiquement le code MFA sans saisie manuelle.
    Le payload est signé (infalsifiable) et inclut un horodatage vérifié à
    la lecture via `max_age` — voir mfa_verify_link() dans api.py.
    """
    payload = {"uid": str(token.utilisateur.id), "tid": str(token.id)}
    jeton_signe = signing.dumps(payload, salt=MFA_LINK_SALT)
    base_url = getattr(settings, "FRONTEND_URL", "http://localhost:8550").rstrip("/")
    return f"{base_url}/mfa/confirmer?uid={token.utilisateur.id}&token={jeton_signe}"


def envoyer_code_mfa(utilisateur: Utilisateur) -> bool:
    """
    Génère un code MFA et l'envoie par email
    Retourne True si l'envoi a réussi
    """
    token = creer_token_mfa(utilisateur)
    lien = generer_lien_mfa(token)

    sujet = "GI2 Cimetière — Votre code de vérification"
    message_texte = f"""
Bonjour {utilisateur.prenom},

Votre code de vérification est :

    {token.code}

Ce code est valable pendant 10 minutes.
Ne le partagez avec personne.

Vous pouvez aussi valider automatiquement en cliquant sur ce lien :
{lien}

Si vous n'avez pas demandé ce code, ignorez cet email.

— Équipe GI2 Gestion de Cimetière
    """

    message_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
        <div style="background: #1a5276; padding: 20px; border-radius: 8px 8px 0 0; text-align: center;">
            <h2 style="color: white; margin: 0;">GI2 — Gestion de Cimetière</h2>
        </div>
        <div style="background: #f8f9fa; padding: 32px; border-radius: 0 0 8px 8px; text-align: center;">
            <p style="color: #333; font-size: 16px;">Bonjour <strong>{utilisateur.prenom}</strong>,</p>
            <p style="color: #555;">Votre code de vérification est :</p>
            <div style="background: #1a5276; color: white; font-size: 36px; font-weight: bold;
                        letter-spacing: 12px; padding: 20px; border-radius: 8px; margin: 20px 0;">
                {token.code}
            </div>
            <p style="color: #e67e22; font-size: 14px;">⏱ Ce code expire dans <strong>10 minutes</strong>.</p>
            <a href="{lien}" style="display:inline-block; background:#38bdf8; color:#0f172a; font-weight:bold;
                        padding:12px 28px; border-radius:8px; text-decoration:none; margin:10px 0;">
                Valider automatiquement
            </a>
            <p style="color: #999; font-size: 12px;">Ne partagez jamais ce code ni ce lien.</p>
        </div>
    </div>
    """

    try:
        send_mail(
            subject=sujet,
            message=message_texte,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[utilisateur.email],
            html_message=message_html,
            fail_silently=False,
        )
        return True
    except Exception as e:
        # Logger l'erreur en production
        print(f"Erreur envoi MFA pour {utilisateur.email}: {e}")
        return False


def envoyer_code_verification_inscription(utilisateur: Utilisateur) -> bool:
    """
    Envoie le code de vérification d'adresse email à l'inscription (une
    seule fois, avant le tout premier login). Distinct du code de connexion
    envoyé à chaque authentification — voir envoyer_code_mfa().
    """
    token = creer_token_mfa(utilisateur, objectif='INSCRIPTION')

    sujet = "GI2 Cimetière — Confirmez votre adresse email"
    message_texte = f"""
Bonjour {utilisateur.prenom},

Merci de vous être inscrit(e) sur GI2 — Gestion de Cimetière.

Pour activer votre compte, saisissez ce code de vérification dans
l'application :

    {token.code}

Ce code est valable pendant 10 minutes.

Si vous n'êtes pas à l'origine de cette inscription, ignorez cet email.

— Équipe GI2 Gestion de Cimetière
    """

    message_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
        <div style="background: #1a5276; padding: 20px; border-radius: 8px 8px 0 0; text-align: center;">
            <h2 style="color: white; margin: 0;">GI2 — Gestion de Cimetière</h2>
        </div>
        <div style="background: #f8f9fa; padding: 32px; border-radius: 0 0 8px 8px; text-align: center;">
            <p style="color: #333; font-size: 16px;">Bonjour <strong>{utilisateur.prenom}</strong>,</p>
            <p style="color: #555;">Merci de vous être inscrit(e). Confirmez votre adresse email avec ce code :</p>
            <div style="background: #1a5276; color: white; font-size: 36px; font-weight: bold;
                        letter-spacing: 12px; padding: 20px; border-radius: 8px; margin: 20px 0;">
                {token.code}
            </div>
            <p style="color: #e67e22; font-size: 14px;">⏱ Ce code expire dans <strong>10 minutes</strong>.</p>
            <p style="color: #999; font-size: 12px;">Si vous n'êtes pas à l'origine de cette inscription, ignorez cet email.</p>
        </div>
    </div>
    """

    try:
        send_mail(
            subject=sujet,
            message=message_texte,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[utilisateur.email],
            html_message=message_html,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Erreur envoi vérification inscription pour {utilisateur.email}: {e}")
        return False


def verifier_code_mfa(utilisateur: Utilisateur, code: str, objectif: str = 'CONNEXION') -> bool:
    """
    Vérifie si le code soumis est valide pour l'objectif donné
    Marque le token comme utilisé si correct
    """
    try:
        token = TokenMFA.objects.get(
            utilisateur=utilisateur,
            code=code,
            objectif=objectif,
            utilise=False,
        )
        if not token.est_valide():
            return False

        # Marquer comme utilisé
        token.utilise = True
        token.save(update_fields=['utilise'])
        return True

    except TokenMFA.DoesNotExist:
        return False

