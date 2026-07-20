"""
Modèles Paiements — GI2 2026
Paiement multi-canaux : Mobile Money, Airtel Money, Espèces, Virement
"""
from django.db import models
from django.utils import timezone
import uuid


class Paiement(models.Model):
    CANAUX = [
        ('MOBILE_MONEY', 'Mobile Money (MTN)'),
        ('AIRTEL_MONEY', 'Airtel Money'),
        ('ESPECES',      'Espèces'),
        ('VIREMENT',     'Virement bancaire'),
    ]
    STATUTS = [
        ('EN_ATTENTE', 'En attente'),
        ('INITIE',     'Initié'),
        ('CONFIRME',   'Confirmé'),
        ('ECHOUE',     'Échoué'),
        ('REMBOURSE',  'Remboursé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=30, unique=True, blank=True)
    reservation = models.ForeignKey(
        'reservations.Reservation', on_delete=models.PROTECT, related_name='paiements'
    )
    client = models.ForeignKey(
        'auth_users.Utilisateur', on_delete=models.PROTECT, related_name='paiements'
    )
    canal = models.CharField(max_length=20, choices=CANAUX)
    statut = models.CharField(max_length=20, choices=STATUTS, default='EN_ATTENTE')

    montant = models.DecimalField(max_digits=12, decimal_places=2)
    devise = models.CharField(max_length=3, default='XAF')
    numero_telephone = models.CharField(max_length=20, blank=True)

    # Références opérateur
    reference_operateur = models.CharField(max_length=100, blank=True)
    transaction_id_externe = models.CharField(max_length=200, blank=True)

    date_initiation = models.DateTimeField(auto_now_add=True)
    date_confirmation = models.DateTimeField(null=True, blank=True)

    reponse_api = models.JSONField(default=dict, blank=True)
    enregistre_par = models.ForeignKey(
        'auth_users.Utilisateur', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='paiements_enregistres'
    )

    class Meta:
        db_table = 'paiements'
        verbose_name = 'Paiement'
        ordering = ['-date_initiation']

    def __str__(self):
        return f"{self.reference} — {self.montant} {self.devise} ({self.statut})"

    def save(self, *args, **kwargs):
        if not self.reference:
            annee = timezone.now().year
            self.reference = f"PAY-{annee}-{str(self.id)[:6].upper()}"
        super().save(*args, **kwargs)


class TransactionMobileMoney(models.Model):
    """Historique détaillé des appels API opérateurs"""
    TYPES = [
        ('DEBIT',   'Débit client'),
        ('WEBHOOK', 'Webhook reçu'),
        ('STATUT',  'Vérification statut'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paiement = models.ForeignKey(
        Paiement, on_delete=models.CASCADE, related_name='transactions'
    )
    type_operation = models.CharField(max_length=20, choices=TYPES)
    url_appelee = models.CharField(max_length=500)
    payload_envoi = models.JSONField(default=dict)
    reponse = models.JSONField(default=dict)
    code_http = models.IntegerField()
    duree_ms = models.IntegerField(default=0)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transactions_mm'
        verbose_name = 'Transaction Mobile Money'
        ordering = ['-cree_le']
