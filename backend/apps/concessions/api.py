"""
API Concessions & Exhumations — Django Ninja — GI2 2026
"""
from typing import List, Optional
from datetime import date
from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.auth_users.api import AuthBearer
from .models import Concession, DemandeExhumation

router = Router(tags=["Concessions & Exhumations"])


# ─── Schémas ─────────────────────────────────────────────────────────────────

class ConcessionCreateSchema(Schema):
    reservation_id: str
    type_concession: str
    date_debut: date
    prix_total: float


class ConcessionSchema(Schema):
    id: str
    reference: str
    type_concession: str
    statut: str
    titulaire_nom: str
    caveau_numero: str
    date_debut: date
    date_fin: Optional[date] = None
    date_alerte: Optional[date] = None
    prix_total: float
    jours_restants: Optional[int] = None


class ExhumationCreateSchema(Schema):
    concession_id: str
    motif: str
    date_execution_prevue: Optional[date] = None


class ExhumationSchema(Schema):
    id: str
    reference: str
    statut: str
    concession_ref: str
    caveau_numero: str
    demandeur_nom: str
    motif: str
    date_demande: str
    date_execution_prevue: Optional[date] = None
    date_execution_reelle: Optional[date] = None
    notes_admin: str


class AutoriserExhumationSchema(Schema):
    notes_admin: str = ''
    date_execution_prevue: Optional[date] = None


# ─── Concessions ─────────────────────────────────────────────────────────────

@router.post("/", response=ConcessionSchema, auth=AuthBearer())
def creer_concession(request, payload: ConcessionCreateSchema):
    """Crée une concession après validation de la réservation — Admin/Secrétariat"""
    if request.auth.role not in ('ADMIN', 'SECRETARIAT'):
        return {"detail": "Accès refusé"}

    from apps.reservations.models import Reservation
    reservation = get_object_or_404(Reservation, id=payload.reservation_id)

    if reservation.statut != 'VALIDEE':
        return {"detail": "La réservation doit être validée avant de créer une concession."}

    if hasattr(reservation, 'concession'):
        return {"detail": "Une concession existe déjà pour cette réservation."}

    concession = Concession.objects.create(
        reservation=reservation,
        titulaire=reservation.client,
        type_concession=payload.type_concession,
        date_debut=payload.date_debut,
        prix_total=payload.prix_total,
        cree_par=request.auth,
    )

    _log(request.auth, 'CREATION_CONCESSION', 'Concession', str(concession.id),
         nouvelle_valeur={'type': payload.type_concession, 'debut': str(payload.date_debut)})

    return _concession_dict(concession)


@router.get("/", response=List[ConcessionSchema], auth=AuthBearer())
def liste_concessions(request, statut: str = None):
    """Liste les concessions"""
    if request.auth.role in ('ADMIN', 'AGENT', 'SECRETARIAT'):
        qs = Concession.objects.select_related(
            'titulaire', 'reservation__caveau'
        )
    else:
        qs = Concession.objects.filter(titulaire=request.auth).select_related(
            'reservation__caveau'
        )

    if statut:
        qs = qs.filter(statut=statut)

    return [_concession_dict(c) for c in qs]


@router.get("/expirant/", response=List[ConcessionSchema], auth=AuthBearer())
def concessions_expirant(request):
    """Concessions qui expirent dans les 90 prochains jours"""
    if request.auth.role not in ('ADMIN', 'SECRETARIAT'):
        return {"detail": "Accès refusé"}

    aujourd_hui = timezone.now().date()
    dans_90j = aujourd_hui + timezone.timedelta(days=90)

    qs = Concession.objects.filter(
        statut='ACTIVE',
        date_fin__lte=dans_90j,
        date_fin__gte=aujourd_hui,
    ).select_related('titulaire', 'reservation__caveau')

    return [_concession_dict(c) for c in qs]


@router.post("/{concession_id}/renouveler/", response=ConcessionSchema, auth=AuthBearer())
def renouveler_concession(request, concession_id: str, nouveau_type: str, prix: float):
    """Renouvelle une concession"""
    if request.auth.role not in ('ADMIN', 'SECRETARIAT'):
        return {"detail": "Accès refusé"}

    concession = get_object_or_404(Concession, id=concession_id)
    ancien_statut = concession.statut
    concession.type_concession = nouveau_type
    concession.statut = 'ACTIVE'
    concession.prix_total = prix
    concession.date_debut = timezone.now().date()
    concession.date_fin = None     # Sera recalculé dans save()
    concession.date_alerte = None  # Sera recalculé dans save()
    concession.save()

    _log(request.auth, 'CREATION_CONCESSION', 'Concession', str(concession_id),
         ancienne_valeur={'statut': ancien_statut},
         nouvelle_valeur={'statut': 'ACTIVE', 'type': nouveau_type})

    return _concession_dict(concession)


