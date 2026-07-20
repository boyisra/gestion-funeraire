"""
MODÈLES COMPLETS — Application de Gestion de Cimetière GI2 2026

Ce fichier contient TOUS les modèles du projet répartis par application.
Chaque section correspond à une app Django dans apps/
"""

# ===========================================================================
# APP: auth_users  →  apps/auth_users/models.py
# ===========================================================================
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import uuid


class UtilisateurManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'ADMIN')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    ROLES = [
        ('ADMIN', 'Administrateur'),
        ('AGENT', 'Agent de terrain'),
        ('SECRETARIAT', 'Secrétariat'),
        ('CLIENT', 'Client / Citoyen'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=ROLES, default='CLIENT')

    # MFA
    mfa_active = models.BooleanField(default=True)
    mfa_secret = models.CharField(max_length=64, blank=True)  # Clé TOTP

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    derniere_connexion_ip = models.GenericIPAddressField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom', 'prenom']
    objects = UtilisateurManager()

    class Meta:
        db_table = 'users'
        verbose_name = 'Utilisateur'

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.role})"

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"


class TokenMFA(models.Model):
    """Codes MFA envoyés par email (6 chiffres, durée 10 min)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey('Utilisateur', on_delete=models.CASCADE, related_name='tokens_mfa')
    code = models.CharField(max_length=6)
    expiration = models.DateTimeField()
    utilise = models.BooleanField(default=False)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mfa_tokens'
"""


# ===========================================================================
# APP: terrain  →  apps/terrain/models.py
# ===========================================================================
"""
from django.contrib.gis.db import models as gis_models
from django.db import models
import uuid


class Configuration(models.Model):
    '''Paramétrage global du cimetière (1 seule ligne)'''
    superficie_totale_m2 = models.DecimalField(max_digits=12, decimal_places=2)
    taille_caveau_longueur = models.DecimalField(max_digits=5, decimal_places=2, help_text="en mètres")
    taille_caveau_largeur = models.DecimalField(max_digits=5, decimal_places=2, help_text="en mètres")
    largeur_allee_m = models.DecimalField(max_digits=5, decimal_places=2, default=1.5)
    nom_cimetiere = models.CharField(max_length=200)
    adresse = models.TextField()
    telephone_contact = models.CharField(max_length=20)
    email_contact = models.EmailField()
    tarif_concession_temporaire = models.DecimalField(max_digits=10, decimal_places=2, help_text="XAF")
    tarif_concession_perpetuelle = models.DecimalField(max_digits=10, decimal_places=2, help_text="XAF")
    modifie_le = models.DateTimeField(auto_now=True)
    modifie_par = models.ForeignKey('auth_users.Utilisateur', on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'configurations'
        verbose_name = 'Configuration du cimetière'

    def __str__(self):
        return self.nom_cimetiere


class Zone(models.Model):
    '''Section / Bloc du cimetière (ex: Section A, Bloc B2)'''
    TYPES = [
        ('SECTION', 'Section'),
        ('BLOC', 'Bloc'),
        ('ALLEE', 'Allée'),
        ('NON_EXPLOITABLE', 'Zone non exploitable'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    type_zone = models.CharField(max_length=20, choices=TYPES)
    superficie_m2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    geometrie = gis_models.PolygonField(srid=4326, null=True, blank=True)  # PostGIS
    cree_le = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey('auth_users.Utilisateur', on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'zones'
        verbose_name = 'Zone'

    def __str__(self):
        return f"{self.nom} ({self.get_type_zone_display()})"


class Caveau(models.Model):
    '''Emplacement funéraire individuel'''
    ETATS = [
        ('DISPONIBLE', 'Disponible'),       # Vert
        ('RESERVE', 'Réservé / En attente'), # Orange
        ('OCCUPE', 'Occupé / Validé'),       # Rouge
        ('NON_EXPLOITABLE', 'Non exploitable'), # Gris
        ('ENTRETIEN', 'En entretien'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='caveaux')
    numero = models.CharField(max_length=20)  # Ex: A-001, B-042
    rangee = models.IntegerField()
    colonne = models.IntegerField()
    etat = models.CharField(max_length=20, choices=ETATS, default='DISPONIBLE')

    # Géolocalisation PostGIS
    coordonnees = gis_models.PointField(srid=4326)
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)

    superficie_m2 = models.DecimalField(max_digits=6, decimal_places=2)
    profondeur_m = models.DecimalField(max_digits=4, decimal_places=2, default=1.8)
    notes = models.TextField(blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'caveaux'
        unique_together = [['zone', 'numero']]
        verbose_name = 'Caveau'

    def __str__(self):
        return f"Caveau {self.numero} — {self.etat}"

    @property
    def couleur_carte(self):
        couleurs = {
            'DISPONIBLE': '#22c55e',       # Vert
            'RESERVE': '#f97316',          # Orange
            'OCCUPE': '#ef4444',           # Rouge
            'NON_EXPLOITABLE': '#6b7280',  # Gris
            'ENTRETIEN': '#a78bfa',        # Violet
        }
        return couleurs.get(self.etat, '#6b7280')
"""


