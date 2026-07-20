# Generated manually — GI2 2026
# Ajoute la vérification d'email à l'inscription (email_verifie) et
# distingue les codes MFA de connexion des codes de vérification d'inscription (objectif)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='utilisateur',
            name='email_verifie',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='tokenmfa',
            name='objectif',
            field=models.CharField(
                choices=[
                    ('CONNEXION', 'Connexion (MFA à chaque login)'),
                    ('INSCRIPTION', "Vérification d'email à l'inscription"),
                ],
                default='CONNEXION',
                max_length=20,
            ),
        ),
    ]
