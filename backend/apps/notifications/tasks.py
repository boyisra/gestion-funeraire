"""
Tâches Celery — GI2 2026
Alertes automatiques : expiration concessions, places critiques, retards paiement
"""
from celery import shared_task
from django.utils import timezone
from django.conf import settings


@shared_task
def verifier_concessions_expirant():
    """
    Tâche planifiée — vérifie chaque jour les concessions
    qui expirent dans les 90, 30 et 7 prochains jours
    Envoie des alertes aux titulaires
    """
    from apps.concessions.models import Concession
    from .service_email import envoyer_alerte_expiration_concession

    aujourd_hui = timezone.now().date()
    seuils = [90, 30, 7]  # Jours avant expiration
    total_alertes = 0

    for seuil in seuils:
        date_cible = aujourd_hui + timezone.timedelta(days=seuil)

        concessions = Concession.objects.filter(
            statut='ACTIVE',
            date_fin=date_cible,  # Exactement ce jour-là
        ).select_related('titulaire', 'reservation__caveau')

        for concession in concessions:
            envoyer_alerte_expiration_concession(concession)
            total_alertes += 1

    return f"{total_alertes} alertes d'expiration envoyées"


@shared_task
def verifier_places_critiques():
    """
    Tâche planifiée — alerte quand les places disponibles
    passent sous le seuil configuré (défaut : 10)
    """
    from apps.terrain.models import Caveau
    from apps.auth_users.models import Utilisateur
    from .service_email import envoyer_alerte_places_critiques

    seuil = getattr(settings, 'ALERTE_PLACES_CRITIQUES', 10)
    nb_disponibles = Caveau.objects.filter(etat='DISPONIBLE').count()

    if nb_disponibles <= seuil:
        admins = list(Utilisateur.objects.filter(role='ADMIN', is_active=True))
        nb_envoyes = envoyer_alerte_places_critiques(nb_disponibles, admins)
        return f"Alerte places critiques : {nb_disponibles} places — {nb_envoyes} admins notifiés"

    return f"OK — {nb_disponibles} places disponibles (seuil : {seuil})"


@shared_task
def verifier_reservations_expirees():
    """
    Tâche planifiée — expire les réservations non payées après 48h
    Remet les caveaux en DISPONIBLE
    """
    from apps.reservations.models import Reservation
    maintenant = timezone.now()

    reservations_expirees = Reservation.objects.filter(
        statut='EN_ATTENTE',
        date_expiration__lt=maintenant,
    )

    nb = 0
    for reservation in reservations_expirees:
        reservation.statut = 'EXPIREE'
        reservation.save(update_fields=['statut'])

        # Remettre le caveau disponible
        caveau = reservation.caveau
        caveau.etat = 'DISPONIBLE'
        caveau.save(update_fields=['etat'])
        nb += 1

    return f"{nb} réservations expirées traitées"


@shared_task
def renvoyer_notifications_echouees():
    """
    Tâche planifiée — retente les notifications non envoyées
    Maximum 3 tentatives
    """
    from .models import Notification
    from .service_email import envoyer_email

    notifications = Notification.objects.filter(
        envoyee=False,
        tentatives__lt=3,
    ).select_related('destinataire')[:50]

    nb_succes = 0
    for notif in notifications:
        succes = envoyer_email(
            notif.destinataire.email,
            notif.sujet,
            notif.contenu,
            notif.contenu_html or notif.contenu,
            notif,
        )
        if succes:
            nb_succes += 1

    return f"{nb_succes}/{len(notifications)} notifications renvoyées"