# ===========================================================================
# APP: reservations  →  apps/reservations/models.py
# ===========================================================================
"""
from django.db import models
import uuid


class Defunt(models.Model):
    '''Informations du défunt (données sensibles)'''
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


class Reservation(models.Model):
    '''Réservation d'un caveau — workflow complet'''
    STATUTS = [
        ('EN_ATTENTE', 'En attente de validation'),   # Orange
        ('VALIDEE', 'Validée'),                        # Rouge (caveau occupé)
        ('ANNULEE', 'Annulée'),
        ('EXPIREE', 'Expirée (non payée)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=20, unique=True)  # Ex: RES-2026-00042
    caveau = models.ForeignKey('terrain.Caveau', on_delete=models.PROTECT, related_name='reservations')
    client = models.ForeignKey('auth_users.Utilisateur', on_delete=models.PROTECT, related_name='reservations')
    defunt = models.OneToOneField(Defunt, on_delete=models.PROTECT)
    statut = models.CharField(max_length=20, choices=STATUTS, default='EN_ATTENTE')

    # Dates
    date_inhumation = models.DateField()
    date_soumission = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    date_expiration = models.DateTimeField(null=True, blank=True)

    # Admin
    valide_par = models.ForeignKey(
        'auth_users.Utilisateur',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reservations_validees'
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
            from django.utils import timezone
            annee = timezone.now().year
            # Auto-incrément géré ailleurs, simplifié ici
            self.reference = f"RES-{annee}-{str(self.id)[:6].upper()}"
        super().save(*args, **kwargs)
"""


# ===========================================================================
# APP: paiements  →  apps/paiements/models.py
# ===========================================================================
"""
from django.db import models
import uuid


class Paiement(models.Model):
    '''Paiement d'une réservation — multi-canaux'''
    CANAUX = [
        ('MOBILE_MONEY', 'Mobile Money (MTN)'),
        ('AIRTEL_MONEY', 'Airtel Money'),
        ('ESPECES', 'Espèces'),
        ('VIREMENT', 'Virement bancaire'),
    ]
    STATUTS = [
        ('EN_ATTENTE', 'En attente'),
        ('INITIE', 'Initié'),
        ('CONFIRME', 'Confirmé'),
        ('ECHOUE', 'Échoué'),
        ('REMBOURSE', 'Remboursé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=30, unique=True)  # PAY-2026-XXXXXX
    reservation = models.ForeignKey('reservations.Reservation', on_delete=models.PROTECT, related_name='paiements')
    client = models.ForeignKey('auth_users.Utilisateur', on_delete=models.PROTECT)
    canal = models.CharField(max_length=20, choices=CANAUX)
    statut = models.CharField(max_length=20, choices=STATUTS, default='EN_ATTENTE')

    montant = models.DecimalField(max_digits=12, decimal_places=2)
    devise = models.CharField(max_length=3, default='XAF')
    numero_telephone = models.CharField(max_length=20, blank=True, help_text="Numéro Mobile Money")

    # Références opérateur
    reference_operateur = models.CharField(max_length=100, blank=True)
    transaction_id_externe = models.CharField(max_length=200, blank=True)

    date_initiation = models.DateTimeField(auto_now_add=True)
    date_confirmation = models.DateTimeField(null=True, blank=True)

    # Réponse brute de l'API
    reponse_api = models.JSONField(default=dict, blank=True)

    enregistre_par = models.ForeignKey(
        'auth_users.Utilisateur',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='paiements_enregistres'
    )

    class Meta:
        db_table = 'paiements'
        verbose_name = 'Paiement'
        ordering = ['-date_initiation']

    def __str__(self):
        return f"{self.reference} — {self.montant} {self.devise} ({self.statut})"


class TransactionMobileMoney(models.Model):
    '''Historique détaillé des appels API Mobile Money / Airtel'''
    TYPES = [('DEBIT', 'Débit client'), ('WEBHOOK', 'Webhook reçu'), ('STATUT', 'Vérification statut')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paiement = models.ForeignKey(Paiement, on_delete=models.CASCADE, related_name='transactions')
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
"""


