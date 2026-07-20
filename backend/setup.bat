@echo off
echo ============================================
echo    GI2 2026 — Setup Backend Django
echo ============================================
echo.

REM Verifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python non trouve. Installez Python 3.12.
    pause
    exit /b 1
)

echo [1/6] Creation de l'environnement virtuel...
python -m venv venv
call venv\Scripts\activate.bat

echo [2/6] Installation des dependances...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERREUR] Installation des dependances echouee.
    pause
    exit /b 1
)

echo [3/6] Verification du fichier .env...
if not exist .env (
    copy .env.example .env
    echo [INFO] Fichier .env cree depuis .env.example
    echo [ATTENTION] Modifiez .env avec vos vraies valeurs de base de donnees et email !
    pause
)

echo [4/6] Application des migrations...
python manage.py makemigrations auth_users terrain reservations paiements concessions notifications rapports documents
python manage.py migrate
if errorlevel 1 (
    echo [ERREUR] Migrations echouees. Verifiez votre connexion PostgreSQL dans .env
    pause
    exit /b 1
)

echo [5/6] Creation du superadmin...
python manage.py shell -c "
from apps.auth_users.models import Utilisateur
if not Utilisateur.objects.filter(email='admin@gi2.com').exists():
    Utilisateur.objects.create_superuser(
        email='admin@gi2.com',
        password='admin123',
        nom='Admin',
        prenom='GI2',
        role='ADMIN',
    )
    print('Superadmin cree : admin@gi2.com / admin123')
else:
    print('Superadmin deja existant')
"

echo [6/6] Demarrage du serveur Django...
echo.
echo ============================================
echo  Backend lance sur http://localhost:8000
echo  Documentation API : http://localhost:8000/api/docs
echo  Admin Django : http://localhost:8000/admin
echo  Login: admin@gi2.com / admin123
echo ============================================
echo.
python manage.py runserver 0.0.0.0:8000
