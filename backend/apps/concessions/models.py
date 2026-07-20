"""
Modèles Concessions & Exhumations — GI2 2026
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta
import uuid


class Concession(models.Model):
    """Contrat de concession funéraire"""
    TYPES = [
        ('TEMPORAIRE',    'Temporaire (5 ans)'),
        ('RENOUVELABLE',  'Renouvelable (15 ans)'),
        ('PERPETUELLE',   'Perpétuelle'),
    ]
    STATUTS = [
        ('ACTIVE',            'Active'),
        ('EXPIREE',           'Expirée'),
        ('RESILIEE',          'Résiliée'),
        ('EN_RENOUVELLEMENT', 'En cours de renouvellement'),
    ]

    DUREES_ANNEES = {
        'TEMPORAIRE':   5,
        'RENOUVELABLE': 15,
        'PERPETUELLE':  None,
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=30, unique=True, blank=True)
    reservation = models.OneToOneField(
        'reservations.Reservation', on_delete=models.PROTECT, related_name='concession'
    )
    titulaire = models.ForeignKey(
        'auth_users.Utilisateur', on_delete=models.PROTECT, related_name='concessions'
    )
    type_concession = models.CharField(max_length=20, choices=TYPES)
    statut = models.CharField(max_length=20, choices=STATUTS, default='ACTIVE')

    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)   # NULL = perpétuelle
    date_alerte = models.DateField(null=True, blank=True) # 3 mois avant expiration

    prix_total = models.DecimalField(max_digits=12, decimal_places=2)
    documents_legaux = models.FileField(upload_to='concessions/docs/', blank=True)

    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)
    cree_par = models.ForeignKey(
        'auth_users.Utilisateur', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='concessions_creees'
    )

    class Meta:
        db_table = 'concessions'
        verbose_name = 'Concession'
        ordering = ['-cree_le']

    def __str__(self):
        return f"{self.reference} — {self.type_concession} ({self.statut})"

    def save(self, *args, **kwargs):
        if not self.reference:
            annee = timezone.now().year
            self.reference = f"CON-{annee}-{str(self.id)[:6].upper()}"

        # Calculer date_fin selon le type
        if not self.date_fin and self.type_concession != 'PERPETUELLE':
            duree = self.DUREES_ANNEES.get(self.type_concession, 5)
            from dateutil.relativedelta import relativedelta
            try:
                self.date_fin = self.date_debut + relativedelta(years=duree)
            except Exception:
                from datetime import date
                self.date_fin = date(
                    self.date_debut.year + duree,
                    self.date_debut.month,
                    self.date_debut.day
                )

        # Alerte 3 mois avant expiration
        if self.date_fin and not self.date_alerte:
            from datetime import timedelta
            self.date_alerte = self.date_fin - timedelta(days=90)

        super().save(*args, **kwargs)

    @property
    def jours_restants(self):
        if not self.date_fin:
            return None
        delta = self.date_fin - timezone.now().date()
        return delta.days

    @property
    def est_expiree(self):
        if not self.date_fin:
            return False
        return timezone.now().date() > self.date_fin


class DemandeExhumation(models.Model):
    """Demande d'exhumation avec validation administrative"""
    STATUTS = [
        ('SOUMISE',        'Soumise'),
        ('EN_INSTRUCTION', 'En instruction'),
        ('AUTORISEE',      'Autorisée'),
        ('REFUSEE',        'Refusée'),
        ('EXECUTEE',       'Exécutée'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=30, unique=True, blank=True)
    concession = models.ForeignKey(
        Concession, on_delete=models.PROTECT, related_name='exhumations'
    )
    demandeur = models.ForeignKey(
        'auth_users.Utilisateur', on_delete=models.PROTECT, related_name='exhumations_demandees'
    )
    motif = models.TextField()
    statut = models.CharField(max_length=20, choices=STATUTS, default='SOUMISE')

    date_demande = models.DateTimeField(auto_now_add=True)
    date_execution_prevue = models.DateField(null=True, blank=True)
    date_execution_reelle = models.DateField(null=True, blank=True)

    autorise_par = models.ForeignKey(
        'auth_users.Utilisateur', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='exhumations_autorisees'
    )
    notes_admin = models.TextField(blank=True)
    autorisation_pdf = models.FileField(upload_to='exhumations/autorisations/', blank=True)
    pv_pdf = models.FileField(upload_to='exhumations/pv/', blank=True)

    class Meta:
        db_table = 'exhumations'
        verbose_name = "Demande d'exhumation"
        ordering = ['-date_demande']

    def __str__(self):
        return f"{self.reference} — {self.statut}"

    def save(self, *args, **kwargs):
        if not self.reference:
            annee = timezone.now().year
            self.reference = f"EXH-{annee}-{str(self.id)[:6].upper()}"
        super().save(*args, **kwargs)
