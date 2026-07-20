"""
Vue Notifications — GI2 2026
Centre de notifications utilisateur
Compatible Flet 0.85+
"""
import flet as ft
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api_client import api, APIError
from components.sidebar import build_sidebar, build_topbar

BG_DARK   = "#f6f3ff"
BG_CARD   = "#ffffff"
BG_INPUT  = "#f1ecff"
ACCENT    = "#8b5cf6"
TEXT_MAIN = "#241f3d"
TEXT_SUB  = "#726c94"
BORDER    = "#e6ddff"
SUCCESS   = "#10b981"
WARNING   = "#f59e0b"
ERROR_C   = "#f43f5e"
PURPLE    = "#d946ef"

ICONES_TYPES = {
    'MFA':                    (ft.Icons.SECURITY,         ACCENT),
    'CONFIRMATION_RESERVATION':(ft.Icons.BOOK_ONLINE,     WARNING),
    'VALIDATION_RESERVATION': (ft.Icons.CHECK_CIRCLE,     SUCCESS),
    'ANNULATION_RESERVATION': (ft.Icons.CANCEL,           ERROR_C),
    'FACTURE':                (ft.Icons.RECEIPT_LONG,     "#f59e0b"),
    'ALERTE_EXPIRATION':      (ft.Icons.WARNING,          WARNING),
    'ALERTE_PLACES':          (ft.Icons.LOCATION_CITY,    ERROR_C),
    'RETARD_PAIEMENT':        (ft.Icons.PAYMENTS,         ERROR_C),
}


