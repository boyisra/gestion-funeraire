"""
API Paiements — Django Ninja — GI2 2026
Mobile Money MTN, Airtel Money, Espèces, Virement
"""
from typing import List, Optional
from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.auth_users.api import AuthBearer
from apps.reservations.models import Reservation
from .models import Paiement, TransactionMobileMoney
from .service_mtn import MTNMoMoService
from .service_airtel import AirtelMoneyService

router = Router(tags=["Paiements"])


# ─── Schémas ─────────────────────────────────────────────────────────────────

class PaiementInitierSchema(Schema):
    reservation_id: str
    canal: str                  # MOBILE_MONEY, AIRTEL_MONEY, ESPECES, VIREMENT
    montant: float
    numero_telephone: str = ''  # Obligatoire pour Mobile Money / Airtel


class PaiementSchema(Schema):
    id: str
    reference: str
    canal: str
    statut: str
    montant: float
    devise: str
    numero_telephone: str
    reference_operateur: str
    transaction_id_externe: str
    reservation_ref: str
    client_nom: str
    date_initiation: str
    date_confirmation: Optional[str] = None


class PaiementEspecesSchema(Schema):
    reservation_id: str
    montant: float
    notes: str = ''


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/initier/", auth=AuthBearer())
def initier_paiement(request, payload: PaiementInitierSchema):
    """
    Initie un paiement selon le canal choisi
    - MOBILE_MONEY : appel API MTN MoMo
    - AIRTEL_MONEY : appel API Airtel Africa
    - ESPECES / VIREMENT : enregistrement direct
    """
    reservation = get_object_or_404(Reservation, id=payload.reservation_id)

    # Vérifier que la réservation est validée
    if reservation.statut != 'VALIDEE':
        return {"success": False, "message": "La réservation doit être validée."}

    # Vérifier qu'un paiement confirmé n'existe pas déjà
    deja_paye = Paiement.objects.filter(
        reservation=reservation, statut='CONFIRME'
    ).exists()
    if deja_paye:
        return {"success": False, "message": "Cette réservation est déjà payée."}

    # Validation numéro pour mobile money
    if payload.canal in ('MOBILE_MONEY', 'AIRTEL_MONEY') and not payload.numero_telephone:
        return {"success": False, "message": "Le numéro de téléphone est obligatoire."}

    # Créer le paiement
    paiement = Paiement.objects.create(
        reservation=reservation,
        client=reservation.client,
        canal=payload.canal,
        montant=payload.montant,
        numero_telephone=payload.numero_telephone,
        enregistre_par=request.auth,
    )

    # Traiter selon le canal
    if payload.canal == 'MOBILE_MONEY':
        service = MTNMoMoService()
        resultat = service.initier_paiement(paiement)

    elif payload.canal == 'AIRTEL_MONEY':
        service = AirtelMoneyService()
        resultat = service.initier_paiement(paiement)

    elif payload.canal in ('ESPECES', 'VIREMENT'):
        # Confirmation immédiate pour espèces/virement (agent sur place)
        if request.auth.role not in ('ADMIN', 'AGENT', 'SECRETARIAT'):
            return {"success": False, "message": "Seul le staff peut enregistrer un paiement espèces."}
        paiement.statut = 'CONFIRME'
        paiement.date_confirmation = timezone.now()
        paiement.reference_operateur = f"CAISSE-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        paiement.save()
        resultat = {
            'success': True,
            'message': f'Paiement {payload.canal.lower()} enregistré et confirmé.',
            'transaction_id': str(paiement.id),
        }

        # Mettre à jour le montant de la réservation
        reservation.montant_total = payload.montant
        reservation.save()

        # Notifier le client
        _notifier_paiement_confirme(paiement)

    else:
        return {"success": False, "message": f"Canal inconnu : {payload.canal}"}

    return {
        "success": resultat.get('success', False),
        "paiement_id": str(paiement.id),
        "reference": paiement.reference,
        "message": resultat.get('message', ''),
        "transaction_id": resultat.get('transaction_id', ''),
    }


