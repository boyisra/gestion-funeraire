"""
API Terrain — Django Ninja — GI2 2026
Endpoints : configuration, zones, caveaux
"""
from typing import List, Optional
from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.auth_users.api import AuthBearer
from .models import Configuration, Zone, Caveau

router = Router(tags=["Terrain"])


# ─── Schémas ─────────────────────────────────────────────────────────────────

class ConfigurationSchema(Schema):
    id: int
    nom_cimetiere: str
    adresse: str
    telephone_contact: str
    email_contact: str
    superficie_totale_m2: float
    taille_caveau_longueur: float
    taille_caveau_largeur: float
    largeur_allee_m: float
    tarif_concession_temporaire: float
    tarif_concession_perpetuelle: float
    places_totales_calculees: int


class ConfigurationUpdateSchema(Schema):
    nom_cimetiere: Optional[str] = None
    adresse: Optional[str] = None
    telephone_contact: Optional[str] = None
    email_contact: Optional[str] = None
    superficie_totale_m2: Optional[float] = None
    taille_caveau_longueur: Optional[float] = None
    taille_caveau_largeur: Optional[float] = None
    largeur_allee_m: Optional[float] = None
    tarif_concession_temporaire: Optional[float] = None
    tarif_concession_perpetuelle: Optional[float] = None


class ZoneSchema(Schema):
    id: str
    nom: str
    code: str
    type_zone: str
    superficie_m2: Optional[float] = None
    description: str
    couleur_carte: str
    latitude_centre: Optional[float] = None
    longitude_centre: Optional[float] = None
    nombre_caveaux: int
    caveaux_disponibles: int
    taux_occupation: float


class ZoneCreateSchema(Schema):
    nom: str
    code: str
    type_zone: str = 'SECTION'
    superficie_m2: Optional[float] = None
    description: str = ''
    couleur_carte: str = '#3b82f6'
    latitude_centre: Optional[float] = None
    longitude_centre: Optional[float] = None


class CaveauSchema(Schema):
    id: str
    zone_id: str
    zone_code: str
    numero: str
    rangee: int
    colonne: int
    etat: str
    couleur: str
    latitude: float
    longitude: float
    superficie_m2: float
    notes: str


class CaveauCreateSchema(Schema):
    zone_id: str
    numero: str
    rangee: int
    colonne: int
    latitude: float = 0
    longitude: float = 0
    superficie_m2: float = 3.0
    notes: str = ''


class CaveauUpdateEtatSchema(Schema):
    etat: str
    notes: str = ''


class StatsTerrainSchema(Schema):
    total_caveaux: int
    disponibles: int
    reserves: int
    occupes: int
    non_exploitables: int
    taux_occupation_global: float
    total_zones: int
    places_calculees: int


# ─── Configuration ───────────────────────────────────────────────────────────

@router.get("/configuration/", response=ConfigurationSchema, auth=AuthBearer())
def get_configuration(request):
    """Retourne la configuration du cimetière"""
    config, _ = Configuration.objects.get_or_create(pk=1)
    return {
        **{f.name: getattr(config, f.name) for f in config._meta.fields},
        'places_totales_calculees': config.calculer_places_totales(),
    }


@router.put("/configuration/", response=ConfigurationSchema, auth=AuthBearer())
def update_configuration(request, payload: ConfigurationUpdateSchema):
    """Met à jour la configuration (Admin seulement)"""
    if request.auth.role != 'ADMIN':
        return {"detail": "Accès refusé"}

    config, _ = Configuration.objects.get_or_create(pk=1)
    for field, value in payload.dict(exclude_none=True).items():
        setattr(config, field, value)
    config.modifie_par = request.auth
    config.save()

    # Audit log
    _log(request.auth, 'MODIFICATION_CONFIG', 'Configuration', '1',
         nouvelle_valeur=payload.dict(exclude_none=True))

    return {
        **{f.name: getattr(config, f.name) for f in config._meta.fields},
        'places_totales_calculees': config.calculer_places_totales(),
    }


# ─── Zones ───────────────────────────────────────────────────────────────────

@router.get("/zones/", response=List[ZoneSchema], auth=AuthBearer())
def liste_zones(request):
    """Liste toutes les zones actives"""
    zones = Zone.objects.filter(active=True).prefetch_related('caveaux')
    return [_zone_to_dict(z) for z in zones]


@router.post("/zones/", response=ZoneSchema, auth=AuthBearer())
def creer_zone(request, payload: ZoneCreateSchema):
    """Crée une nouvelle zone (Admin/Agent)"""
    if request.auth.role not in ('ADMIN', 'AGENT'):
        return {"detail": "Accès refusé"}

    zone = Zone.objects.create(
        **payload.dict(),
        cree_par=request.auth,
    )
    return _zone_to_dict(zone)


@router.get("/zones/{zone_id}/", response=ZoneSchema, auth=AuthBearer())
def get_zone(request, zone_id: str):
    zone = get_object_or_404(Zone, id=zone_id)
    return _zone_to_dict(zone)


@router.delete("/zones/{zone_id}/", auth=AuthBearer())
def supprimer_zone(request, zone_id: str):
    if request.auth.role != 'ADMIN':
        return {"detail": "Accès refusé"}
    zone = get_object_or_404(Zone, id=zone_id)
    zone.active = False
    zone.save()
    return {"success": True}


# ─── Caveaux ─────────────────────────────────────────────────────────────────

@router.get("/caveaux/", response=List[CaveauSchema], auth=AuthBearer())
def liste_caveaux(request, zone_id: str = None, etat: str = None):
    """Liste les caveaux avec filtres optionnels"""
    qs = Caveau.objects.select_related('zone')
    if zone_id:
        qs = qs.filter(zone_id=zone_id)
    if etat:
        qs = qs.filter(etat=etat)
    return [_caveau_to_dict(c) for c in qs]


