"""
Client API HTTP — Frontend Flet → Backend Django Ninja
Gère l'authentification JWT et les appels REST
"""
import requests
import json
from typing import Optional, Any, Dict
from utils.config import API_BASE_URL, REQUEST_TIMEOUT, session


class APIError(Exception):
    def __init__(self, message: str, code: int = 0):
        super().__init__(message)
        self.code = code


class APIClient:
    """Client HTTP avec gestion automatique du token JWT"""

    def __init__(self):
        self.base_url = API_BASE_URL

    def _headers(self, authentifie: bool = True) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if authentifie and session.token_acces:
            headers["Authorization"] = f"Bearer {session.token_acces}"
        return headers

    def _traiter_reponse(self, response: requests.Response, authentifie: bool = True) -> Any:
        if response.status_code == 401:
            if authentifie:
                # Token JWT expiré sur un appel authentifié — tenter le refresh
                if self._rafraichir_token():
                    return None  # Signale qu'il faut réessayer
                session.deconnecter()
                raise APIError("Session expirée. Veuillez vous reconnecter.", 401)
            # Endpoint public (login, MFA, etc.) : un 401 signifie simplement que
            # les identifiants / le code fourni sont invalides — ce n'est PAS une
            # session expirée puisqu'il n'y a pas encore de session à ce stade.
            try:
                return response.json()
            except json.JSONDecodeError:
                raise APIError("Identifiants ou code invalide.", 401)

        if response.status_code == 403:
            raise APIError("Accès non autorisé.", 403)

        if response.status_code == 404:
            raise APIError("Ressource introuvable.", 404)

        if response.status_code >= 500:
            raise APIError("Erreur serveur. Réessayez plus tard.", response.status_code)

        try:
            return response.json()
        except json.JSONDecodeError:
            raise APIError("Réponse invalide du serveur.")

    def _rafraichir_token(self) -> bool:
        """Rafraîchit le token d'accès avec le token de refresh"""
        if not session.token_refresh:
            return False
        try:
            r = requests.post(
                f"{self.base_url}/auth/token/refresh/",
                json={"refresh": session.token_refresh},
                timeout=REQUEST_TIMEOUT
            )
            if r.status_code == 200:
                data = r.json()
                session.token_acces = data.get("access")
                return True
        except Exception:
            pass
        return False

    def get(self, endpoint: str, params: dict = None, authentifie: bool = True) -> Any:
        try:
            r = requests.get(
                f"{self.base_url}/{endpoint}",
                headers=self._headers(authentifie),
                params=params,
                timeout=REQUEST_TIMEOUT
            )
            return self._traiter_reponse(r, authentifie)
        except requests.exceptions.ConnectionError:
            raise APIError("Impossible de contacter le serveur. Vérifiez votre connexion.")
        except requests.exceptions.Timeout:
            raise APIError("La requête a expiré. Réessayez.")

    def post(self, endpoint: str, data: dict = None, authentifie: bool = True) -> Any:
        try:
            r = requests.post(
                f"{self.base_url}/{endpoint}",
                headers=self._headers(authentifie),
                json=data or {},
                timeout=REQUEST_TIMEOUT
            )
            return self._traiter_reponse(r, authentifie)
        except requests.exceptions.ConnectionError:
            raise APIError("Impossible de contacter le serveur.")
        except requests.exceptions.Timeout:
            raise APIError("La requête a expiré.")

    def put(self, endpoint: str, data: dict = None, authentifie: bool = True) -> Any:
        try:
            r = requests.put(
                f"{self.base_url}/{endpoint}",
                headers=self._headers(authentifie),
                json=data or {},
                timeout=REQUEST_TIMEOUT
            )
            return self._traiter_reponse(r, authentifie)
        except requests.exceptions.ConnectionError:
            raise APIError("Impossible de contacter le serveur.")

    def patch(self, endpoint: str, data: dict = None, authentifie: bool = True) -> Any:
        try:
            r = requests.patch(
                f"{self.base_url}/{endpoint}",
                headers=self._headers(authentifie),
                json=data or {},
                timeout=REQUEST_TIMEOUT
            )
            return self._traiter_reponse(r, authentifie)
        except requests.exceptions.ConnectionError:
            raise APIError("Impossible de contacter le serveur.")

    def delete(self, endpoint: str, authentifie: bool = True) -> Any:
        try:
            r = requests.delete(
                f"{self.base_url}/{endpoint}",
                headers=self._headers(authentifie),
                timeout=REQUEST_TIMEOUT
            )
            return self._traiter_reponse(r, authentifie)
        except requests.exceptions.ConnectionError:
            raise APIError("Impossible de contacter le serveur.")


# ─── Instance globale partagée ───────────────────────────────────────────────
api = APIClient()