# ===========================================================================
# APP: concessions  →  apps/concessions/models.py
# ===========================================================================
"""
from django.db import models
import uuid


class Concession(models.Model):
    '''Contrat de concession funéraire'''
    TYPES = [
        ('TEMPORAIRE', 'Temporaire (5 ans)'),
        ('RENOUVELABLE', 'Renouvelable (15 ans)'),
        ('PERPETUELLE', 'Perpétuelle'),
    ]
    STATUTS = [
        ('ACTIVE', 'Active'),
        ('EXPIREE', 'Expirée'),
        ('RESILIEE', 'Résiliée'),
        ('EN_RENOUVELLEMENT', 'En cours de renouvellement'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=30, unique=True)  # CON-2026-XXXXX
    reservation = models.OneToOneField('reservations.Reservation', on_delete=models.PROTECT)
    titulaire = models.ForeignKey('auth_users.Utilisateur', on_delete=models.PROTECT, related_name='concessions')
    type_concession = models.CharField(max_length=20, choices=TYPES)
    statut = models.CharField(max_length=20, choices=STATUTS, default='ACTIVE')

    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)  # NULL = perpétuelle
    date_alerte = models.DateField(null=True, blank=True)  # 3 mois avant expiration

    prix_total = models.DecimalField(max_digits=12, decimal_places=2)
    documents_legaux = models.FileField(upload_to='concessions/docs/', blank=True)

    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)
    cree_par = models.ForeignKey(
        'auth_users.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        related_name='concessions_creees'
    )

    class Meta:
        db_table = 'concessions'
        verbose_name = 'Concession'


class DemandeExhumation(models.Model):
    '''Demande d'exhumation avec validation admin'''
    STATUTS = [
        ('SOUMISE', 'Soumise'),
        ('EN_INSTRUCTION', 'En instruction'),
        ('AUTORISEE', 'Autorisée'),
        ('REFUSEE', 'Refusée'),
        ('EXECUTEE', 'Exécutée'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    concession = models.ForeignKey(Concession, on_delete=models.PROTECT, related_name='exhumations')
    demandeur = models.ForeignKey('auth_users.Utilisateur', on_delete=models.PROTECT)
    motif = models.TextField()
    statut = models.CharField(max_length=20, choices=STATUTS, default='SOUMISE')

    date_demande = models.DateTimeField(auto_now_add=True)
    date_execution_prevue = models.DateField(null=True, blank=True)
    date_execution_reelle = models.DateField(null=True, blank=True)

    autorise_par = models.ForeignKey(
        'auth_users.Utilisateur',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='exhumations_autorisees'
    )
    notes_admin = models.TextField(blank=True)
    autorisation_pdf = models.FileField(upload_to='exhumations/autorisations/', blank=True)
    pv_pdf = models.FileField(upload_to='exhumations/pv/', blank=True)

    class Meta:
        db_table = 'exhumations'
        verbose_name = "Demande d'exhumation"


# ===========================================================================
# APP: notifications  →  apps/notifications/models.py
# ===========================================================================

class Notification(models.Model):
    TYPES = [
        ('MFA', 'Code MFA'),
        ('CONFIRMATION_RESERVATION', 'Confirmation réservation'),
        ('FACTURE', 'Facture'),
        ('ALERTE_EXPIRATION', 'Alerte expiration concession'),
        ('ALERTE_PLACES', 'Alerte places critiques'),
        ('RETARD_PAIEMENT', 'Retard de paiement'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destinataire = models.ForeignKey('auth_users.Utilisateur', on_delete=models.CASCADE)
    type_notif = models.CharField(max_length=30, choices=TYPES)
    sujet = models.CharField(max_length=200)
    contenu = models.TextField()
    envoyee = models.BooleanField(default=False)
    date_envoi = models.DateTimeField(null=True, blank=True)
    erreur = models.TextField(blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'


# ===========================================================================
# Audit Log — apps/auth_users/models.py (à ajouter)
# ===========================================================================

class AuditLog(models.Model):
    '''Journal immuable de toutes les actions critiques'''
    ACTIONS = [
        ('CHANGEMENT_STATUT_CAVEAU', 'Changement statut caveau'),
        ('VALIDATION_RESERVATION', 'Validation réservation'),
        ('ANNULATION_RESERVATION', 'Annulation réservation'),
        ('PAIEMENT_CONFIRME', 'Paiement confirmé'),
        ('CONNEXION', 'Connexion utilisateur'),
        ('CREATION_CONCESSION', 'Création concession'),
        ('AUTORISATION_EXHUMATION', 'Autorisation exhumation'),
        ('MODIFICATION_CONFIG', 'Modification configuration'),
    ]

    id = models.BigAutoField(primary_key=True)
    utilisateur = models.ForeignKey('auth_users.Utilisateur', on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50, choices=ACTIONS)
    objet_type = models.CharField(max_length=50)   # Ex: 'Caveau', 'Reservation'
    objet_id = models.CharField(max_length=100)    # UUID ou ID de l'objet
    ancienne_valeur = models.JSONField(default=dict, blank=True)
    nouvelle_valeur = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    horodatage = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        verbose_name = "Journal d'audit"
        ordering = ['-horodatage']
        # Lecture seule — pas de update/delete autorisé
"""
