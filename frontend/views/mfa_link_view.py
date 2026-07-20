"""
Vue de confirmation MFA par lien email — GI2 2026
Gère le clic sur le lien de vérification envoyé par email :
.../mfa/confirmer?uid=<user_id>&token=<jeton_signe>

Nécessite côté backend un endpoint (ex: POST /api/auth/mfa/verify-link/)
qui valide {uid, token} et renvoie la même réponse que /auth/mfa/verify/
(success, access, refresh, user). Voir les notes envoyées en backend.
"""
import flet as ft
import sys, os, time, threading
from urllib.parse import urlparse, parse_qs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api_client import api, APIError
from utils.config import session

BG_DARK   = "#f6f3ff"
BG_CARD   = "#ffffff"
ACCENT    = "#8b5cf6"
TEXT_MAIN = "#241f3d"
TEXT_SUB  = "#726c94"
ERROR_COLOR = "#f43f5e"
SUCCESS   = "#10b981"


class MFALinkView:
    """Affichée dès que l'utilisateur clique sur le lien reçu par email."""

    def __init__(self, page: ft.Page):
        self.page = page

    def _params(self) -> dict:
        # page.route ressemble à "/mfa/confirmer?uid=12&token=abcdef"
        parsed = urlparse(self.page.route)
        qs = parse_qs(parsed.query)
        return {
            "uid": qs.get("uid", [""])[0],
            "token": qs.get("token", [""])[0],
        }

    def build(self) -> ft.View:
        params = self._params()

        icone = ft.Icon(ft.Icons.HOURGLASS_TOP, size=48, color=ACCENT)
        titre = ft.Text("Validation en cours…", size=20, weight=ft.FontWeight.BOLD, color=TEXT_MAIN)
        sous_titre = ft.Text("Merci de patienter pendant la vérification du lien.", size=13, color=TEXT_SUB)
        bouton_retour = ft.TextButton(
            content=ft.Text("← Retour à la connexion", color=TEXT_SUB, size=13),
            on_click=lambda e: self.page.go("/login"),
            visible=False,
        )

        self.icone, self.titre, self.sous_titre, self.bouton_retour = icone, titre, sous_titre, bouton_retour

        carte = ft.Container(
            content=ft.Column(
                controls=[icone, titre, sous_titre, ft.Divider(height=10, color=ft.Colors.TRANSPARENT), bouton_retour],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            width=420,
            bgcolor=BG_CARD,
            border_radius=26,
            padding=ft.Padding(left=48, top=48, right=48, bottom=48),
            shadow=ft.BoxShadow(spread_radius=2, blur_radius=40,
                                 color=ft.Colors.with_opacity(0.25, "#8b5cf6"),
                                 offset=ft.Offset(0, 12)),
        )

        vue = ft.View(
            route=self.page.route,
            bgcolor=BG_DARK,
            controls=[
                ft.Container(
                    content=carte, expand=True, alignment=ft.Alignment(x=0, y=0),
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(x=-1, y=-1), end=ft.Alignment(x=1, y=1),
                        Colors=["#f6f3ff", "#fdf2ff", "#fff0f7"],
                    ),
                )
            ],
            padding=40,
        )

        if not params["uid"] or not params["token"]:
            self._afficher_echec("Lien invalide ou incomplet.")
        else:
            # Lance la validation juste après le rendu de la vue
            threading.Thread(target=self._valider, args=(params,), daemon=True).start()

        return vue

    def _valider(self, params: dict):
        time.sleep(0.3)  # laisse la vue s'afficher avant l'appel réseau
        try:
            reponse = api.post(
                "auth/mfa/verify-link/",
                data={"uid": params["uid"], "token": params["token"]},
                authentifie=False,
            )
            # --- CORRECTION ICI : vérifier la présence du champ "access" ---
            if reponse and reponse.get("access"):
                session.token_acces = reponse.get("access")
                session.token_refresh = reponse.get("refresh")
                session.utilisateur_id = reponse.get("user", {}).get("id")
                session.nom_complet = reponse.get("user", {}).get("nom_complet")
                session.email = reponse.get("user", {}).get("email")
                session.role = reponse.get("user", {}).get("role")
                session.mfa_valide = True
                session.mfa_email_temp = None
                session.mfa_user_id_temp = None
                self._afficher_succes()
                time.sleep(0.8)
                self.page.go("/dashboard")
            else:
                msg = reponse.get("detail", "Lien invalide ou expiré.") if reponse else "Lien invalide ou expiré."
                self._afficher_echec(msg)
        except APIError as ex:
            self._afficher_echec(str(ex))
        except Exception as ex:
            self._afficher_echec(f"Erreur : {str(ex)}")

    def _afficher_succes(self):
        self.icone.name = ft.Icons.CHECK_CIRCLE
        self.icone.color = SUCCESS
        self.titre.value = "Vérification réussie !"
        self.titre.color = SUCCESS
        self.sous_titre.value = "Redirection vers votre tableau de bord…"
        self.page.update()

    def _afficher_echec(self, message: str):
        self.icone.name = ft.Icons.ERROR_OUTLINE
        self.icone.color = ERROR_COLOR
        self.titre.value = "Échec de la vérification"
        self.titre.color = ERROR_COLOR
        self.sous_titre.value = message
        self.bouton_retour.visible = True
        self.page.update()