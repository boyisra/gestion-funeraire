"""
API Réservations — Django Ninja — GI2 2026
Endpoints : créer, lister, valider, annuler
"""
from typing import List, Optional
from datetime import date
from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.auth_users.api import AuthBearer
from apps.terrain.models import Caveau
from .models import Reservation, Defunt

router = Router(tags=["Réservations"])


# ─── Schémas ─────────────────────────────────────────────────────────────────

class DefuntSchema(Schema):
    nom: str
    prenom: str
    date_naissance: Optional[date] = None
    date_deces: date
    lieu_deces: str = ''
    numero_acte_deces: str = ''
    nationalite: str = 'Congolaise'


class ReservationCreateSchema(Schema):
    caveau_id: str
    defunt: DefuntSchema
    date_inhumation: date
    notes_admin: str = ''


class ReservationSchema(Schema):
    id: str
    reference: str
    statut: str
    caveau_numero: str
    caveau_zone: str
    client_nom: str
    client_email: str
    defunt_nom: str
    defunt_prenom: str
    defunt_date_deces: date
    date_inhumation: date
    date_soumission: str
    date_validation: Optional[str] = None
    montant_total: float
    notes_admin: str


class ValidationSchema(Schema):
    notes_admin: str = ''
    montant_total: float = 0


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/", response=ReservationSchema, auth=AuthBearer())
def creer_reservation(request, payload: ReservationCreateSchema):
    """Crée une réservation — accessible aux clients et staff"""
    caveau = get_object_or_404(Caveau, id=payload.caveau_id)

    if caveau.etat != 'DISPONIBLE':
        return {"detail": f"Ce caveau n'est pas disponible (état : {caveau.etat})"}

    # Créer le défunt
    defunt = Defunt.objects.create(**payload.defunt.dict())

    # Créer la réservation
    reservation = Reservation.objects.create(
        caveau=caveau,
        client=request.auth,
        defunt=defunt,
        date_inhumation=payload.date_inhumation,
        notes_admin=payload.notes_admin,
    )

    # Passer le caveau en RESERVE
    caveau.etat = 'RESERVE'
    caveau.modifie_par = request.auth
    caveau.save()

    # Audit log
    _log(request.auth, 'CHANGEMENT_STATUT_CAVEAU', 'Caveau', str(caveau.id),
         ancienne_valeur={'etat': 'DISPONIBLE'},
         nouvelle_valeur={'etat': 'RESERVE', 'reservation': str(reservation.id)})

    # Notifier l'admin
    _notifier_admin_nouvelle_reservation(reservation)

    return _to_dict(reservation)


@router.get("/", response=List[ReservationSchema], auth=AuthBearer())
def liste_reservations(request, statut: str = None):
    """
    Liste les réservations.
    - Admin/Agent/Secrétariat : toutes les réservations
    - Client : seulement les siennes
    """
    if request.auth.role in ('ADMIN', 'AGENT', 'SECRETARIAT'):
        qs = Reservation.objects.select_related(
            'caveau', 'caveau__zone', 'client', 'defunt', 'valide_par'
        )
    else:
        qs = Reservation.objects.filter(client=request.auth).select_related(
            'caveau', 'caveau__zone', 'client', 'defunt'
        )

    if statut:
        qs = qs.filter(statut=statut)

    return [_to_dict(r) for r in qs]


@router.get("/{reservation_id}/", response=ReservationSchema, auth=AuthBearer())
def get_reservation(request, reservation_id: str):
    """Détail d'une réservation"""
    reservation = get_object_or_404(Reservation, id=reservation_id)

    # Client ne peut voir que la sienne
    if request.auth.role == 'CLIENT' and reservation.client != request.auth:
        return {"detail": "Accès refusé"}

    return _to_dict(reservation)


@router.post("/{reservation_id}/valider/", response=ReservationSchema, auth=AuthBearer())
def valider_reservation(request, reservation_id: str, payload: ValidationSchema):
    """
    Valide une réservation — Admin/Secrétariat seulement
    Passe le statut EN_ATTENTE → VALIDEE et le caveau RESERVE → OCCUPE
    """
    if request.auth.role not in ('ADMIN', 'SECRETARIAT'):
        return {"detail": "Accès refusé"}

    reservation = get_object_or_404(Reservation, id=reservation_id)

    if reservation.statut != 'EN_ATTENTE':
        return {"detail": f"Impossible de valider : statut actuel = {reservation.statut}"}

    # Mettre à jour la réservation
    reservation.statut = 'VALIDEE'
    reservation.date_validation = timezone.now()
    reservation.valide_par = request.auth
    reservation.notes_admin = payload.notes_admin
    if payload.montant_total:
        reservation.montant_total = payload.montant_total
    reservation.save()

    # Passer le caveau en OCCUPE
    caveau = reservation.caveau
    caveau.etat = 'OCCUPE'
    caveau.modifie_par = request.auth
    caveau.save()

    # Audit log
    _log(request.auth, 'VALIDATION_RESERVATION', 'Reservation', str(reservation_id),
         ancienne_valeur={'statut': 'EN_ATTENTE'},
         nouvelle_valeur={'statut': 'VALIDEE'})

    # Notifier le client
    _notifier_client_validation(reservation)

    return _to_dict(reservation)


