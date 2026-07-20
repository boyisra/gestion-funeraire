"""
Modèle Notifications — GI2 2026
"""
from django.db import models
import uuid


class Notification(models.Model):
    TYPES = [
        ('MFA',                    'Code MFA'),
        ('CONFIRMATION_RESERVATION','Confirmation réservation'),
        ('FACTURE',                'Facture'),
        ('ALERTE_EXPIRATION',      'Alerte expiration concession'),
        ('ALERTE_PLACES',          'Alerte places critiques'),
        ('RETARD_PAIEMENT',        'Retard de paiement'),
        ('VALIDATION_RESERVATION', 'Validation réservation'),
        ('ANNULATION_RESERVATION', 'Annulation réservation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destinataire = models.ForeignKey(
        'auth_users.Utilisateur', on_delete=models.CASCADE,
        related_name='notifications'
    )
    type_notif = models.CharField(max_length=30, choices=TYPES)
    sujet = models.CharField(max_length=200)
    contenu = models.TextField()
    contenu_html = models.TextField(blank=True)

    envoyee = models.BooleanField(default=False)
    lue = models.BooleanField(default=False)
    date_envoi = models.DateTimeField(null=True, blank=True)
    erreur = models.TextField(blank=True)
    tentatives = models.IntegerField(default=0)

    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notification'
        ordering = ['-cree_le']

    def __str__(self):
        return f"{self.type_notif} → {self.destinataire.email} ({'envoyée' if self.envoyee else 'en attente'})"
