"""
Service Email — GI2 2026
Envoi de toutes les notifications par email
Templates HTML intégrés
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from datetime import datetime


# ─── Template HTML de base ────────────────────────────────────────────────────

def _html_base(titre: str, contenu_html: str, couleur: str = "#1a5276") -> str:
    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<style>
  body {{ font-family: Arial, sans-serif; background:#f0f4f8; margin:0; padding:0; }}
  .wrapper {{ max-width:560px; margin:30px auto; background:#fff; border-radius:12px;
               overflow:hidden; box-shadow:0 2px 20px rgba(0,0,0,0.1); }}
  .header {{ background:{couleur}; padding:24px 30px; text-align:center; }}
  .header h1 {{ color:#fff; margin:0; font-size:20px; }}
  .header p {{ color:rgba(255,255,255,0.8); margin:6px 0 0; font-size:13px; }}
  .body {{ padding:30px; }}
  .body p {{ color:#444; line-height:1.6; font-size:14px; }}
  .info-box {{ background:#f8fafc; border-left:4px solid {couleur};
                border-radius:0 8px 8px 0; padding:16px; margin:16px 0; }}
  .info-box p {{ margin:4px 0; font-size:13px; }}
  .info-box strong {{ color:{couleur}; }}
  .btn {{ display:inline-block; background:{couleur}; color:#fff; padding:12px 28px;
           border-radius:8px; text-decoration:none; font-weight:bold; font-size:14px;
           margin:16px 0; }}
  .footer {{ background:#f8fafc; padding:16px 30px; text-align:center;
              border-top:1px solid #e2e8f0; }}
  .footer p {{ color:#999; font-size:11px; margin:0; }}
  .code-box {{ background:#1a5276; color:#fff; font-size:36px; font-weight:bold;
                letter-spacing:14px; text-align:center; padding:20px;
                border-radius:10px; margin:20px 0; }}
  .alerte {{ background:#fef3c7; border:1px solid #f59e0b; border-radius:8px;
              padding:14px; margin:12px 0; }}
  .alerte p {{ color:#92400e; margin:4px 0; font-size:13px; }}
  .success {{ background:#d1fae5; border:1px solid #10b981; border-radius:8px;
               padding:14px; margin:12px 0; }}
  .success p {{ color:#065f46; margin:4px 0; font-size:13px; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>⚰️ GI2 — Gestion de Cimetière</h1>
    <p>Système de gestion funéraire numérique</p>
  </div>
  <div class="body">
    <h2 style="color:{couleur};margin-top:0">{titre}</h2>
    {contenu_html}
  </div>
  <div class="footer">
    <p>© {datetime.now().year} GI2 — Application de Gestion de Cimetière</p>
    <p>Ce message est généré automatiquement, merci de ne pas y répondre.</p>
  </div>
</div>
</body>
</html>
"""


# ─── Fonction d'envoi principale ─────────────────────────────────────────────

def envoyer_email(
    destinataire_email: str,
    sujet: str,
    texte: str,
    html: str,
    notification=None,
) -> bool:
    """
    Envoie un email et met à jour la notification en base
    Retourne True si succès
    """
    try:
        msg = EmailMultiAlternatives(
            subject=sujet,
            body=texte,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinataire_email],
        )
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=False)

        if notification:
            notification.envoyee = True
            notification.date_envoi = timezone.now()
            notification.erreur = ''
            notification.save(update_fields=['envoyee', 'date_envoi', 'erreur'])

        return True

    except Exception as e:
        if notification:
            notification.tentatives += 1
            notification.erreur = str(e)[:500]
            notification.save(update_fields=['tentatives', 'erreur'])
        print(f"[EMAIL ERROR] {destinataire_email}: {e}")
        return False


# ─── Templates par type de notification ──────────────────────────────────────

