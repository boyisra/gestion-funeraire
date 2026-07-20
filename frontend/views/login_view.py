"""
Vue Login — GI2 2026
Design glassmorphism sombre — Flet 0.85+
"""
import flet as ft
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api_client import api, APIError
from utils.config import session

# --- Palette du nouveau design ---
BG_DARK      = "#0f0f1a"          # fond principal très sombre
CARD_BG      = "#1a1a2e"          # fond de la carte (légèrement plus clair)
CARD_BORDER  = "#2a2a3e"          # bordure subtile
INPUT_BG     = "#151525"          # fond des champs
ACCENT       = "#a78bfa"          # violet clair
ACCENT_HOVER = "#c4b5fd"
TEXT_MAIN    = "#f1f5f9"          # texte principal
TEXT_SUB     = "#94a3b8"          # texte secondaire
ERROR_COLOR  = "#f87171"
SUCCESS      = "#34d399"


class LoginView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.chargement = False

    def build(self) -> ft.View:
        # --- Logo / marque ---
        logo = ft.Container(
            content=ft.Text("⚰", size=32),
            bgcolor=ft.colors.with_opacity(0.1, "#ffffff"),
            border_radius=16,
            padding=ft.padding.all(12),
        )

        titre = ft.Text("Connexion", size=26, weight=ft.FontWeight.BOLD, color=TEXT_MAIN)
        sous_titre = ft.Text(
            "Accédez à votre espace de gestion",
            size=13,
            color=TEXT_SUB,
        )

        # --- Champs ---
        self.champ_email = ft.TextField(
            label="Adresse email",
            label_style=ft.TextStyle(color=TEXT_SUB, size=12),
            prefix_icon=ft.icons.EMAIL_OUTLINED,
            keyboard_type=ft.KeyboardType.EMAIL,
            autofocus=True,
            border_radius=12,
            border_color=CARD_BORDER,
            focused_border_color=ACCENT,
            cursor_color=ACCENT,
            color=TEXT_MAIN,
            bgcolor=INPUT_BG,
            on_submit=lambda e: self.champ_password.focus(),
        )

        self.champ_password = ft.TextField(
            label="Mot de passe",
            label_style=ft.TextStyle(color=TEXT_SUB, size=12),
            prefix_icon=ft.icons.LOCK_OUTLINED,
            password=True,
            can_reveal_password=True,
            border_radius=12,
            border_color=CARD_BORDER,
            focused_border_color=ACCENT,
            cursor_color=ACCENT,
            color=TEXT_MAIN,
            bgcolor=INPUT_BG,
            on_submit=lambda e: self.se_connecter(e),
        )

        # --- Message d'erreur ---
        self.message_erreur = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.icons.ERROR_OUTLINE, color=ERROR_COLOR, size=16),
                    ft.Text("", color=ERROR_COLOR, size=13),
                ],
                spacing=8,
            ),
            visible=False,
            bgcolor="#2d1b1b",
            border_radius=12,
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            border=ft.border.all(1, "#3b2020"),
        )

        # --- Bouton de connexion ---
        self.label_btn = ft.Text(
            "Se connecter",
            color="#ffffff",
            size=14,
            weight=ft.FontWeight.BOLD,
        )

        self.btn_connexion = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.icons.LOGIN, color="#ffffff", size=18),
                    self.label_btn,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            width=320,
            height=48,
            gradient=ft.LinearGradient(
                begin=ft.alignment.center_left,
                end=ft.alignment.center_right,
                colors=["#8b5cf6", "#ec4899"],
            ),
            border_radius=14,
            on_click=self.se_connecter,
            ink=True,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=20,
                color=ft.colors.with_opacity(0.3, "#8b5cf6"),
                offset=ft.Offset(0, 8),
            ),
        )

        # --- Liens additionnels (mot de passe oublié, s'inscrire) ---
        liens = ft.Row(
            controls=[
                ft.TextButton(
                    "Mot de passe oublié ?",
                    style=ft.ButtonStyle(color=TEXT_SUB, overlay_color=ft.colors.TRANSPARENT),
                ),
                ft.TextButton(
                    "Créer un compte",
                    style=ft.ButtonStyle(color=ACCENT, overlay_color=ft.colors.TRANSPARENT),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # --- Assemblage de la carte ---
        carte = ft.Container(
            content=ft.Column(
                controls=[
                    logo,
                    titre,
                    sous_titre,
                    ft.Divider(height=24, color=ft.colors.TRANSPARENT),
                    self.champ_email,
                    self.champ_password,
                    self.message_erreur,
                    ft.Divider(height=8, color=ft.colors.TRANSPARENT),
                    ft.Row(controls=[self.btn_connexion], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(height=16, color=ft.colors.TRANSPARENT),
                    liens,
                ],
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=420,
            padding=ft.padding.symmetric(horizontal=32, vertical=40),
            bgcolor=CARD_BG,
            border_radius=24,
            border=ft.border.all(1, CARD_BORDER),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=40,
                color=ft.colors.with_opacity(0.15, "#000000"),
                offset=ft.Offset(0, 20),
            ),
        )

        # --- Fond avec un dégradé circulaire pour donner de la profondeur ---
        fond = ft.Container(
            content=ft.Stack(
                controls=[
                    # Cercle décoratif violet en haut à droite
                    ft.Container(
                        width=300,
                        height=300,
                        gradient=ft.RadialGradient(
                            center=ft.alignment.center,
                            radius=1.0,
                            colors=["#8b5cf6", "#1a1a2e00"],
                        ),
                        top=-50,
                        right=-50,
                    ),
                    # Cercle décoratif rose en bas à gauche
                    ft.Container(
                        width=250,
                        height=250,
                        gradient=ft.RadialGradient(
                            center=ft.alignment.center,
                            radius=1.0,
                            colors=["#ec4899", "#1a1a2e00"],
                        ),
                        bottom=-60,
                        left=-60,
                    ),
                ]
            ),
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
                colors=["#0a0a14", "#0f0f1a", "#0a0a14"],
            ),
        )

        # --- Vue finale ---
        return ft.View(
            route="/login",
            bgcolor=BG_DARK,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Stack(
                    controls=[
                        fond,
                        ft.Container(
                            content=carte,
                            alignment=ft.alignment.center,
                            expand=True,
                        ),
                    ],
                    expand=True,
                )
            ],
            padding=0,
        )

    # ----- Les méthodes restent inchangées -----
    def se_connecter(self, e):
        if self.chargement:
            return

        email = self.champ_email.value.strip() if self.champ_email.value else ""
        password = self.champ_password.value or ""

        if not email or not password:
            self._afficher_erreur("Veuillez remplir tous les champs.")
            return

        self._set_chargement(True)

        try:
            reponse = api.post(
                "auth/login/",
                data={"email": email, "password": password},
                authentifie=False,
            )
            if reponse and reponse.get("success"):
                session.mfa_email_temp = email
                session.mfa_user_id_temp = reponse.get("user_id", "")
                self.page.go("/mfa")
            else:
                msg = reponse.get("detail", "Email ou mot de passe incorrect.") if reponse else "Erreur de connexion."
                self._afficher_erreur(msg)

        except APIError as ex:
            self._afficher_erreur("Impossible de contacter le serveur." if ex.code == 0 else str(ex))
        except Exception as ex:
            self._afficher_erreur(f"Erreur : {str(ex)}")
        finally:
            self._set_chargement(False)

    def _afficher_erreur(self, message: str):
        self.message_erreur.content.controls[1].value = message
        self.message_erreur.visible = True
        self.page.update()

    def _set_chargement(self, actif: bool):
        self.chargement = actif
        self.btn_connexion.opacity = 0.6 if actif else 1.0
        self.btn_connexion.disabled = actif
        self.label_btn.value = "Connexion en cours..." if actif else "Se connecter"
        self.page.update()