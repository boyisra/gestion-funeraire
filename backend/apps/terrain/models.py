"""
Modèles Terrain — GI2 2026
Zone, Caveau, Configuration du cimetière
"""
from django.db import models
import uuid
import math


class Configuration(models.Model):
    """Paramétrage global du cimetière (1 seule ligne)"""
    nom_cimetiere = models.CharField(max_length=200, default="Cimetière GI2")
    adresse = models.TextField(default="")
    telephone_contact = models.CharField(max_length=20, default="")
    email_contact = models.EmailField(default="")

    # Dimensions
    superficie_totale_m2 = models.DecimalField(max_digits=12, decimal_places=2, default=10000)
    taille_caveau_longueur = models.DecimalField(max_digits=5, decimal_places=2, default=2.5)
    taille_caveau_largeur = models.DecimalField(max_digits=5, decimal_places=2, default=1.2)
    largeur_allee_m = models.DecimalField(max_digits=5, decimal_places=2, default=1.5)

    # Tarifs (XAF)
    tarif_concession_temporaire = models.DecimalField(max_digits=10, decimal_places=2, default=150000)
    tarif_concession_perpetuelle = models.DecimalField(max_digits=10, decimal_places=2, default=500000)

    modifie_le = models.DateTimeField(auto_now=True)
    modifie_par = models.ForeignKey(
        'auth_users.Utilisateur',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        db_table = 'configurations'
        verbose_name = 'Configuration'

    def __str__(self):
        return self.nom_cimetiere

    def calculer_places_totales(self) -> int:
        """Calcule le nombre de caveaux possibles sur la superficie totale"""
        superficie = float(self.superficie_totale_m2)
        longueur = float(self.taille_caveau_longueur)
        largeur = float(self.taille_caveau_largeur)
        allee = float(self.largeur_allee_m)

        # Surface par caveau incluant sa part d'allée
        surface_par_caveau = (longueur + allee) * (largeur + allee)

        # 20% déduit pour zones non exploitables (chemins principaux, bâtiments)
        superficie_exploitable = superficie * 0.80

        return math.floor(superficie_exploitable / surface_par_caveau)


class Zone(models.Model):
    """Section / Bloc du cimetière"""
    TYPES = [
        ('SECTION', 'Section'),
        ('BLOC', 'Bloc'),
        ('ALLEE', 'Allée principale'),
        ('NON_EXPLOITABLE', 'Zone non exploitable'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)  # Ex: A, B, C, BL1
    type_zone = models.CharField(max_length=20, choices=TYPES, default='SECTION')
    superficie_m2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    couleur_carte = models.CharField(max_length=7, default='#3b82f6')  # Hex color

    # Coordonnées centre de la zone (pour la carte)
    latitude_centre = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude_centre = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)

    active = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey(
        'auth_users.Utilisateur',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        db_table = 'zones'
        verbose_name = 'Zone'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} — {self.nom}"

    @property
    def nombre_caveaux(self):
        return self.caveaux.count()

    @property
    def caveaux_disponibles(self):
        return self.caveaux.filter(etat='DISPONIBLE').count()

    @property
    def taux_occupation(self):
        total = self.nombre_caveaux
        if total == 0:
            return 0
        occupes = self.caveaux.filter(etat='OCCUPE').count()
        return round((occupes / total) * 100, 1)


class Caveau(models.Model):
    """Emplacement funéraire individuel"""
    ETATS = [
        ('DISPONIBLE', 'Disponible'),
        ('RESERVE', 'Réservé / En attente'),
        ('OCCUPE', 'Occupé / Validé'),
        ('NON_EXPLOITABLE', 'Non exploitable'),
        ('ENTRETIEN', 'En entretien'),
    ]

    COULEURS_ETATS = {
        'DISPONIBLE': '#22c55e',
        'RESERVE': '#f97316',
        'OCCUPE': '#ef4444',
        'NON_EXPLOITABLE': '#6b7280',
        'ENTRETIEN': '#a78bfa',
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='caveaux')
    numero = models.CharField(max_length=20)   # Ex: A-001, B-042
    rangee = models.IntegerField(default=1)
    colonne = models.IntegerField(default=1)
    etat = models.CharField(max_length=20, choices=ETATS, default='DISPONIBLE')

    # Coordonnées GPS
    latitude = models.DecimalField(max_digits=10, decimal_places=8, default=0)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, default=0)

    superficie_m2 = models.DecimalField(max_digits=6, decimal_places=2, default=3.0)
    profondeur_m = models.DecimalField(max_digits=4, decimal_places=2, default=1.8)
    notes = models.TextField(blank=True)

    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)
    modifie_par = models.ForeignKey(
        'auth_users.Utilisateur',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='caveaux_modifies'
    )

    class Meta:
        db_table = 'caveaux'
        unique_together = [['zone', 'numero']]
        verbose_name = 'Caveau'
        ordering = ['zone', 'rangee', 'colonne']

    def __str__(self):
        return f"Caveau {self.numero} ({self.etat})"

    @property
    def couleur(self):
        return self.COULEURS_ETATS.get(self.etat, '#6b7280')
