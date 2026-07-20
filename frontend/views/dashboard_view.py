"""
Vue Dashboard — GI2 2026
Design glassmorphism sombre — Flet 0.85+
"""
import flet as ft
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api_client import api, APIError
from utils.config import session
from components.sidebar import build_sidebar, build_topbar

# ----- Nouvelle palette sombre -----
BG_DARK      = "#0f0f1a"
CARD_BG      = "#1a1a2e"
CARD_BORDER  = "#2a2a3e"
INPUT_BG     = "#151525"
ACCENT       = "#a78bfa"
TEXT_MAIN    = "#f1f5f9"
TEXT_SUB     = "#94a3b8"
BORDER       = "#2a2a3e"
SUCCESS      = "#34d399"
WARNING      = "#fbbf24"
ERROR_C      = "#f87171"
PURPLE       = "#c084fc"
INFO         = "#60a5fa"


class DashboardView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.stats = {}
        self.notif_count = 0

    def build(self) -> ft.View:
        self._charger_stats()
        self.contenu = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        self._construire_contenu()

        corps = ft.Column(
            controls=[
                build_topbar(
                    self.page, ft.Icons.SPACE_DASHBOARD_ROUNDED, "Tableau de bord",
                    on_refresh=lambda e: self._actualiser(),
                ),
                ft.Container(
                    content=self.contenu,
                    expand=True,
                    padding=ft.Padding(left=24, top=20, right=24, bottom=24),
                ),
            ],
            expand=True, spacing=0,
        )

        # Fond avec halos décoratifs (identique aux autres vues)
        fond = ft.Stack(
            controls=[
                ft.Container(
                    width=300, height=300,
                    gradient=ft.RadialGradient(
                        center=ft.alignment.center, radius=1.0,
                        colors=["#8b5cf6", "#0f0f1a00"]
                    ),
                    top=-50, right=-50,
                ),
                ft.Container(
                    width=250, height=250,
                    gradient=ft.RadialGradient(
                        center=ft.alignment.center, radius=1.0,
                        colors=["#ec4899", "#0f0f1a00"]
                    ),
                    bottom=-60, left=-60,
                ),
            ]
        )

        return ft.View(
            route="/dashboard",
            bgcolor=BG_DARK,
            padding=0,
            controls=[
                ft.Stack(
                    controls=[
                        fond,
                        ft.Row(
                            controls=[
                                build_sidebar(self.page, "/dashboard", self.notif_count),
                                ft.Container(content=corps, expand=True, bgcolor=BG_DARK),
                            ],
                            expand=True, spacing=0,
                        ),
                    ],
                    expand=True,
                ),
            ],
        )

    def _construire_contenu(self):
        s = self.stats

        self.contenu.controls = [
            ft.Row(controls=[
                ft.Column(controls=[
                    ft.Text("Tableau de bord", size=22,
                            weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ft.Text(f"Bienvenue, {session.nom_complet or 'Utilisateur'}",
                            size=13, color=TEXT_SUB),
                ], spacing=2),
                ft.IconButton(icon=ft.Icons.REFRESH, icon_color=TEXT_SUB,
                              on_click=lambda e: self._actualiser()),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

            ft.Divider(height=16, color=ft.colors.TRANSPARENT),

            ft.Text("Vue d'ensemble", size=14, color=TEXT_SUB, weight=ft.FontWeight.BOLD),

            ft.Row(controls=[
                self._metrique("Taux d'occupation",
                               f"{s.get('taux_occupation', 0)}%",
                               ft.Icons.PIE_CHART, ACCENT,
                               f"{s.get('caveaux_occupes',0)}/{s.get('total_caveaux',0)} caveaux"),
                self._metrique("Disponibles",
                               str(s.get('caveaux_disponibles', 0)),
                               ft.Icons.CHECK_CIRCLE, SUCCESS, "caveaux libres"),
                self._metrique("En attente",
                               str(s.get('reservations_en_attente', 0)),
                               ft.Icons.HOURGLASS_EMPTY, WARNING, "à valider"),
                self._metrique("Revenus ce mois",
                               f"{int(s.get('revenus_mois', 0)):,}",
                               ft.Icons.ACCOUNT_BALANCE_WALLET, SUCCESS, "XAF"),
            ], spacing=12, wrap=True),

            ft.Divider(height=20, color=CARD_BORDER),

            ft.Text("Occupation globale", size=14, color=TEXT_SUB, weight=ft.FontWeight.BOLD),
            self._carte(ft.Column(controls=[
                ft.Row(controls=[
                    ft.Text(f"{s.get('taux_occupation', 0)}%", size=32,
                            weight=ft.FontWeight.BOLD,
                            color=SUCCESS if s.get('taux_occupation', 0) < 70
                            else WARNING if s.get('taux_occupation', 0) < 90 else ERROR_C),
                    ft.Column(controls=[
                        ft.Text("Taux d'occupation global", color=TEXT_SUB, size=12),
                        ft.Text(f"Capacité : {s.get('places_calculees', 0)} places",
                                color=TEXT_SUB, size=11),
                    ], spacing=2),
                ], spacing=16),
                ft.ProgressBar(
                    value=min(s.get('taux_occupation', 0) / 100, 1.0),
                    bgcolor=INPUT_BG, color=ACCENT, height=14, border_radius=12,
                ),
                ft.Row(controls=[
                    self._legende("Disponibles", SUCCESS, str(s.get('caveaux_disponibles', 0))),
                    self._legende("Réservés", WARNING, str(s.get('caveaux_reserves', 0))),
                    self._legende("Occupés", ERROR_C, str(s.get('caveaux_occupes', 0))),
                ], spacing=20),
            ], spacing=12)),

            ft.Divider(height=20, color=CARD_BORDER),

            ft.Row(controls=[
                ft.Column(controls=[
                    ft.Text("Réservations", size=14, color=TEXT_SUB, weight=ft.FontWeight.BOLD),
                    self._carte(ft.Column(controls=[
                        self._stat_ligne("Total", str(s.get('reservations_total', 0)), ACCENT),
                        self._stat_ligne("Ce mois", str(s.get('reservations_mois', 0)), SUCCESS),
                        self._stat_ligne("En attente", str(s.get('reservations_en_attente', 0)), WARNING),
                        self._stat_ligne("Validées", str(s.get('reservations_validees', 0)), SUCCESS),
                    ], spacing=8)),
                    ft.Container(
                        content=ft.Row(controls=[
                            ft.Icon(ft.Icons.ARROW_FORWARD, color=ACCENT, size=14),
                            ft.Text("Voir les réservations", color=ACCENT, size=12),
                        ], spacing=6),
                        on_click=lambda e: self.page.go("/reservations"), ink=True,
                    ),
                ], spacing=8, expand=True),

                ft.Column(controls=[
                    ft.Text("Finances", size=14, color=TEXT_SUB, weight=ft.FontWeight.BOLD),
                    self._carte(ft.Column(controls=[
                        self._stat_ligne("Total revenus",
                                         f"{int(s.get('revenus_total', 0)):,} XAF", SUCCESS),
                        self._stat_ligne("Ce mois",
                                         f"{int(s.get('revenus_mois', 0)):,} XAF", ACCENT),
                        self._stat_ligne("En attente", str(s.get('paiements_en_attente', 0)), WARNING),
                    ], spacing=8)),
                    ft.Container(
                        content=ft.Row(controls=[
                            ft.Icon(ft.Icons.ARROW_FORWARD, color=ACCENT, size=14),
                            ft.Text("Voir les paiements", color=ACCENT, size=12),
                        ], spacing=6),
                        on_click=lambda e: self.page.go("/paiements"), ink=True,
                    ),
                ], spacing=8, expand=True),

                ft.Column(controls=[
                    ft.Text("Concessions", size=14, color=TEXT_SUB, weight=ft.FontWeight.BOLD),
                    self._carte(ft.Column(controls=[
                        self._stat_ligne("Actives", str(s.get('concessions_actives', 0)), SUCCESS),
                        self._stat_ligne("Expirant bientôt",
                                         str(s.get('concessions_expirant', 0)), WARNING),
                        self._stat_ligne("Exhumations",
                                         str(s.get('exhumations_en_cours', 0)), PURPLE),
                    ], spacing=8)),
                    ft.Container(
                        content=ft.Row(controls=[
                            ft.Icon(ft.Icons.ARROW_FORWARD, color=ACCENT, size=14),
                            ft.Text("Voir les concessions", color=ACCENT, size=12),
                        ], spacing=6),
                        on_click=lambda e: self.page.go("/concessions"), ink=True,
                    ),
                ], spacing=8, expand=True),
            ], spacing=20),

            ft.Divider(height=20, color=CARD_BORDER),

            ft.Text("Accès rapides", size=14, color=TEXT_SUB, weight=ft.FontWeight.BOLD),
            ft.Row(controls=[
                self._raccourci("Carte", ft.Icons.MAP, ACCENT,
                                lambda e: self.page.go("/carte")),
                self._raccourci("Réservation", ft.Icons.ADD_CIRCLE, SUCCESS,
                                lambda e: self.page.go("/reservations")),
                self._raccourci("Paiement", ft.Icons.PAYMENTS, WARNING,
                                lambda e: self.page.go("/paiements")),
                self._raccourci("Documents", ft.Icons.PICTURE_AS_PDF, ERROR_C,
                                lambda e: self.page.go("/documents")),
                self._raccourci("Rapports", ft.Icons.BAR_CHART, PURPLE,
                                lambda e: self.page.go("/rapports")),
            ], spacing=12, wrap=True),
        ]

    def _charger_stats(self):
        try:
            self.stats = api.get("rapports/dashboard/") or {}
        except Exception:
            self.stats = {}
        try:
            data = api.get("notifications/non-lues/count/") or {}
            self.notif_count = data.get('count', 0)
        except Exception:
            self.notif_count = 0

    def _actualiser(self):
        self._charger_stats()
        self.contenu.controls.clear()
        self._construire_contenu()
        self.page.update()

    def _deconnecter(self, e):
        session.deconnecter()
        self.page.go("/login")

    # ----- Utilitaires UI (adaptés au thème sombre) -----
    def _ombre(self, couleur: str = "#000000", force: float = 0.2) -> ft.BoxShadow:
        return ft.BoxShadow(
            spread_radius=0,
            blur_radius=20,
            color=ft.colors.with_opacity(force, couleur),
            offset=ft.Offset(0, 8),
        )

    def _metrique(self, label, valeur, icon, couleur, sous="") -> ft.Container:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Container(
                    content=ft.Icon(icon, color=couleur, size=20),
                    bgcolor=ft.colors.with_opacity(0.15, couleur),
                    border_radius=12,
                    padding=ft.Padding(left=9, top=9, right=9, bottom=9),
                ),
                ft.Text(valeur, size=26, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                ft.Text(label, size=12, color=TEXT_SUB),
                ft.Text(sous, size=11, color=couleur) if sous else ft.Container(height=0),
            ], spacing=6),
            bgcolor=CARD_BG,
            border_radius=20,
            border=ft.Border.all(1, CARD_BORDER),
            shadow=self._ombre(),
            padding=ft.Padding(left=18, top=18, right=18, bottom=18),
            expand=True,
        )

    def _carte(self, content) -> ft.Container:
        return ft.Container(
            content=content,
            bgcolor=CARD_BG,
            border_radius=20,
            border=ft.Border.all(1, CARD_BORDER),
            shadow=self._ombre(),
            padding=ft.Padding(left=18, top=18, right=18, bottom=18),
        )

    def _stat_ligne(self, label, valeur, couleur) -> ft.Row:
        return ft.Row(controls=[
            ft.Text(label, size=12, color=TEXT_SUB, expand=True),
            ft.Text(valeur, size=13, color=couleur, weight=ft.FontWeight.BOLD),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    def _legende(self, label, couleur, valeur) -> ft.Row:
        return ft.Row(controls=[
            ft.Container(width=10, height=10, bgcolor=couleur, border_radius=2),
            ft.Text(f"{label} ({valeur})", size=11, color=TEXT_SUB),
        ], spacing=6)

    def _raccourci(self, label, icon, couleur, handler) -> ft.Container:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Icon(icon, color=couleur, size=26),
                ft.Text(label, size=11, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            bgcolor=CARD_BG,
            border_radius=18,
            border=ft.Border.all(1, CARD_BORDER),
            shadow=self._ombre(couleur, 0.1),
            padding=ft.Padding(left=16, top=16, right=16, bottom=16),
            width=120,
            alignment=ft.Alignment(x=0, y=0),
            on_click=handler,
            ink=True,
            animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        )