"""
API Rapports & Statistiques — Django Ninja — GI2 2026
Dashboard, exports CSV/Excel
"""
from ninja import Router, Schema
from typing import List, Optional
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import HttpResponse

from apps.auth_users.api import AuthBearer

router = Router(tags=["Rapports"])


class DashboardSchema(Schema):
    # Terrain
    total_caveaux: int
    caveaux_disponibles: int
    caveaux_reserves: int
    caveaux_occupes: int
    taux_occupation: float
    places_calculees: int
    # Réservations
    reservations_total: int
    reservations_en_attente: int
    reservations_validees: int
    reservations_mois: int
    # Paiements
    revenus_total: float
    revenus_mois: float
    paiements_en_attente: int
    # Concessions
    concessions_actives: int
    concessions_expirant: int
    # Exhumations
    exhumations_en_cours: int


@router.get("/dashboard/", response=DashboardSchema, auth=AuthBearer())
def get_dashboard(request):
    """Données complètes du tableau de bord"""
    if request.auth.role not in ('ADMIN', 'AGENT', 'SECRETARIAT'):
        return {"detail": "Accès refusé"}

    from apps.terrain.models import Caveau, Configuration
    from apps.reservations.models import Reservation
    from apps.paiements.models import Paiement
    from apps.concessions.models import Concession, DemandeExhumation

    maintenant = timezone.now()
    debut_mois = maintenant.replace(day=1, hour=0, minute=0, second=0)
    dans_90j = maintenant.date() + timezone.timedelta(days=90)

    # Terrain
    total_caveaux      = Caveau.objects.count()
    caveaux_disponibles = Caveau.objects.filter(etat='DISPONIBLE').count()
    caveaux_reserves   = Caveau.objects.filter(etat='RESERVE').count()
    caveaux_occupes    = Caveau.objects.filter(etat='OCCUPE').count()
    taux = round((caveaux_occupes / total_caveaux * 100), 1) if total_caveaux > 0 else 0
    config, _ = Configuration.objects.get_or_create(pk=1)

    # Réservations
    res_total      = Reservation.objects.count()
    res_en_attente = Reservation.objects.filter(statut='EN_ATTENTE').count()
    res_validees   = Reservation.objects.filter(statut='VALIDEE').count()
    res_mois       = Reservation.objects.filter(date_soumission__gte=debut_mois).count()

    # Paiements
    revenus = Paiement.objects.filter(statut='CONFIRME').aggregate(total=Sum('montant'))
    revenus_mois = Paiement.objects.filter(
        statut='CONFIRME', date_confirmation__gte=debut_mois
    ).aggregate(total=Sum('montant'))
    paie_attente = Paiement.objects.filter(statut__in=['EN_ATTENTE', 'INITIE']).count()

    # Concessions
    con_actives  = Concession.objects.filter(statut='ACTIVE').count()
    con_expirant = Concession.objects.filter(
        statut='ACTIVE', date_fin__lte=dans_90j, date_fin__gte=maintenant.date()
    ).count()

    # Exhumations
    exh_cours = DemandeExhumation.objects.filter(
        statut__in=['SOUMISE', 'EN_INSTRUCTION', 'AUTORISEE']
    ).count()

    return {
        'total_caveaux':        total_caveaux,
        'caveaux_disponibles':  caveaux_disponibles,
        'caveaux_reserves':     caveaux_reserves,
        'caveaux_occupes':      caveaux_occupes,
        'taux_occupation':      taux,
        'places_calculees':     config.calculer_places_totales(),
        'reservations_total':   res_total,
        'reservations_en_attente': res_en_attente,
        'reservations_validees': res_validees,
        'reservations_mois':    res_mois,
        'revenus_total':        float(revenus['total'] or 0),
        'revenus_mois':         float(revenus_mois['total'] or 0),
        'paiements_en_attente': paie_attente,
        'concessions_actives':  con_actives,
        'concessions_expirant': con_expirant,
        'exhumations_en_cours': exh_cours,
    }


@router.get("/occupation-par-zone/", auth=AuthBearer())
def occupation_par_zone(request):
    """Taux d'occupation par zone"""
    if request.auth.role not in ('ADMIN', 'AGENT', 'SECRETARIAT'):
        return {"detail": "Accès refusé"}

    from apps.terrain.models import Zone
    zones = Zone.objects.filter(active=True).prefetch_related('caveaux')
    return [
        {
            'zone': z.code,
            'nom': z.nom,
            'total': z.nombre_caveaux,
            'disponibles': z.caveaux_disponibles,
            'occupes': z.caveaux.filter(etat='OCCUPE').count(),
            'taux': z.taux_occupation,
            'couleur': z.couleur_carte,
        }
        for z in zones
    ]