@router.post("/{paiement_id}/verifier/", auth=AuthBearer())
def verifier_paiement(request, paiement_id: str):
    """
    Vérifie le statut d'un paiement Mobile Money en cours
    Interroge l'API de l'opérateur
    """
    paiement = get_object_or_404(Paiement, id=paiement_id)

    if paiement.statut == 'CONFIRME':
        return {"success": True, "statut": "CONFIRME", "message": "Paiement déjà confirmé."}

    if paiement.canal == 'MOBILE_MONEY':
        service = MTNMoMoService()
        resultat = service.verifier_statut(paiement)
    elif paiement.canal == 'AIRTEL_MONEY':
        service = AirtelMoneyService()
        resultat = service.verifier_statut(paiement)
    else:
        return {"success": False, "statut": paiement.statut, "message": "Vérification non applicable."}

    # Si confirmé, notifier le client
    if resultat.get('statut') == 'CONFIRME':
        reservation = paiement.reservation
        reservation.montant_total = paiement.montant
        reservation.save()
        _notifier_paiement_confirme(paiement)

    return {
        "success": resultat.get('success', False),
        "statut": resultat.get('statut', 'INCONNU'),
        "message": resultat.get('message', ''),
        "paiement_id": str(paiement.id),
        "reference": paiement.reference,
    }


@router.get("/", response=List[PaiementSchema], auth=AuthBearer())
def liste_paiements(request, reservation_id: str = None, statut: str = None):
    """Liste les paiements"""
    if request.auth.role in ('ADMIN', 'AGENT', 'SECRETARIAT'):
        qs = Paiement.objects.select_related('reservation', 'client')
    else:
        qs = Paiement.objects.filter(client=request.auth).select_related('reservation')

    if reservation_id:
        qs = qs.filter(reservation_id=reservation_id)
    if statut:
        qs = qs.filter(statut=statut)

    return [_paiement_dict(p) for p in qs]


@router.get("/stats/", auth=AuthBearer())
def stats_paiements(request):
    """Statistiques financières"""
    if request.auth.role not in ('ADMIN', 'SECRETARIAT'):
        return {"detail": "Accès refusé"}

    from django.db.models import Sum, Count

    total_confirme = Paiement.objects.filter(statut='CONFIRME').aggregate(
        total=Sum('montant'), count=Count('id')
    )
    par_canal = {}
    for canal, _ in Paiement.CANAUX:
        agg = Paiement.objects.filter(statut='CONFIRME', canal=canal).aggregate(
            total=Sum('montant'), count=Count('id')
        )
        par_canal[canal] = {
            'total': float(agg['total'] or 0),
            'count': agg['count'] or 0,
        }

    return {
        'total_revenus': float(total_confirme['total'] or 0),
        'total_transactions': total_confirme['count'] or 0,
        'en_attente': Paiement.objects.filter(statut__in=['EN_ATTENTE', 'INITIE']).count(),
        'echoues': Paiement.objects.filter(statut='ECHOUE').count(),
        'par_canal': par_canal,
    }


@router.post("/{paiement_id}/rembourser/", auth=AuthBearer())
def rembourser(request, paiement_id: str, motif: str = ''):
    """Marque un paiement comme remboursé — Admin seulement"""
    if request.auth.role != 'ADMIN':
        return {"detail": "Accès refusé"}

    paiement = get_object_or_404(Paiement, id=paiement_id)
    paiement.statut = 'REMBOURSE'
    paiement.reponse_api = {**paiement.reponse_api, 'motif_remboursement': motif}
    paiement.save()

    _log(request.auth, 'PAIEMENT_CONFIRME', 'Paiement', paiement_id,
         nouvelle_valeur={'statut': 'REMBOURSE', 'motif': motif})

    return {"success": True, "message": "Paiement marqué comme remboursé."}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _paiement_dict(p: Paiement) -> dict:
    return {
        'id': str(p.id),
        'reference': p.reference,
        'canal': p.canal,
        'statut': p.statut,
        'montant': float(p.montant),
        'devise': p.devise,
        'numero_telephone': p.numero_telephone,
        'reference_operateur': p.reference_operateur,
        'transaction_id_externe': p.transaction_id_externe,
        'reservation_ref': p.reservation.reference,
        'client_nom': p.client.nom_complet,
        'date_initiation': p.date_initiation.strftime('%d/%m/%Y %H:%M'),
        'date_confirmation': p.date_confirmation.strftime('%d/%m/%Y %H:%M') if p.date_confirmation else None,
    }


def _notifier_paiement_confirme(paiement: Paiement):
    try:
        from apps.notifications.models import Notification
        Notification.objects.create(
            destinataire=paiement.client,
            type_notif='FACTURE',
            sujet=f"Paiement {paiement.reference} confirmé",
            contenu=(
                f"Votre paiement de {int(paiement.montant):,} XAF "
                f"via {paiement.get_canal_display()} a été confirmé.\n"
                f"Référence : {paiement.reference}\n"
                f"Réservation : {paiement.reservation.reference}"
            ),
        )
    except Exception:
        pass


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