@router.post("/{reservation_id}/annuler/", response=ReservationSchema, auth=AuthBearer())
def annuler_reservation(request, reservation_id: str):
    """
    Annule une réservation
    Remet le caveau en DISPONIBLE
    """
    reservation = get_object_or_404(Reservation, id=reservation_id)

    # Seul le client propriétaire ou le staff peut annuler
    if request.auth.role == 'CLIENT' and reservation.client != request.auth:
        return {"detail": "Accès refusé"}

    if reservation.statut == 'VALIDEE':
        return {"detail": "Une réservation validée ne peut pas être annulée directement."}

    reservation.statut = 'ANNULEE'
    reservation.save()

    # Remettre le caveau disponible
    caveau = reservation.caveau
    caveau.etat = 'DISPONIBLE'
    caveau.modifie_par = request.auth
    caveau.save()

    _log(request.auth, 'ANNULATION_RESERVATION', 'Reservation', str(reservation_id),
         ancienne_valeur={'statut': reservation.statut},
         nouvelle_valeur={'statut': 'ANNULEE'})

    return _to_dict(reservation)


@router.get("/stats/", auth=AuthBearer())
def stats_reservations(request):
    """Statistiques des réservations"""
    if request.auth.role not in ('ADMIN', 'AGENT', 'SECRETARIAT'):
        return {"detail": "Accès refusé"}

    return {
        "total": Reservation.objects.count(),
        "en_attente": Reservation.objects.filter(statut='EN_ATTENTE').count(),
        "validees": Reservation.objects.filter(statut='VALIDEE').count(),
        "annulees": Reservation.objects.filter(statut='ANNULEE').count(),
        "expirees": Reservation.objects.filter(statut='EXPIREE').count(),
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _to_dict(r: Reservation) -> dict:
    return {
        'id': str(r.id),
        'reference': r.reference,
        'statut': r.statut,
        'caveau_numero': r.caveau.numero,
        'caveau_zone': r.caveau.zone.code,
        'client_nom': r.client.nom_complet,
        'client_email': r.client.email,
        'defunt_nom': r.defunt.nom,
        'defunt_prenom': r.defunt.prenom,
        'defunt_date_deces': r.defunt.date_deces,
        'date_inhumation': r.date_inhumation,
        'date_soumission': r.date_soumission.strftime('%d/%m/%Y %H:%M'),
        'date_validation': r.date_validation.strftime('%d/%m/%Y %H:%M') if r.date_validation else None,
        'montant_total': float(r.montant_total),
        'notes_admin': r.notes_admin,
    }


def _log(user, action, obj_type, obj_id, ancienne_valeur=None, nouvelle_valeur=None):
    try:
        from apps.auth_users.models import AuditLog
        AuditLog.objects.create(
            utilisateur=user, action=action,
            objet_type=obj_type, objet_id=obj_id,
            ancienne_valeur=ancienne_valeur or {},
            nouvelle_valeur=nouvelle_valeur or {},
        )
    except Exception:
        pass


def _notifier_admin_nouvelle_reservation(reservation: Reservation):
    try:
        from apps.notifications.models import Notification
        from apps.auth_users.models import Utilisateur
        admins = Utilisateur.objects.filter(role='ADMIN', is_active=True)
        for admin in admins:
            Notification.objects.create(
                destinataire=admin,
                type_notif='CONFIRMATION_RESERVATION',
                sujet=f"Nouvelle réservation {reservation.reference}",
                contenu=f"Nouvelle réservation de {reservation.client.nom_complet} "
                        f"pour le caveau {reservation.caveau.numero}.",
            )
    except Exception:
        pass


def _notifier_client_validation(reservation: Reservation):
    try:
        from apps.notifications.models import Notification
        Notification.objects.create(
            destinataire=reservation.client,
            type_notif='CONFIRMATION_RESERVATION',
            sujet=f"Réservation {reservation.reference} validée",
            contenu=f"Votre réservation pour le caveau {reservation.caveau.numero} "
                    f"a été validée le {reservation.date_validation.strftime('%d/%m/%Y')}.",
        )
    except Exception:
        pass