@router.post("/caveaux/", response=CaveauSchema, auth=AuthBearer())
def creer_caveau(request, payload: CaveauCreateSchema):
    """Crée un caveau (Admin/Agent)"""
    if request.auth.role not in ('ADMIN', 'AGENT'):
        return {"detail": "Accès refusé"}

    zone = get_object_or_404(Zone, id=payload.zone_id)
    data = payload.dict()
    data.pop('zone_id')
    caveau = Caveau.objects.create(zone=zone, modifie_par=request.auth, **data)
    return _caveau_to_dict(caveau)


@router.post("/caveaux/generer/", auth=AuthBearer())
def generer_caveaux(request, zone_id: str, nb_rangees: int, nb_colonnes: int,
                    lat_depart: float = 0, lng_depart: float = 0,
                    espacement_lat: float = 0.00003, espacement_lng: float = 0.00005):
    """
    Génère automatiquement les caveaux d'une zone en grille
    Admin/Agent seulement
    """
    if request.auth.role not in ('ADMIN', 'AGENT'):
        return {"detail": "Accès refusé"}

    zone = get_object_or_404(Zone, id=zone_id)
    caveaux_crees = []

    for r in range(1, nb_rangees + 1):
        for c in range(1, nb_colonnes + 1):
            numero = f"{zone.code}-{str((r-1)*nb_colonnes + c).zfill(3)}"
            lat = lat_depart + (r - 1) * espacement_lat
            lng = lng_depart + (c - 1) * espacement_lng

            caveau, created = Caveau.objects.get_or_create(
                zone=zone,
                numero=numero,
                defaults={
                    'rangee': r,
                    'colonne': c,
                    'latitude': lat,
                    'longitude': lng,
                    'modifie_par': request.auth,
                }
            )
            if created:
                caveaux_crees.append(numero)

    return {
        "success": True,
        "caveaux_crees": len(caveaux_crees),
        "message": f"{len(caveaux_crees)} caveaux générés dans la zone {zone.code}"
    }


@router.patch("/caveaux/{caveau_id}/etat/", response=CaveauSchema, auth=AuthBearer())
def changer_etat_caveau(request, caveau_id: str, payload: CaveauUpdateEtatSchema):
    """Change l'état d'un caveau avec journalisation"""
    if request.auth.role not in ('ADMIN', 'AGENT', 'SECRETARIAT'):
        return {"detail": "Accès refusé"}

    caveau = get_object_or_404(Caveau, id=caveau_id)
    ancien_etat = caveau.etat
    caveau.etat = payload.etat
    if payload.notes:
        caveau.notes = payload.notes
    caveau.modifie_par = request.auth
    caveau.save()

    # Audit log
    _log(request.auth, 'CHANGEMENT_STATUT_CAVEAU', 'Caveau', str(caveau_id),
         ancienne_valeur={'etat': ancien_etat},
         nouvelle_valeur={'etat': payload.etat})

    return _caveau_to_dict(caveau)


# ─── Statistiques ────────────────────────────────────────────────────────────

@router.get("/stats/", response=StatsTerrainSchema, auth=AuthBearer())
def stats_terrain(request):
    """Statistiques globales du terrain"""
    total = Caveau.objects.count()
    disponibles = Caveau.objects.filter(etat='DISPONIBLE').count()
    reserves = Caveau.objects.filter(etat='RESERVE').count()
    occupes = Caveau.objects.filter(etat='OCCUPE').count()
    non_exploit = Caveau.objects.filter(etat='NON_EXPLOITABLE').count()
    taux = round((occupes / total * 100), 1) if total > 0 else 0

    config, _ = Configuration.objects.get_or_create(pk=1)

    return {
        'total_caveaux': total,
        'disponibles': disponibles,
        'reserves': reserves,
        'occupes': occupes,
        'non_exploitables': non_exploit,
        'taux_occupation_global': taux,
        'total_zones': Zone.objects.filter(active=True).count(),
        'places_calculees': config.calculer_places_totales(),
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _zone_to_dict(z: Zone) -> dict:
    return {
        'id': str(z.id),
        'nom': z.nom,
        'code': z.code,
        'type_zone': z.type_zone,
        'superficie_m2': float(z.superficie_m2) if z.superficie_m2 else None,
        'description': z.description,
        'couleur_carte': z.couleur_carte,
        'latitude_centre': float(z.latitude_centre) if z.latitude_centre else None,
        'longitude_centre': float(z.longitude_centre) if z.longitude_centre else None,
        'nombre_caveaux': z.nombre_caveaux,
        'caveaux_disponibles': z.caveaux_disponibles,
        'taux_occupation': z.taux_occupation,
    }


def _caveau_to_dict(c: Caveau) -> dict:
    return {
        'id': str(c.id),
        'zone_id': str(c.zone_id),
        'zone_code': c.zone.code,
        'numero': c.numero,
        'rangee': c.rangee,
        'colonne': c.colonne,
        'etat': c.etat,
        'couleur': c.couleur,
        'latitude': float(c.latitude),
        'longitude': float(c.longitude),
        'superficie_m2': float(c.superficie_m2),
        'notes': c.notes,
    }


def _log(user, action, obj_type, obj_id, ancienne_valeur=None, nouvelle_valeur=None):
    try:
        from apps.auth_users.models import AuditLog
        AuditLog.objects.create(
            utilisateur=user,
            action=action,
            objet_type=obj_type,
            objet_id=obj_id,
            ancienne_valeur=ancienne_valeur or {},
            nouvelle_valeur=nouvelle_valeur or {},
        )
    except Exception:
        pass
