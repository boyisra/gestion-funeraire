"""
Vue MFA — GI2 2026
Compatible Flet 0.85+ — utilise page.session au lieu de client_storage
"""
import flet as ft
import sys, os, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api_client import api, APIError
from utils.config import session

DUREE_EXPIRATION_SECONDES = 600  # 10 minutes — doit correspondre à la durée définie côté backend

BG_DARK   = "#f6f3ff"
BG_CARD   = "#ffffff"
BG_INPUT  = "#f1ecff"
ACCENT    = "#8b5cf6"
TEXT_MAIN = "#241f3d"
TEXT_SUB  = "#726c94"
BORDER    = "#e6ddff"
ERROR_COLOR = "#f43f5e"
SUCCESS   = "#10b981"


class MFAView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.chargement = False
        # Récupérer depuis le stockage temporaire de notre session custom
        self.email = session.mfa_email_temp or ""
        self.user_id = session.mfa_user_id_temp or ""
        # Décompte d'expiration du code OTP (réel, basé sur la durée backend)
        self.secondes_restantes = DUREE_EXPIRATION_SECONDES
        self.code_expire = False
        self._thread_decompte = None

    def build(self) -> ft.View:

        # ─── Calcul responsive (corrige le débordement de la case n°6 et
        # adapte la carte aux petits écrans / mobile) ──────────────────────
        largeur_ecran = self.page.width or 420
        mobile = largeur_ecran < 480
        padding_vue = 16 if mobile else 40
        padding_carte = 24 if mobile else 48
        espacement_cases = 8 if mobile else 10
        largeur_carte = min(420, max(300, largeur_ecran - 2 * padding_vue))
        largeur_contenu = largeur_carte - 2 * padding_carte
        # Taille de case calculée pour que les 6 cases + espacements tiennent
        # toujours exactement dans la largeur disponible — plus aucun débordement.
        taille_case = max(36, min(54, (largeur_contenu - 5 * espacement_cases) / 6))

        # Hauteur augmentée pour laisser assez de place au chiffre (le padding
        # interne par défaut du TextField coupait le haut/bas des caractères)
        hauteur_case = taille_case * 1.35
        taille_texte = max(20, taille_case * 0.42)
        # Centrage vertical via un padding calculé manuellement — le paramètre
        # text_vertical_align provoque un rendu déformé/pivoté des chiffres
        # sur certaines versions de Flet, on l'évite complètement.
        padding_vertical_case = max(4, (hauteur_case - taille_texte * 1.3) / 2)

        self.cases = []
        for i in range(6):
            case = ft.TextField(
                width=taille_case,
                height=hauteur_case,
                text_align=ft.TextAlign.CENTER,
                content_padding=ft.Padding(left=0, top=padding_vertical_case, right=0, bottom=padding_vertical_case),
                max_length=1,
                # counter_text=""  # <-- SUPPRIMÉ car non supporté dans cette version de Flet
                keyboard_type=ft.KeyboardType.NUMBER,
                border_radius=18,
                text_size=taille_texte,
                border_color=BORDER,
                focused_border_color=ACCENT,
                cursor_color=ACCENT,
                color=TEXT_MAIN,
                bgcolor=BG_INPUT,
                on_change=lambda e, idx=i: self._case_changee(e, idx),
            )
            self.cases.append(case)

        self.msg_erreur = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=ERROR_COLOR, size=16),
                    ft.Text("", color=ERROR_COLOR, size=13),
                ],
                spacing=8,
            ),
            visible=False,
            bgcolor="#ffe4e6",
            border_radius=14,
            padding=ft.Padding(left=12, top=10, right=12, bottom=10),
        )

        self.msg_succes = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=SUCCESS, size=16),
                    ft.Text("", color=SUCCESS, size=13),
                ],
                spacing=8,
            ),
            visible=False,
            bgcolor="#d1fae5",
            border_radius=14,
            padding=ft.Padding(left=12, top=10, right=12, bottom=10),
        )

        self.label_btn = ft.Text(
            "Vérifier le code",
            color=BG_DARK,
            size=15,
            weight=ft.FontWeight.BOLD,
        )

        self.btn_verifier = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.VERIFIED_USER, color="#ffffff", size=18),
                    self.label_btn,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
            ),
            width=300,
            height=50,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(x=-1, y=0), end=ft.Alignment(x=1, y=0),
                Colors=["#8b5cf6", "#ec4899"],
            ),
            border_radius=18,
            on_click=self.verifier_code,
            ink=True,
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=18,
                                 color=ft.Colors.with_opacity(0.35, "#8b5cf6"),
                                 offset=ft.Offset(0, 6)),
        )

        email_masque = self._masquer_email(self.email)

        self.txt_timer = ft.Text(self._format_decompte(), color=ACCENT, size=12)
        self.icone_timer = ft.Icon(ft.Icons.TIMER, color=ACCENT, size=14)
        self.conteneur_timer = ft.Container(
            content=ft.Row(
                controls=[self.icone_timer, self.txt_timer],
                spacing=6,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bgcolor="#ede9fe",
            border_radius=26,
            padding=ft.Padding(left=16, top=6, right=16, bottom=6),
        )

        carte = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Container(
                                content=ft.Icon(ft.Icons.MARK_EMAIL_READ, size=48, color=ACCENT),
                                bgcolor="#ede9fe",
                                border_radius=50,
                                padding=ft.Padding(left=16, top=16, right=16, bottom=16),
                            ),
                            ft.Text(
                                "Vérification en deux étapes",
                                size=22,
                                weight=ft.FontWeight.BOLD,
                                color=TEXT_MAIN,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                f"Code envoyé à  {email_masque}",
                                size=13,
                                color=TEXT_SUB,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            self.conteneur_timer,
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    ft.Row(
                        controls=self.cases,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=espacement_cases,
                    ),
                    self.msg_erreur,
                    self.msg_succes,
                    ft.Divider(height=12, color=ft.Colors.TRANSPARENT),
                    ft.Row(controls=[self.btn_verifier], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                    ft.Row(
                        controls=[
                            ft.TextButton(
                                content=ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.REFRESH, size=15, color=TEXT_SUB),
                                        ft.Text("Renvoyer", color=TEXT_SUB, size=13),
                                    ],
                                    spacing=4,
                                ),
                                on_click=self.renvoyer_code,
                            ),
                            ft.Text("·", color=BORDER),
                            ft.TextButton(
                                content=ft.Text("← Retour", color=TEXT_SUB, size=13),
                                on_click=lambda e: self.page.go("/login"),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=4,
                    ),
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            width=largeur_carte,
            bgcolor=BG_CARD,
            border_radius=26,
            padding=ft.Padding(left=padding_carte, top=padding_carte, right=padding_carte, bottom=padding_carte),
            shadow=ft.BoxShadow(
                spread_radius=2,
                blur_radius=40,
                color=ft.Colors.with_opacity(0.25, "#8b5cf6"),
                offset=ft.Offset(0, 12),
            ),
        )

        self._id_session = id(self)
        self.page.mfa_session_actif = self._id_session

        vue = ft.View(
            route="/mfa",
            bgcolor=BG_DARK,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Container(
                    content=carte,
                    expand=True,
                    alignment=ft.Alignment(x=0, y=0),
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(x=-1, y=-1), end=ft.Alignment(x=1, y=1),
                        Colors=["#f6f3ff", "#fdf2ff", "#fff0f7"],
                    ),
                )
            ],
            padding=padding_vue,
        )

        self._demarrer_decompte()
        return vue

    # ─── Gestion du décompte d'expiration (réel, en direct) ──────────────────
    def _format_decompte(self) -> str:
        if self.code_expire:
            return "Code expiré"
        minutes, secondes = divmod(max(self.secondes_restantes, 0), 60)
        return f"Expire dans {minutes:02d}:{secondes:02d}"

    def _demarrer_decompte(self):
        """Lance un thread qui décrémente le compteur chaque seconde tant que
        la vue /mfa est active et notifie l'utilisateur dès l'expiration réelle."""
        if self._thread_decompte and self._thread_decompte.is_alive():
            return

        def boucle():
            while (
                self.page.route == "/mfa"
                and not self.code_expire
                and getattr(self.page, "mfa_session_actif", None) == self._id_session
            ):
                time.sleep(1)
                if self.page.route != "/mfa" or getattr(self.page, "mfa_session_actif", None) != self._id_session:
                    return
                self.secondes_restantes -= 1
                if self.secondes_restantes <= 0:
                    self.code_expire = True
                    self.txt_timer.value = "Code expiré — demandez un nouveau code"
                    self.txt_timer.color = ERROR_COLOR
                    self.icone_timer.color = ERROR_COLOR
                    self.conteneur_timer.bgcolor = "#ffe4e6"
                    self._afficher_erreur("Le code a expiré. Cliquez sur « Renvoyer » pour en recevoir un nouveau.")
                else:
                    self.txt_timer.value = self._format_decompte()
                try:
                    self.page.update()
                except Exception:
                    return

        self._thread_decompte = threading.Thread(target=boucle, daemon=True)
        self._thread_decompte.start()

    def _reinitialiser_decompte(self):
        self.secondes_restantes = DUREE_EXPIRATION_SECONDES
        self.code_expire = False
        self.txt_timer.value = self._format_decompte()
        self.txt_timer.color = ACCENT
        self.icone_timer.color = ACCENT
        self.conteneur_timer.bgcolor = "#ede9fe"
        self.page.update()
        self._demarrer_decompte()

    def _case_changee(self, e, index: int):
        valeur = e.control.value
        if valeur and index < 5:
            self.cases[index + 1].focus()
        elif valeur and index == 5:
            self.verifier_code(None)
        self.page.update()

    def _get_code(self) -> str:
        return "".join([c.value or "" for c in self.cases])

    def _masquer_email(self, email: str) -> str:
        if "@" not in email:
            return email
        local, domaine = email.split("@", 1)
        masque = local[:2] + "***" if len(local) > 2 else local[0] + "***"
        return f"{masque}@{domaine}"

    def verifier_code(self, e):
        if self.chargement:
            return
        if self.code_expire:
            self._afficher_erreur("Le code a expiré. Cliquez sur « Renvoyer » pour en recevoir un nouveau.")
            return
        code = self._get_code()
        if len(code) < 6:
            self._afficher_erreur("Veuillez saisir les 6 chiffres.")
            return
        self._set_chargement(True)
        try:
            reponse = api.post("auth/mfa/verify/", data={"user_id": self.user_id, "code": code}, authentifie=False)
            # --- CORRECTION : vérifier la présence du champ "access" ---
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
                self._afficher_succes("Authentification réussie !")
                time.sleep(0.8)
                self.page.go("/dashboard")
            else:
                # Le backend renvoie un détail d'erreur dans "detail"
                msg = reponse.get("detail") if reponse else "Erreur inconnue"
                self._afficher_erreur(msg)
                self._vider_cases()
        except APIError as ex:
            self._afficher_erreur(str(ex))
            self._vider_cases()
        except Exception as ex:
            self._afficher_erreur(f"Erreur : {str(ex)}")
        finally:
            self._set_chargement(False)

    def renvoyer_code(self, e):
        if not self.email:
            self._afficher_erreur("Email introuvable.")
            return
        try:
            reponse = api.post("auth/mfa/resend/", data={"email": self.email}, authentifie=False)
            if reponse and reponse.get("success"):
                self._afficher_succes("Nouveau code envoyé !")
                self._vider_cases()
                self._reinitialiser_decompte()
            else:
                self._afficher_erreur("Impossible d'envoyer le code.")
        except APIError as ex:
            self._afficher_erreur(str(ex))

    def _vider_cases(self):
        for case in self.cases:
            case.value = ""
        self.cases[0].focus()
        self.page.update()

    def _afficher_erreur(self, message: str):
        self.msg_erreur.content.controls[1].value = message
        self.msg_erreur.visible = True
        self.msg_succes.visible = False
        self.page.update()

    def _afficher_succes(self, message: str):
        self.msg_succes.content.controls[1].value = message
        self.msg_succes.visible = True
        self.msg_erreur.visible = False
        self.page.update()

    def _set_chargement(self, actif: bool):
        self.chargement = actif
        self.btn_verifier.opacity = 0.6 if actif else 1.0
        self.btn_verifier.disabled = actif
        self.label_btn.value = "Vérification..." if actif else "Vérifier le code"
        self.page.update()