class NotificationView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.notifications = []
        self.filtre = "toutes"

    def build(self) -> ft.View:
        self._charger()
        self.contenu = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        self._rafraichir()

        non_lues = sum(1 for n in self.notifications if not n.get('lue'))
        badge_non_lues = ft.Container(
            content=ft.Text(str(non_lues), size=11, color="#ffffff", weight=ft.FontWeight.BOLD),
            bgcolor=ERROR_C if non_lues > 0 else BG_INPUT,
            border_radius=26,
            padding=ft.Padding(left=8, top=2, right=8, bottom=2),
            visible=non_lues > 0,
        )
        titre_row = ft.Row(controls=[
            ft.Container(
                content=ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED, color=ACCENT, size=20),
                bgcolor="#f1ecff", border_radius=12,
                padding=ft.Padding(left=9, top=9, right=9, bottom=9),
            ),
            ft.Text("Notifications", size=19, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
            badge_non_lues,
        ], spacing=12)

        corps = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=[
                            titre_row,
                            ft.Row(controls=[
                                ft.TextButton(
                                    content=ft.Row(controls=[
                                        ft.Icon(ft.Icons.DONE_ALL, color=ACCENT, size=16),
                                        ft.Text("Tout marquer lu", color=ACCENT, size=13),
                                    ], spacing=6),
                                    on_click=self._tout_marquer_lu,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.REFRESH_ROUNDED, icon_color=TEXT_SUB,
                                    on_click=lambda e: self._actualiser(),
                                ),
                            ], spacing=4),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    bgcolor=BG_CARD,
                    padding=ft.Padding(left=24, top=16, right=20, bottom=16),
                    border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
                ),
                self._build_filtres(),
                ft.Container(
                    content=self.contenu,
                    expand=True,
                    padding=ft.Padding(left=24, top=16, right=24, bottom=24),
                ),
            ],
            expand=True, spacing=0,
        )

        return ft.View(
            route="/notifications",
            bgcolor=BG_DARK,
            padding=0,
            controls=[
                ft.Row(
                    controls=[
                        build_sidebar(self.page, "/notifications", non_lues),
                        ft.Container(content=corps, expand=True, bgcolor=BG_DARK),
                    ],
                    expand=True, spacing=0,
                )
            ],
        )

    def _build_filtres(self) -> ft.Container:
        filtres = [
            ("toutes",    "Toutes"),
            ("non_lues",  "Non lues"),
            ("FACTURE",   "Factures"),
            ("ALERTE_EXPIRATION", "Alertes"),
            ("CONFIRMATION_RESERVATION", "Réservations"),
        ]
        boutons = []
        for key, label in filtres:
            actif = self.filtre == key
            boutons.append(
                ft.Container(
                    content=ft.Text(label, size=12,
                                    color=BG_DARK if actif else TEXT_SUB,
                                    weight=ft.FontWeight.BOLD if actif else ft.FontWeight.NORMAL),
                    bgcolor=ACCENT if actif else BG_INPUT,
                    border_radius=26,
                    padding=ft.Padding(left=14, top=6, right=14, bottom=6),
                    on_click=lambda e, k=key: self._changer_filtre(k),
                    ink=True,
                )
            )
        return ft.Container(
            content=ft.Row(controls=boutons, spacing=8, scroll=ft.ScrollMode.AUTO),
            bgcolor="#ffffff",
            padding=ft.Padding(left=16, top=8, right=16, bottom=10),
            border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
        )

    def _changer_filtre(self, key: str):
        self.filtre = key
        self._rafraichir()

    def _charger(self):
        try:
            self.notifications = api.get("notifications/") or []
        except Exception:
            self.notifications = []

    def _actualiser(self):
        self._charger()
        self._rafraichir()

    def _rafraichir(self):
        # Filtrer
        if self.filtre == "non_lues":
            liste = [n for n in self.notifications if not n.get('lue')]
        elif self.filtre == "toutes":
            liste = self.notifications
        else:
            liste = [n for n in self.notifications if n.get('type_notif') == self.filtre]

        self.contenu.controls.clear()

        if not liste:
            self.contenu.controls.append(
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Icon(ft.Icons.NOTIFICATIONS_NONE, size=52, color=TEXT_SUB),
                        ft.Text("Aucune notification", color=TEXT_SUB, size=14),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    alignment=ft.Alignment(x=0, y=0), height=200,
                )
            )
        else:
            for n in liste:
                self.contenu.controls.append(self._carte_notif(n))

        self.page.update()

    def _carte_notif(self, n: dict) -> ft.Container:
        type_notif = n.get('type_notif', '')
        icon, couleur = ICONES_TYPES.get(type_notif, (ft.Icons.NOTIFICATIONS, ACCENT))
        lue = n.get('lue', False)

        return ft.Container(
            content=ft.Row(
                controls=[
                    # Indicateur non lue
                    ft.Container(
                        width=6,
                        bgcolor=ACCENT if not lue else "transparent",
                        border_radius=ft.BorderRadius.only(top_left=8, bottom_left=8),
                    ),
                    # Icône type
                    ft.Container(
                        content=ft.Icon(icon, color=couleur, size=22),
                        bgcolor=f"{couleur}22",
                        border_radius=50,
                        padding=ft.Padding(left=10, top=10, right=10, bottom=10),
                        margin=ft.Margin(left=10, top=0, right=0, bottom=0),
                    ),
                    # Contenu
                    ft.Column(
                        controls=[
                            ft.Text(n.get('sujet', ''), size=13,
                                    weight=ft.FontWeight.BOLD if not lue else ft.FontWeight.NORMAL,
                                    color=TEXT_MAIN if not lue else TEXT_SUB),
                            ft.Text(
                                n.get('contenu', '')[:120] + ('...' if len(n.get('contenu','')) > 120 else ''),
                                size=12, color=TEXT_SUB,
                            ),
                            ft.Text(n.get('cree_le', ''), size=10, color=BORDER),
                        ],
                        spacing=3, expand=True,
                    ),
                    # Bouton marquer lu
                    ft.IconButton(
                        icon=ft.Icons.CIRCLE if not lue else ft.Icons.CHECK_CIRCLE,
                        icon_color=ACCENT if not lue else SUCCESS,
                        icon_size=18,
                        tooltip="Marquer comme lu",
                        on_click=lambda e, nid=n['id']: self._marquer_lue(nid),
                    ) if not lue else ft.Container(width=40),
                ],
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=BG_CARD if not lue else "#141e2d",
            border_radius=14,
            border=ft.Border.all(1, BORDER if lue else ACCENT),
            padding=ft.Padding(left=0, top=10, right=8, bottom=10),
            margin=ft.Margin(left=0, top=0, right=0, bottom=0),
        )

    def _marquer_lue(self, notif_id: str):
        try:
            api.post(f"notifications/{notif_id}/lire/")
            self._actualiser()
        except Exception:
            pass

    def _tout_marquer_lu(self, e):
        try:
            api.post("notifications/lire-toutes/")
            self._actualiser()
        except Exception:
            pass
