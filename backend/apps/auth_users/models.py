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

    mfa_active = models.BooleanField(default=True)
    # Vérifie que le client a confirmé son adresse email à l'inscription
    # (code envoyé par email, à saisir avant le tout premier login).
    # default=True : les comptes déjà existants (créés via l'admin) restent
    # utilisables sans nouvelle vérification — seule l'auto-inscription
    # (endpoint /auth/inscription/) crée des comptes avec False au départ.
    email_verifie = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

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
    """Code MFA à 6 chiffres envoyé par email — expire en 10 min"""
    OBJECTIFS = [
        ('CONNEXION', 'Connexion (MFA à chaque login)'),
        ('INSCRIPTION', "Vérification d'email à l'inscription"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='tokens_mfa')
    code = models.CharField(max_length=6)
    objectif = models.CharField(max_length=20, choices=OBJECTIFS, default='CONNEXION')
    expiration = models.DateTimeField()
    utilise = models.BooleanField(default=False)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mfa_tokens'

    def est_valide(self) -> bool:
        from django.utils import timezone
        return not self.utilise and self.expiration > timezone.now()
