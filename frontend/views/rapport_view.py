"""
Vue Rapports — GI2 2026
Statistiques avancées et exports CSV
Design glassmorphism sombre — Flet 0.85+
"""
import flet as ft
import webbrowser
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api_client import api, APIError
from utils.config import session, API_BASE_URL
from components.sidebar import build_sidebar, build_topbar

# ----- Palette sombre cohérente -----
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


class RapportView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.stats = {}
        self.zones = []
        self.canaux = []

    def build(self) -> ft.View:
        self._charger_donnees()
        self.contenu = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        self._construire_contenu()

        corps = ft.Column(
            controls=[
                build_topbar(
                    self.page, ft.Icons.INSIGHTS_ROUNDED, "Rapports & Statistiques",
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
                        Colors=["#8b5cf6", "#0f0f1a00"]
                    ),
                    top=-50, right=-50,
                ),
                ft.Container(
                    width=250, height=250,
                    gradient=ft.RadialGradient(
                        center=ft.alignment.center, radius=1.0,
                        Colors=["#ec4899", "#0f0f1a00"]
                    ),
                    bottom=-60, left=-60,
                ),
            ]
        )

        return ft.View(
            route="/rapports",
            bgcolor=BG_DARK,
            padding=0,
            controls=[
                ft.Stack(
                    controls=[
                        fond,
                        ft.Row(
                            controls=[
                                build_sidebar(self.page, "/rapports"),
                                ft.Container(content=corps, expand=True, bgcolor=BG_DARK),
                            ],
                            expand=True, spacing=0,
                        ),
                    ],
                    expand=True,
                ),
            ],
        )

    def _charger_donnees(self):
        try:
            self.stats = api.get("rapports/dashboard/") or {}
        except Exception:
            self.stats = {}
        try:
            self.zones = api.get("rapports/occupation-par-zone/") or []
        except Exception:
            self.zones = []
        try:
            self.canaux = api.get("rapports/revenus-par-canal/") or []
        except Exception:
            self.canaux = []

    def _actualiser(self):
        self._charger_donnees()
        self.contenu.controls.clear()
        self._construire_contenu()
        self.page.update()

    def _construire_contenu(self):
        s = self.stats

        self.contenu.controls = [

            # ── KPIs globaux ──────────────────────────────────────────
            ft.Text("Indicateurs Clés", size=15,
                    weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
            ft.Row(controls=[
                self._kpi("Total caveaux",
                          str(s.get('total_caveaux', 0)),
                          ft.Icons.GRID_VIEW, ACCENT),
                self._kpi("Taux occupation",
                          f"{s.get('taux_occupation', 0)}%",
                          ft.Icons.PIE_CHART,
                          SUCCESS if s.get('taux_occupation', 0) < 70
                          else WARNING if s.get('taux_occupation', 0) < 90 else ERROR_C),
                self._kpi("Revenus totaux",
                          f"{int(s.get('revenus_total', 0)):,} XAF",
                          ft.Icons.ACCOUNT_BALANCE_WALLET, SUCCESS),
                self._kpi("Concessions actives",
                          str(s.get('concessions_actives', 0)),
                          ft.Icons.DESCRIPTION, PURPLE),
            ], spacing=12, wrap=True),

            ft.Divider(height=24, color=CARD_BORDER),

            # ── Occupation par zone ───────────────────────────────────
            ft.Text("Occupation par Zone", size=15,
                    weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
            self._carte(self._build_graphe_zones()),

            ft.Divider(height=24, color=CARD_BORDER),

            # ── Revenus par canal ─────────────────────────────────────
            ft.Text("Revenus par Canal de Paiement", size=15,
                    weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
            self._carte(self._build_graphe_canaux()),

            ft.Divider(height=24, color=CARD_BORDER),

            # ── Exports CSV ───────────────────────────────────────────
            ft.Text("Exports des Registres", size=15,
                    weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
            ft.Row(controls=[
                self._btn_export(
                    "Registre des Réservations",
                    ft.Icons.TABLE_CHART, SUCCESS,
                    "rapports/export/reservations/",
                    "Exporte toutes les réservations en CSV",
                ),
                self._btn_export(
                    "Registre des Paiements",
                    ft.Icons.RECEIPT_LONG, WARNING,
                    "rapports/export/paiements/",
                    "Exporte tous les paiements en CSV",
                ),
                self._btn_export(
                    "Registre des Concessions",
                    ft.Icons.DESCRIPTION, PURPLE,
                    "rapports/export/concessions/",
                    "Exporte toutes les concessions en CSV",
                ),
            ], spacing=16, wrap=True),
        ]

    # ─── Graphe zones (barres verticales + tableau) ────────────────────────
    def _build_graphe_zones(self) -> ft.Column:
        if not self.zones:
            return ft.Column(controls=[
                ft.Text("Aucune zone configurée", color=TEXT_SUB, size=13)
            ])

        barres = []
        for z in self.zones:
            taux = z.get('taux', 0)
            couleur = (SUCCESS if taux < 70 else WARNING if taux < 90 else ERROR_C)
            total = z.get('total', 1) or 1

            barres.append(
                ft.Column(
                    controls=[
                        ft.Row(controls=[
                            ft.Column(controls=[
                                ft.Text(f"{taux}%", size=11,
                                        color=couleur, weight=ft.FontWeight.BOLD,
                                        text_align=ft.TextAlign.CENTER),
                                ft.Container(
                                    content=ft.Column(
                                        controls=[
                                            ft.Container(
                                                height=max(int(taux * 1.2), 4),
                                                bgcolor=couleur,
                                                border_radius=ft.BorderRadius.only(
                                                    top_left=4, top_right=4
                                                ),
                                                width=40,
                                            ),
                                        ],
                                        spacing=0,
                                        alignment=ft.MainAxisAlignment.END,
                                    ),
                                    height=120,
                                    bgcolor=INPUT_BG,   # fond sombre pour la barre
                                    border_radius=10,
                                    width=40,
                                    alignment=ft.Alignment(x=0, y=1),
                                    padding=ft.Padding(left=0, top=0, right=0, bottom=0),
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=4),
                        ]),
                        ft.Text(z.get('zone', ''), size=12,
                                color=TEXT_MAIN, weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text(f"{z.get('occupes',0)}/{z.get('total',0)}",
                                size=10, color=TEXT_SUB,
                                text_align=ft.TextAlign.CENTER),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                )
            )

        return ft.Column(controls=[
            ft.Row(controls=barres, spacing=20, wrap=True),
            ft.Divider(height=12, color=CARD_BORDER),
            self._tableau_zones(),
        ], spacing=12)

    def _tableau_zones(self) -> ft.Column:
        if not self.zones:
            return ft.Column()

        lignes = []
        # En-tête
        lignes.append(
            ft.Container(
                content=ft.Row(controls=[
                    ft.Text("Zone", size=12, color=TEXT_MAIN,
                            weight=ft.FontWeight.BOLD, expand=2),
                    ft.Text("Total", size=12, color=TEXT_MAIN,
                            weight=ft.FontWeight.BOLD, expand=1,
                            text_align=ft.TextAlign.CENTER),
                    ft.Text("Disponibles", size=12, color=SUCCESS,
                            weight=ft.FontWeight.BOLD, expand=1,
                            text_align=ft.TextAlign.CENTER),
                    ft.Text("Occupés", size=12, color=ERROR_C,
                            weight=ft.FontWeight.BOLD, expand=1,
                            text_align=ft.TextAlign.CENTER),
                    ft.Text("Taux", size=12, color=ACCENT,
                            weight=ft.FontWeight.BOLD, expand=1,
                            text_align=ft.TextAlign.RIGHT),
                ]),
                bgcolor=INPUT_BG,   # fond légèrement plus clair pour l'en-tête
                border_radius=10,
                padding=ft.Padding(left=12, top=8, right=12, bottom=8),
            )
        )

        for z in self.zones:
            taux = z.get('taux', 0)
            couleur_taux = (SUCCESS if taux < 70 else WARNING if taux < 90 else ERROR_C)
            lignes.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Row(controls=[
                            ft.Container(
                                width=10, height=10,
                                bgcolor=z.get('couleur', ACCENT),
                                border_radius=2,
                            ),
                            ft.Text(f"{z.get('zone','')} — {z.get('nom','')}",
                                    size=12, color=TEXT_MAIN, expand=True),
                        ], spacing=8, expand=2),
                        ft.Text(str(z.get('total', 0)), size=12, color=TEXT_SUB,
                                expand=1, text_align=ft.TextAlign.CENTER),
                        ft.Text(str(z.get('disponibles', 0)), size=12, color=SUCCESS,
                                expand=1, text_align=ft.TextAlign.CENTER),
                        ft.Text(str(z.get('occupes', 0)), size=12, color=ERROR_C,
                                expand=1, text_align=ft.TextAlign.CENTER),
                        ft.Text(f"{taux}%", size=12, color=couleur_taux,
                                weight=ft.FontWeight.BOLD,
                                expand=1, text_align=ft.TextAlign.RIGHT),
                    ]),
                    padding=ft.Padding(left=12, top=8, right=12, bottom=8),
                    border=ft.Border.only(bottom=ft.BorderSide(1, CARD_BORDER)),
                )
            )

        return ft.Column(controls=lignes, spacing=0)

    # ─── Graphe canaux ────────────────────────────────────────────────────
    def _build_graphe_canaux(self) -> ft.Column:
        canaux_config = {
            'MOBILE_MONEY': ('MTN Mobile Money', '#fbbf24'),   # jaune
            'AIRTEL_MONEY': ('Airtel Money',     '#f87171'),   # rouge clair
            'ESPECES':      ('Espèces',           '#34d399'),   # vert
            'VIREMENT':     ('Virement',          '#a78bfa'),   # violet
        }

        total_global = sum(c.get('total', 0) for c in self.canaux)
        if total_global == 0:
            return ft.Column(controls=[
                ft.Text("Aucun paiement confirmé", color=TEXT_SUB, size=13)
            ])

        cartes = []
        for c in self.canaux:
            label, couleur = canaux_config.get(c.get('canal', ''),
                                                (c.get('canal', ''), ACCENT))
            montant = c.get('total', 0)
            count   = c.get('count', 0)
            pct     = round((montant / total_global * 100), 1) if total_global > 0 else 0

            cartes.append(
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Row(controls=[
                            ft.Container(
                                width=12, height=12,
                                bgcolor=couleur, border_radius=2,
                            ),
                            ft.Text(label, size=12, color=TEXT_MAIN,
                                    weight=ft.FontWeight.BOLD),
                        ], spacing=8),
                        ft.Text(f"{int(montant):,} XAF", size=18,
                                color=couleur, weight=ft.FontWeight.BOLD),
                        ft.ProgressBar(
                            value=pct / 100,
                            bgcolor=INPUT_BG,
                            color=couleur,
                            height=8,
                            border_radius=14,
                        ),
                        ft.Row(controls=[
                            ft.Text(f"{pct}% du total", size=11, color=TEXT_SUB),
                            ft.Text(f"{count} transaction(s)", size=11, color=TEXT_SUB),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ], spacing=8),
                    bgcolor=INPUT_BG,   # carte sombre
                    border_radius=16,
                    border=ft.Border.all(1, couleur),
                    padding=ft.Padding(left=16, top=14, right=16, bottom=14),
                    expand=True,
                )
            )

        return ft.Column(controls=[
            ft.Row(controls=cartes, spacing=12, wrap=True),
            ft.Divider(height=8, color=CARD_BORDER),
            ft.Row(controls=[
                ft.Text("Total revenus confirmés :", color=TEXT_SUB, size=13),
                ft.Text(f"{int(total_global):,} XAF", size=16,
                        color=SUCCESS, weight=ft.FontWeight.BOLD),
            ], spacing=10),
        ], spacing=12)

    # ─── Helpers UI (thème sombre) ────────────────────────────────────────
    def _kpi(self, label: str, valeur: str, icon, couleur: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Icon(icon, color=couleur, size=28),
                ft.Text(valeur, size=22, weight=ft.FontWeight.BOLD,
                        color=TEXT_MAIN, text_align=ft.TextAlign.CENTER),
                ft.Text(label, size=11, color=TEXT_SUB,
                        text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            bgcolor=CARD_BG,
            border_radius=18,
            border=ft.Border.all(1, CARD_BORDER),
            shadow=ft.BoxShadow(
                spread_radius=0, blur_radius=15,
                color=ft.Colors.with_opacity(0.1, "#000000"),
                offset=ft.Offset(0, 8),
            ),
            padding=ft.Padding(left=20, top=18, right=20, bottom=18),
            expand=True,
        )

    def _carte(self, content) -> ft.Container:
        return ft.Container(
            content=content,
            bgcolor=CARD_BG,
            border_radius=18,
            border=ft.Border.all(1, CARD_BORDER),
            shadow=ft.BoxShadow(
                spread_radius=0, blur_radius=15,
                color=ft.Colors.with_opacity(0.1, "#000000"),
                offset=ft.Offset(0, 8),
            ),
            padding=ft.Padding(left=20, top=20, right=20, bottom=20),
        )

    def _btn_export(self, label: str, icon, couleur: str,
                    endpoint: str, description: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Icon(icon, color=couleur, size=24),
                    ft.Text(label, size=13, color=TEXT_MAIN,
                            weight=ft.FontWeight.BOLD),
                ], spacing=10),
                ft.Text(description, size=11, color=TEXT_SUB),
                ft.Row(controls=[
                    ft.Icon(ft.Icons.DOWNLOAD, color=couleur, size=14),
                    ft.Text("Télécharger CSV", color=couleur, size=12,
                            weight=ft.FontWeight.BOLD),
                ], spacing=6),
            ], spacing=8),
            bgcolor=CARD_BG,
            border_radius=18,
            border=ft.Border.all(1, couleur),
            shadow=ft.BoxShadow(
                spread_radius=0, blur_radius=10,
                color=ft.Colors.with_opacity(0.2, couleur),
                offset=ft.Offset(0, 6),
            ),
            padding=ft.Padding(left=16, top=16, right=16, bottom=16),
            on_click=lambda e, ep=endpoint: webbrowser.open(
                f"{API_BASE_URL}/{ep}?token={session.token_acces or ''}"
            ),
            ink=True,
            width=260,
        )