def envoyer_code_mfa(utilisateur, code: str) -> bool:
    """Envoi du code MFA à 6 chiffres"""
    from .models import Notification

    sujet = "GI2 — Votre code de vérification"

    texte = (
        f"Bonjour {utilisateur.prenom},\n\n"
        f"Votre code de vérification est : {code}\n\n"
        f"Ce code expire dans 10 minutes.\n"
        f"Ne le partagez jamais.\n\n"
        f"— GI2 Gestion de Cimetière"
    )

    html_contenu = f"""
    <p>Bonjour <strong>{utilisateur.prenom}</strong>,</p>
    <p>Votre code de vérification pour accéder à votre espace GI2 est :</p>
    <div class="code-box">{code}</div>
    <div class="alerte">
      <p>⏱ Ce code expire dans <strong>10 minutes</strong>.</p>
      <p>🔒 Ne partagez jamais ce code avec personne.</p>
    </div>
    <p style="color:#999;font-size:12px;">
      Si vous n'avez pas demandé ce code, ignorez cet email.
    </p>
    """

    html = _html_base("Code de vérification", html_contenu)

    notif = Notification.objects.create(
        destinataire=utilisateur,
        type_notif='MFA',
        sujet=sujet,
        contenu=texte,
        contenu_html=html,
    )

    return envoyer_email(utilisateur.email, sujet, texte, html, notif)


def envoyer_confirmation_reservation(reservation) -> bool:
    """Confirmation de soumission d'une réservation"""
    from .models import Notification

    client = reservation.client
    caveau = reservation.caveau
    defunt = reservation.defunt

    sujet = f"GI2 — Réservation {reservation.reference} soumise"

    texte = (
        f"Bonjour {client.prenom},\n\n"
        f"Votre réservation {reservation.reference} a été soumise avec succès.\n"
        f"Elle est en attente de validation par notre équipe.\n\n"
        f"Défunt : {defunt.prenom} {defunt.nom}\n"
        f"Caveau : {caveau.numero} — Zone {caveau.zone.code}\n"
        f"Date d'inhumation : {reservation.date_inhumation}\n\n"
        f"Vous recevrez une confirmation dès validation.\n\n"
        f"— GI2 Gestion de Cimetière"
    )

    html_contenu = f"""
    <p>Bonjour <strong>{client.prenom}</strong>,</p>
    <p>Votre demande de réservation a été soumise avec succès et est en attente de validation.</p>
    <div class="info-box">
      <p><strong>Référence :</strong> {reservation.reference}</p>
      <p><strong>Défunt :</strong> {defunt.prenom} {defunt.nom}</p>
      <p><strong>Caveau :</strong> {caveau.numero} — Zone {caveau.zone.code}</p>
      <p><strong>Date d'inhumation :</strong> {reservation.date_inhumation}</p>
      <p><strong>Statut :</strong> En attente de validation</p>
    </div>
    <div class="alerte">
      <p>⏳ Votre réservation expire dans <strong>48 heures</strong> si non validée.</p>
    </div>
    <p>Notre équipe traitera votre demande dans les plus brefs délais.</p>
    """

    html = _html_base("Réservation soumise", html_contenu, "#f97316")

    notif = Notification.objects.create(
        destinataire=client,
        type_notif='CONFIRMATION_RESERVATION',
        sujet=sujet,
        contenu=texte,
        contenu_html=html,
    )

    return envoyer_email(client.email, sujet, texte, html, notif)


def envoyer_validation_reservation(reservation) -> bool:
    """Notification de validation d'une réservation"""
    from .models import Notification

    client = reservation.client
    caveau = reservation.caveau

    sujet = f"GI2 — Réservation {reservation.reference} validée ✅"

    texte = (
        f"Bonjour {client.prenom},\n\n"
        f"Votre réservation {reservation.reference} a été validée.\n\n"
        f"Caveau : {caveau.numero} — Zone {caveau.zone.code}\n"
        f"Montant : {int(reservation.montant_total):,} XAF\n\n"
        f"Vous pouvez maintenant procéder au paiement.\n\n"
        f"— GI2 Gestion de Cimetière"
    )

    html_contenu = f"""
    <p>Bonjour <strong>{client.prenom}</strong>,</p>
    <div class="success">
      <p>✅ Votre réservation <strong>{reservation.reference}</strong> a été <strong>validée</strong> !</p>
    </div>
    <div class="info-box">
      <p><strong>Caveau :</strong> {caveau.numero} — Zone {caveau.zone.code}</p>
      <p><strong>Montant à payer :</strong> {int(reservation.montant_total):,} XAF</p>
      <p><strong>Validée le :</strong> {reservation.date_validation.strftime('%d/%m/%Y à %H:%M') if reservation.date_validation else ''}</p>
    </div>
    <p>Vous pouvez maintenant effectuer votre paiement via Mobile Money, Airtel Money, espèces ou virement.</p>
    """

    html = _html_base("Réservation validée", html_contenu, "#22c55e")

    notif = Notification.objects.create(
        destinataire=client,
        type_notif='VALIDATION_RESERVATION',
        sujet=sujet,
        contenu=texte,
        contenu_html=html,
    )

    return envoyer_email(client.email, sujet, texte, html, notif)


