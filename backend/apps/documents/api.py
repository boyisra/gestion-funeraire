"""
API Documents PDF — Django Ninja — GI2 2026
Endpoints : facture, certificat inhumation, autorisation exhumation, PV
"""
from ninja import Router
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from apps.auth_users.api import AuthBearer
from apps.paiements.models import Paiement
from apps.reservations.models import Reservation
from apps.concessions.models import DemandeExhumation
from apps.terrain.models import Configuration
from .service_pdf import (
    generer_facture,
    generer_certificat_inhumation,
    generer_autorisation_exhumation,
    generer_pv_exhumation,
)

router = Router(tags=["Documents PDF"])


def _get_config():
    config, _ = Configuration.objects.get_or_create(pk=1)
    return config


@router.get("/facture/{paiement_id}/", auth=AuthBearer())
def telecharger_facture(request, paiement_id: str):
    """Génère et télécharge la facture PDF d'un paiement"""
    paiement = get_object_or_404(Paiement, id=paiement_id)

    # Le client ne peut télécharger que sa propre facture
    if request.auth.role == 'CLIENT' and paiement.client != request.auth:
        return HttpResponse("Accès refusé", status=403)

    if paiement.statut != 'CONFIRME':
        return HttpResponse("Facture disponible uniquement pour les paiements confirmés.", status=400)

    try:
        pdf_bytes = generer_facture(paiement, paiement.reservation, _get_config())
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="facture_{paiement.reference}.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Erreur génération PDF : {str(e)}", status=500)


@router.get("/certificat/{reservation_id}/", auth=AuthBearer())
def telecharger_certificat(request, reservation_id: str):
    """Génère et télécharge le certificat d'inhumation"""
    reservation = get_object_or_404(Reservation, id=reservation_id)

    if request.auth.role == 'CLIENT' and reservation.client != request.auth:
        return HttpResponse("Accès refusé", status=403)

    if reservation.statut != 'VALIDEE':
        return HttpResponse("Certificat disponible uniquement pour les réservations validées.", status=400)

    try:
        pdf_bytes = generer_certificat_inhumation(reservation, _get_config())
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="certificat_{reservation.reference}.pdf"'
        )
        return response
    except Exception as e:
        return HttpResponse(f"Erreur génération PDF : {str(e)}", status=500)


@router.get("/autorisation-exhumation/{exh_id}/", auth=AuthBearer())
def telecharger_autorisation_exhumation(request, exh_id: str):
    """Génère l'autorisation d'exhumation PDF"""
    exh = get_object_or_404(DemandeExhumation, id=exh_id)

    if request.auth.role == 'CLIENT' and exh.demandeur != request.auth:
        return HttpResponse("Accès refusé", status=403)

    if exh.statut not in ('AUTORISEE', 'EXECUTEE'):
        return HttpResponse("L'exhumation doit être autorisée.", status=400)

    try:
        pdf_bytes = generer_autorisation_exhumation(exh, _get_config())
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="autorisation_{exh.reference}.pdf"'
        )
        return response
    except Exception as e:
        return HttpResponse(f"Erreur génération PDF : {str(e)}", status=500)


@router.get("/pv-exhumation/{exh_id}/", auth=AuthBearer())
def telecharger_pv_exhumation(request, exh_id: str):
    """Génère le procès-verbal d'exhumation PDF"""
    exh = get_object_or_404(DemandeExhumation, id=exh_id)

    if request.auth.role not in ('ADMIN', 'AGENT', 'SECRETARIAT'):
        return HttpResponse("Accès refusé", status=403)

    if exh.statut != 'EXECUTEE':
        return HttpResponse("PV disponible uniquement après exécution.", status=400)

    try:
        pdf_bytes = generer_pv_exhumation(exh, _get_config())
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="pv_{exh.reference}.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Erreur génération PDF : {str(e)}", status=500)
