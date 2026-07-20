"""
Modèles Réservations — GI2 2026
Defunt, Reservation
"""
from django.db import models
from django.utils import timezone
import uuid


class Defunt(models.Model):
    """Informations du défunt"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    date_naissance = models.DateField(null=True, blank=True)
    date_deces = models.DateField()
    lieu_deces = models.CharField(max_length=200, blank=True)
    numero_acte_deces = models.CharField(max_length=100, blank=True)
    nationalite = models.CharField(max_length=100, default='Congolaise')
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'defunts'
        verbose_name = 'Défunt'

    def __str__(self):
        return f"{self.prenom} {self.nom} (†{self.date_deces})"

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"


class Reservation(models.Model):
    """Réservation d'un caveau — workflow complet"""
    STATUTS = [
        ('EN_ATTENTE', 'En attente de validation'),
        ('VALIDEE', 'Validée'),
        ('ANNULEE', 'Annulée'),
        ('EXPIREE', 'Expirée'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=30, unique=True, blank=True)
    caveau = models.ForeignKey(
        'terrain.Caveau', on_delete=models.PROTECT, related_name='reservations'
    )
    client = models.ForeignKey(
        'auth_users.Utilisateur', on_delete=models.PROTECT, related_name='reservations'
    )
    defunt = models.OneToOneField(Defunt, on_delete=models.PROTECT)
    statut = models.CharField(max_length=20, choices=STATUTS, default='EN_ATTENTE')

    date_inhumation = models.DateField()
    date_soumission = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    date_expiration = models.DateTimeField(null=True, blank=True)

    valide_par = models.ForeignKey(
        'auth_users.Utilisateur', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reservations_validees'
    )
    notes_admin = models.TextField(blank=True)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'reservations'
        verbose_name = 'Réservation'
        ordering = ['-date_soumission']

    def __str__(self):
        return f"{self.reference} — {self.statut}"

    def save(self, *args, **kwargs):
        if not self.reference:
            annee = timezone.now().year
            self.reference = f"RES-{annee}-{str(self.id)[:6].upper()}"
        # Définir expiration : 48h après soumission
        if not self.date_expiration:
            from datetime import timedelta
            self.date_expiration = timezone.now() + timedelta(hours=48)
        super().save(*args, **kwargs)