def envoyer_confirmation_paiement(paiement) -> bool:
    """Notification de paiement confirmé avec lien facture"""
    from .models import Notification

    client = paiement.client
    reservation = paiement.reservation
    canal_label = dict(paiement.CANAUX).get(paiement.canal, paiement.canal)

    sujet = f"GI2 — Paiement {paiement.reference} confirmé ✅"

    texte = (
        f"Bonjour {client.prenom},\n\n"
        f"Votre paiement de {int(paiement.montant):,} XAF a été confirmé.\n\n"
        f"Référence paiement : {paiement.reference}\n"
        f"Mode : {canal_label}\n"
        f"Réservation : {reservation.reference}\n\n"
        f"Votre facture est disponible dans votre espace client.\n\n"
        f"— GI2 Gestion de Cimetière"
    )

    html_contenu = f"""
    <p>Bonjour <strong>{client.prenom}</strong>,</p>
    <div class="success">
      <p>✅ Votre paiement de <strong>{int(paiement.montant):,} XAF</strong> a été confirmé !</p>
    </div>
    <div class="info-box">
      <p><strong>Réf. paiement :</strong> {paiement.reference}</p>
      <p><strong>Mode de paiement :</strong> {canal_label}</p>
      <p><strong>Réservation :</strong> {reservation.reference}</p>
      <p><strong>Montant :</strong> {int(paiement.montant):,} XAF</p>
      {'<p><strong>Réf. opérateur :</strong> ' + paiement.reference_operateur + '</p>' if paiement.reference_operateur else ''}
      <p><strong>Date :</strong> {paiement.date_confirmation.strftime('%d/%m/%Y à %H:%M') if paiement.date_confirmation else ''}</p>
    </div>
    <p>Votre facture et votre certificat d'inhumation sont disponibles dans votre espace client.</p>
    """

    html = _html_base("Paiement confirmé", html_contenu, "#22c55e")

    notif = Notification.objects.create(
        destinataire=client,
        type_notif='FACTURE',
        sujet=sujet,
        contenu=texte,
        contenu_html=html,
    )

    return envoyer_email(client.email, sujet, texte, html, notif)


def envoyer_alerte_expiration_concession(concession) -> bool:
    """Alerte 90 jours avant expiration d'une concession"""
    from .models import Notification

    titulaire = concession.titulaire
    jours = concession.jours_restants

    sujet = f"GI2 — Alerte : votre concession expire dans {jours} jours"

    texte = (
        f"Bonjour {titulaire.prenom},\n\n"
        f"Votre concession {concession.reference} expire dans {jours} jours.\n\n"
        f"Type : {concession.get_type_concession_display()}\n"
        f"Caveau : {concession.reservation.caveau.numero}\n"
        f"Date d'expiration : {concession.date_fin}\n\n"
        f"Contactez-nous pour renouveler votre concession.\n\n"
        f"— GI2 Gestion de Cimetière"
    )

    couleur_alerte = "#ef4444" if jours <= 30 else "#f59e0b"

    html_contenu = f"""
    <p>Bonjour <strong>{titulaire.prenom}</strong>,</p>
    <div class="alerte" style="border-color:{couleur_alerte};background:{'#fef2f2' if jours <= 30 else '#fef3c7'}">
      <p style="color:{'#991b1b' if jours <= 30 else '#92400e'}">
        ⚠️ Votre concession expire dans <strong>{jours} jours</strong> !
      </p>
    </div>
    <div class="info-box">
      <p><strong>Concession :</strong> {concession.reference}</p>
      <p><strong>Type :</strong> {concession.get_type_concession_display()}</p>
      <p><strong>Caveau :</strong> {concession.reservation.caveau.numero}</p>
      <p><strong>Date d'expiration :</strong> {concession.date_fin}</p>
    </div>
    <p>Pour renouveler votre concession, connectez-vous à votre espace client ou contactez notre administration.</p>
    """

    html = _html_base("Alerte expiration concession", html_contenu, couleur_alerte)

    notif = Notification.objects.create(
        destinataire=titulaire,
        type_notif='ALERTE_EXPIRATION',
        sujet=sujet,
        contenu=texte,
        contenu_html=html,
    )

    return envoyer_email(titulaire.email, sujet, texte, html, notif)