@router.post("/{concession_id}/resilier/", auth=AuthBearer())
def resilier_concession(request, concession_id: str):
    """Résilie une concession — Admin seulement"""
    if request.auth.role != 'ADMIN':
        return {"detail": "Accès refusé"}

    concession = get_object_or_404(Concession, id=concession_id)
    concession.statut = 'RESILIEE'
    concession.save()

    # Remettre le caveau disponible
    caveau = concession.reservation.caveau
    caveau.etat = 'DISPONIBLE'
    caveau.save()

    return {"success": True, "message": "Concession résiliée."}


# ─── Exhumations ─────────────────────────────────────────────────────────────

@router.post("/exhumations/", response=ExhumationSchema, auth=AuthBearer())
def creer_exhumation(request, payload: ExhumationCreateSchema):
    """Soumet une demande d'exhumation"""
    concession = get_object_or_404(Concession, id=payload.concession_id)

    # Seul le titulaire ou le staff peut demander
    if request.auth.role == 'CLIENT' and concession.titulaire != request.auth:
        return {"detail": "Accès refusé"}

    exhumation = DemandeExhumation.objects.create(
        concession=concession,
        demandeur=request.auth,
        motif=payload.motif,
        date_execution_prevue=payload.date_execution_prevue,
    )

    return _exhumation_dict(exhumation)


@router.get("/exhumations/", response=List[ExhumationSchema], auth=AuthBearer())
def liste_exhumations(request):
    """Liste les demandes d'exhumation"""
    if request.auth.role in ('ADMIN', 'AGENT', 'SECRETARIAT'):
        qs = DemandeExhumation.objects.select_related(
            'concession__reservation__caveau', 'demandeur', 'autorise_par'
        )
    else:
        qs = DemandeExhumation.objects.filter(
            demandeur=request.auth
        ).select_related('concession__reservation__caveau')

    return [_exhumation_dict(e) for e in qs]


@router.post("/exhumations/{exh_id}/autoriser/", response=ExhumationSchema, auth=AuthBearer())
def autoriser_exhumation(request, exh_id: str, payload: AutoriserExhumationSchema):
    """Autorise une exhumation — Admin seulement"""
    if request.auth.role != 'ADMIN':
        return {"detail": "Accès refusé"}

    exh = get_object_or_404(DemandeExhumation, id=exh_id)
    exh.statut = 'AUTORISEE'
    exh.autorise_par = request.auth
    exh.notes_admin = payload.notes_admin
    if payload.date_execution_prevue:
        exh.date_execution_prevue = payload.date_execution_prevue
    exh.save()

    _log(request.auth, 'AUTORISATION_EXHUMATION', 'Exhumation', str(exh_id),
         nouvelle_valeur={'statut': 'AUTORISEE'})

    return _exhumation_dict(exh)


@router.post("/exhumations/{exh_id}/refuser/", response=ExhumationSchema, auth=AuthBearer())
def refuser_exhumation(request, exh_id: str, notes: str = ''):
    """Refuse une exhumation — Admin seulement"""
    if request.auth.role != 'ADMIN':
        return {"detail": "Accès refusé"}

    exh = get_object_or_404(DemandeExhumation, id=exh_id)
    exh.statut = 'REFUSEE'
    exh.notes_admin = notes
    exh.autorise_par = request.auth
    exh.save()

    return _exhumation_dict(exh)


@router.post("/exhumations/{exh_id}/executer/", response=ExhumationSchema, auth=AuthBearer())
def executer_exhumation(request, exh_id: str):
    """Marque une exhumation comme exécutée — Agent/Admin"""
    if request.auth.role not in ('ADMIN', 'AGENT'):
        return {"detail": "Accès refusé"}

    exh = get_object_or_404(DemandeExhumation, id=exh_id)
    if exh.statut != 'AUTORISEE':
        return {"detail": "L'exhumation doit être autorisée avant d'être exécutée."}

    exh.statut = 'EXECUTEE'
    exh.date_execution_reelle = timezone.now().date()
    exh.save()

    # Remettre le caveau disponible
    caveau = exh.concession.reservation.caveau
    caveau.etat = 'DISPONIBLE'
    caveau.save()

    return _exhumation_dict(exh)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _concession_dict(c: Concession) -> dict:
    return {
        'id': str(c.id),
        'reference': c.reference,
        'type_concession': c.type_concession,
        'statut': c.statut,
        'titulaire_nom': c.titulaire.nom_complet,
        'caveau_numero': c.reservation.caveau.numero,
        'date_debut': c.date_debut,
        'date_fin': c.date_fin,
        'date_alerte': c.date_alerte,
        'prix_total': float(c.prix_total),
        'jours_restants': c.jours_restants,
    }


def _exhumation_dict(e: DemandeExhumation) -> dict:
    return {
        'id': str(e.id),
        'reference': e.reference,
        'statut': e.statut,
        'concession_ref': e.concession.reference,
        'caveau_numero': e.concession.reservation.caveau.numero,
        'demandeur_nom': e.demandeur.nom_complet,
        'motif': e.motif,
        'date_demande': e.date_demande.strftime('%d/%m/%Y %H:%M'),
        'date_execution_prevue': e.date_execution_prevue,
        'date_execution_reelle': e.date_execution_reelle,
        'notes_admin': e.notes_admin,
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