@router.get("/revenus-par-canal/", auth=AuthBearer())
def revenus_par_canal(request):
    """Revenus par canal de paiement"""
    if request.auth.role not in ('ADMIN', 'SECRETARIAT'):
        return {"detail": "Accès refusé"}

    from apps.paiements.models import Paiement
    canaux = ['MOBILE_MONEY', 'AIRTEL_MONEY', 'ESPECES', 'VIREMENT']
    result = []
    for canal in canaux:
        agg = Paiement.objects.filter(
            statut='CONFIRME', canal=canal
        ).aggregate(total=Sum('montant'), count=Count('id'))
        result.append({
            'canal': canal,
            'total': float(agg['total'] or 0),
            'count': agg['count'] or 0,
        })
    return result


@router.get("/export/reservations/", auth=AuthBearer())
def export_reservations_csv(request):
    """Export CSV du registre des réservations"""
    if request.auth.role not in ('ADMIN', 'SECRETARIAT'):
        return HttpResponse("Accès refusé", status=403)

    import csv
    from apps.reservations.models import Reservation

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="reservations_gi2.csv"'
    response.write('\ufeff')  # BOM UTF-8 pour Excel

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Référence', 'Statut', 'Client', 'Email client',
        'Défunt', 'Date décès', 'Date inhumation',
        'Caveau', 'Zone', 'Montant (XAF)',
        'Date soumission', 'Date validation',
    ])

    reservations = Reservation.objects.select_related(
        'client', 'defunt', 'caveau', 'caveau__zone'
    ).order_by('-date_soumission')

    for r in reservations:
        writer.writerow([
            r.reference,
            r.statut,
            r.client.nom_complet,
            r.client.email,
            f"{r.defunt.prenom} {r.defunt.nom}",
            str(r.defunt.date_deces),
            str(r.date_inhumation),
            r.caveau.numero,
            r.caveau.zone.code,
            int(r.montant_total),
            r.date_soumission.strftime('%d/%m/%Y %H:%M'),
            r.date_validation.strftime('%d/%m/%Y %H:%M') if r.date_validation else '',
        ])

    return response


@router.get("/export/paiements/", auth=AuthBearer())
def export_paiements_csv(request):
    """Export CSV des paiements"""
    if request.auth.role not in ('ADMIN', 'SECRETARIAT'):
        return HttpResponse("Accès refusé", status=403)

    import csv
    from apps.paiements.models import Paiement

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="paiements_gi2.csv"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Référence', 'Statut', 'Canal', 'Montant (XAF)',
        'Client', 'Réservation', 'Réf. opérateur',
        'Date initiation', 'Date confirmation',
    ])

    paiements = Paiement.objects.select_related(
        'client', 'reservation'
    ).order_by('-date_initiation')

    for p in paiements:
        writer.writerow([
            p.reference,
            p.statut,
            p.get_canal_display(),
            int(p.montant),
            p.client.nom_complet,
            p.reservation.reference,
            p.reference_operateur,
            p.date_initiation.strftime('%d/%m/%Y %H:%M'),
            p.date_confirmation.strftime('%d/%m/%Y %H:%M') if p.date_confirmation else '',
        ])

    return response


@router.get("/export/concessions/", auth=AuthBearer())
def export_concessions_csv(request):
    """Export CSV du registre des concessions"""
    if request.auth.role not in ('ADMIN', 'SECRETARIAT'):
        return HttpResponse("Accès refusé", status=403)

    import csv
    from apps.concessions.models import Concession

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="concessions_gi2.csv"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Référence', 'Type', 'Statut', 'Titulaire', 'Email',
        'Caveau', 'Zone', 'Prix (XAF)',
        'Date début', 'Date fin', 'Jours restants',
    ])

    concessions = Concession.objects.select_related(
        'titulaire', 'reservation__caveau__zone'
    ).order_by('-cree_le')

    for c in concessions:
        writer.writerow([
            c.reference,
            c.get_type_concession_display(),
            c.statut,
            c.titulaire.nom_complet,
            c.titulaire.email,
            c.reservation.caveau.numero,
            c.reservation.caveau.zone.code,
            int(c.prix_total),
            str(c.date_debut),
            str(c.date_fin) if c.date_fin else 'Perpétuelle',
            str(c.jours_restants) if c.jours_restants is not None else 'N/A',
        ])

    return response