def envoyer_alerte_places_critiques(nb_places: int, admins) -> int:
    """Alerte admin quand le nombre de places disponibles est critique"""
    from .models import Notification

    sujet = f"GI2 — ⚠️ Alerte : seulement {nb_places} places disponibles"

    texte = (
        f"Alerte système GI2\n\n"
        f"Il ne reste que {nb_places} place(s) disponible(s) dans le cimetière.\n\n"
        f"Veuillez prendre les mesures nécessaires.\n\n"
        f"— Système GI2"
    )

    html_contenu = f"""
    <p>Alerte système automatique :</p>
    <div class="alerte" style="border-color:#ef4444;background:#fef2f2">
      <p style="color:#991b1b;font-size:16px">
        🚨 Il ne reste que <strong>{nb_places} place(s)</strong> disponible(s) !
      </p>
    </div>
    <p>Veuillez vérifier la capacité du cimetière et prendre les mesures nécessaires.</p>
    """

    html = _html_base("Alerte places critiques", html_contenu, "#ef4444")

    envoyes = 0
    for admin in admins:
        notif = Notification.objects.create(
            destinataire=admin,
            type_notif='ALERTE_PLACES',
            sujet=sujet,
            contenu=texte,
            contenu_html=html,
        )
        if envoyer_email(admin.email, sujet, texte, html, notif):
            envoyes += 1

    return envoyes


def envoyer_alerte_admin_nouvelle_reservation(reservation, admins) -> int:
    """Notifie les admins d'une nouvelle réservation en attente"""
    from .models import Notification

    sujet = f"GI2 — Nouvelle réservation {reservation.reference} en attente"

    texte = (
        f"Nouvelle réservation reçue\n\n"
        f"Référence : {reservation.reference}\n"
        f"Client : {reservation.client.nom_complet}\n"
        f"Caveau : {reservation.caveau.numero}\n"
        f"À valider dans votre espace admin.\n\n"
        f"— Système GI2"
    )

    html_contenu = f"""
    <p>Une nouvelle réservation est en attente de validation :</p>
    <div class="info-box">
      <p><strong>Référence :</strong> {reservation.reference}</p>
      <p><strong>Client :</strong> {reservation.client.nom_complet}</p>
      <p><strong>Email :</strong> {reservation.client.email}</p>
      <p><strong>Caveau :</strong> {reservation.caveau.numero} — Zone {reservation.caveau.zone.code}</p>
      <p><strong>Défunt :</strong> {reservation.defunt.prenom} {reservation.defunt.nom}</p>
      <p><strong>Date d'inhumation :</strong> {reservation.date_inhumation}</p>
    </div>
    <p>Connectez-vous à votre espace administrateur pour valider cette réservation.</p>
    """

    html = _html_base("Nouvelle réservation à valider", html_contenu, "#f97316")

    envoyes = 0
    for admin in admins:
        notif = Notification.objects.create(
            destinataire=admin,
            type_notif='CONFIRMATION_RESERVATION',
            sujet=sujet,
            contenu=texte,
            contenu_html=html,
        )
        if envoyer_email(admin.email, sujet, texte, html, notif):
            envoyes += 1

    return envoyes
