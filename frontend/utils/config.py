"""
Configuration du frontend Flet — GI2 2026
"""
import os
from dataclasses import dataclass
from typing import Optional

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")
REQUEST_TIMEOUT = 15

COULEURS_CAVEAUX = {
    "DISPONIBLE": "#22c55e",
    "RESERVE": "#f97316",
    "OCCUPE": "#ef4444",
    "NON_EXPLOITABLE": "#6b7280",
    "ENTRETIEN": "#d946ef",
}

THEME_COULEUR_PRIMAIRE = "#7c3aed"
THEME_COULEUR_SECONDAIRE = "#8b5cf6"
THEME_COULEUR_ACCENT = "#f59e0b"


@dataclass
class Session:
    token_acces: Optional[str] = None
    token_refresh: Optional[str] = None
    utilisateur_id: Optional[str] = None
    nom_complet: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    mfa_valide: bool = False

    # Stockage temporaire pour le flux MFA (remplace client_storage)
    mfa_email_temp: Optional[str] = None
    mfa_user_id_temp: Optional[str] = None

    def est_connecte(self) -> bool:
        return self.token_acces is not None and self.mfa_valide

    def est_admin(self) -> bool:
        return self.role in ("ADMIN",)

    def est_staff(self) -> bool:
        return self.role in ("ADMIN", "AGENT", "SECRETARIAT")

    def deconnecter(self):
        self.token_acces = None
        self.token_refresh = None
        self.utilisateur_id = None
        self.nom_complet = None
        self.email = None
        self.role = None
        self.mfa_valide = False
        self.mfa_email_temp = None
        self.mfa_user_id_temp = None


session = Session()
