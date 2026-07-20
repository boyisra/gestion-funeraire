"""
Vue Terrain — GI2 2026
Gestion du terrain : configuration, zones, caveaux
Design glassmorphism sombre — Flet 0.85+
"""
import flet as ft
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api_client import api, APIError
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

COULEURS_ZONES = [
    "#60a5fa", "#34d399", "#fbbf24", "#c084fc",
    "#f87171", "#2dd4bf", "#facc15", "#818cf8",
]


class TerrainView:
    def __init__(self, page: ft.Page, on_retour=None):
        self.page = page
        self.on_retour = on_retour
        self.config = None
        self.zones = []
        self.onglet_actif = "config"

    def build(self) -> ft.View:
        self.zone_content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        self._charger_donnees()

        corps = ft.Column(
            controls=[
                build_topbar(
                    self.page, ft.Icons.TERRAIN_ROUNDED, "Terrain & Zones",
                    on_refresh=lambda e: self._charger_donnees(),
                ),
                self._build_onglets(),
                ft.Container(
                    content=self.zone_content,
                    expand=True,
                    padding=ft.Padding(left=24, top=16, right=24, bottom=24),
                ),
            ],
            expand=True, spacing=0,
        )

        # Fond avec halos décoratifs
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
            route="/terrain",
            bgcolor=BG_DARK,
            padding=0,
            controls=[
                ft.Stack(
                    controls=[
                        fond,
                        ft.Row(
                            controls=[
                                build_sidebar(self.page, "/terrain"),
                                ft.Container(content=corps, expand=True, bgcolor=BG_DARK),
                            ],
                            expand=True, spacing=0,
                        ),
                    ],
                    expand=True,
                ),
            ],
        )

    def _build_onglets(self) -> ft.Container:
        onglets = [
            ("config", ft.Icons.SETTINGS, "Configuration"),
            ("zones", ft.Icons.MAP, "Zones"),
            ("caveaux", ft.Icons.GRID_VIEW, "Caveaux"),
            ("stats", ft.Icons.BAR_CHART, "Statistiques"),
        ]

        boutons = []
        for key, icon, label in onglets:
            actif = self.onglet_actif == key
            boutons.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(icon, size=16,
                                    color=ACCENT if actif else TEXT_SUB),
                            ft.Text(label, size=13,
                                    color=ACCENT if actif else TEXT_SUB,
                                    weight=ft.FontWeight.BOLD if actif else ft.FontWeight.NORMAL),
                        ],
                        spacing=6,
                    ),
                    padding=ft.Padding(left=16, top=10, right=16, bottom=10),
                    border=ft.Border.only(bottom=ft.BorderSide(2, ACCENT) if actif else ft.BorderSide(2, "transparent")),
                    on_click=lambda e, k=key: self._changer_onglet(k),
                    ink=True,
                )
            )

        return ft.Container(
            content=ft.Row(controls=boutons, spacing=0),
            bgcolor=CARD_BG,   # fond sombre pour la barre
            border=ft.Border.only(bottom=ft.BorderSide(1, CARD_BORDER)),
        )

    def _changer_onglet(self, key: str):
        self.onglet_actif = key
        self._rafraichir_contenu()

    def _charger_donnees(self):
        try:
            self.config = api.get("terrain/configuration/")
        except Exception:
            self.config = None
        try:
            self.zones = api.get("terrain/zones/") or []
        except Exception:
            self.zones = []
        self._rafraichir_contenu()

    def _rafraichir_contenu(self):
        self.zone_content.controls.clear()

        if self.onglet_actif == "config":
            self.zone_content.controls.append(self._build_config())
        elif self.onglet_actif == "zones":
            self.zone_content.controls.append(self._build_zones())
        elif self.onglet_actif == "caveaux":
            self.zone_content.controls.append(self._build_caveaux())
        elif self.onglet_actif == "stats":
            self.zone_content.controls.append(self._build_stats())

        self.page.update()

    # ─── Onglet Configuration (identique logique, UI sombre) ─────────────
    def _build_config(self) -> ft.Column:
        c = self.config or {}

        self.f_nom = ft.TextField(label="Nom du cimetière", value=str(c.get("nom_cimetiere", "")),
                                   bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
                                   focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
                                   border_radius=12)
        self.f_adresse = ft.TextField(label="Adresse", value=str(c.get("adresse", "")),
                                       bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
                                       focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
                                       multiline=True, min_lines=2, border_radius=12)
        self.f_tel = ft.TextField(label="Téléphone", value=str(c.get("telephone_contact", "")),
                                   bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
                                   focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
                                   border_radius=12)
        self.f_email = ft.TextField(label="Email", value=str(c.get("email_contact", "")),
                                     bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
                                     focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
                                     border_radius=12)
        self.f_superficie = ft.TextField(label="Superficie totale (m²)",
                                          value=str(c.get("superficie_totale_m2", "10000")),
                                          bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
                                          focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
                                          keyboard_type=ft.KeyboardType.NUMBER, border_radius=12)
        self.f_longueur = ft.TextField(label="Longueur caveau (m)",
                                        value=str(c.get("taille_caveau_longueur", "2.5")),
                                        bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
                                        focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
                                        keyboard_type=ft.KeyboardType.NUMBER, border_radius=12)
        self.f_largeur = ft.TextField(label="Largeur caveau (m)",
                                       value=str(c.get("taille_caveau_largeur", "1.2")),
                                       bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
                                       focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
                                       keyboard_type=ft.KeyboardType.NUMBER, border_radius=12)
        self.f_allee = ft.TextField(label="Largeur allée (m)",
                                     value=str(c.get("largeur_allee_m", "1.5")),
                                     bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
                                     focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
                                     keyboard_type=ft.KeyboardType.NUMBER, border_radius=12)
        self.f_tarif_temp = ft.TextField(label="Tarif concession temporaire (XAF)",
                                          value=str(c.get("tarif_concession_temporaire", "150000")),
                                          bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
                                          focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
                                          keyboard_type=ft.KeyboardType.NUMBER, border_radius=12)
        self.f_tarif_perp = ft.TextField(label="Tarif concession perpétuelle (XAF)",
                                          value=str(c.get("tarif_concession_perpetuelle", "500000")),
                                          bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
                                          focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
                                          keyboard_type=ft.KeyboardType.NUMBER, border_radius=12)

        places = c.get("places_totales_calculees", 0)
        self.label_places = ft.Text(
            f"📊 Places calculées : {places} caveaux",
            size=14, color=SUCCESS, weight=ft.FontWeight.BOLD,
        )

        self.msg_config = ft.Text("", color=SUCCESS, size=13, visible=False)

        return ft.Column(
            controls=[
                self._titre_section("⚙️ Paramètres du Cimetière"),
                self._carte(ft.Column(controls=[self.f_nom, self.f_adresse,
                                                 ft.Row(controls=[self.f_tel, self.f_email], spacing=12)], spacing=14)),
                self._titre_section("📐 Dimensions & Calcul"),
                self._carte(ft.Column(
                    controls=[
                        ft.Row(controls=[self.f_superficie, self.f_allee], spacing=12),
                        ft.Row(controls=[self.f_longueur, self.f_largeur], spacing=12),
                        ft.Container(
                            content=self.label_places,
                            bgcolor="rgba(52,211,153,0.1)",  # vert translucide
                            border_radius=14,
                            padding=ft.Padding(left=16, top=12, right=16, bottom=12),
                        ),
                        ft.TextButton(
                            content=ft.Row(controls=[
                                ft.Icon(ft.Icons.CALCULATE, color=ACCENT, size=16),
                                ft.Text("Recalculer", color=ACCENT),
                            ], spacing=6),
                            on_click=self._recalculer_places,
                        ),
                    ],
                    spacing=14,
                )),
                self._titre_section("💰 Tarifs (XAF)"),
                self._carte(ft.Row(controls=[self.f_tarif_temp, self.f_tarif_perp], spacing=12)),
                self.msg_config,
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Row(controls=[
                                    ft.Icon(ft.Icons.SAVE, color="#ffffff", size=18),
                                    ft.Text("Enregistrer", color="#ffffff", weight=ft.FontWeight.BOLD),
                                ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                                width=200, height=46, bgcolor=ACCENT, border_radius=16,
                                on_click=self._sauvegarder_config, ink=True,
                                shadow=ft.BoxShadow(spread_radius=0, blur_radius=12,
                                                    color=ft.colors.with_opacity(0.3, ACCENT),
                                                    offset=ft.Offset(0, 6)),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                    padding=ft.Padding(left=0, top=8, right=0, bottom=0),
                ),
            ],
            spacing=12,
        )

    # Les méthodes _recalculer_places et _sauvegarder_config restent identiques
    def _recalculer_places(self, e):
        try:
            superficie = float(self.f_superficie.value or 0)
            longueur = float(self.f_longueur.value or 0)
            largeur = float(self.f_largeur.value or 0)
            allee = float(self.f_allee.value or 0)
            import math
            surface_par_caveau = (longueur + allee) * (largeur + allee)
            exploitable = superficie * 0.80
            places = math.floor(exploitable / surface_par_caveau) if surface_par_caveau > 0 else 0
            self.label_places.value = f"📊 Places calculées : {places} caveaux"
            self.page.update()
        except Exception:
            pass

    def _sauvegarder_config(self, e):
        try:
            api.put("terrain/configuration/", data={
                "nom_cimetiere": self.f_nom.value,
                "adresse": self.f_adresse.value,
                "telephone_contact": self.f_tel.value,
                "email_contact": self.f_email.value,
                "superficie_totale_m2": float(self.f_superficie.value or 0),
                "taille_caveau_longueur": float(self.f_longueur.value or 0),
                "taille_caveau_largeur": float(self.f_largeur.value or 0),
                "largeur_allee_m": float(self.f_allee.value or 0),
                "tarif_concession_temporaire": float(self.f_tarif_temp.value or 0),
                "tarif_concession_perpetuelle": float(self.f_tarif_perp.value or 0),
            })
            self.msg_config.value = "✅ Configuration enregistrée !"
            self.msg_config.color = SUCCESS
            self.msg_config.visible = True
            self.page.update()
        except APIError as ex:
            self.msg_config.value = f"Erreur : {str(ex)}"
            self.msg_config.color = ERROR_C
            self.msg_config.visible = True
            self.page.update()

    # ─── Onglet Zones ─────────────────────────────────────────────────────
    def _build_zones(self) -> ft.Column:
        cartes_zones = []
        for z in self.zones:
            cartes_zones.append(self._carte_zone(z))

        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        self._titre_section("🗺️ Zones du Cimetière"),
                        ft.Container(
                            content=ft.Row(controls=[
                                ft.Icon(ft.Icons.ADD, color="#ffffff", size=16),
                                ft.Text("Nouvelle zone", color="#ffffff", weight=ft.FontWeight.BOLD, size=13),
                            ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
                            width=160, height=38, bgcolor=ACCENT, border_radius=14,
                            on_click=self._ouvrir_form_zone, ink=True,
                            shadow=ft.BoxShadow(spread_radius=0, blur_radius=8,
                                                color=ft.colors.with_opacity(0.3, ACCENT),
                                                offset=ft.Offset(0, 4)),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Column(controls=cartes_zones, spacing=10) if cartes_zones
                else ft.Container(
                    content=ft.Column(controls=[
                        ft.Icon(ft.Icons.MAP_OUTLINED, size=48, color=TEXT_SUB),
                        ft.Text("Aucune zone créée", color=TEXT_SUB, size=14),
                        ft.Text("Commencez par créer une section ou un bloc.", color=TEXT_SUB, size=12),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                    alignment=ft.Alignment(x=0, y=0),
                    height=200,
                ),
            ],
            spacing=14,
        )

    def _carte_zone(self, z: dict) -> ft.Container:
        taux = z.get("taux_occupation", 0)
        couleur_taux = SUCCESS if taux < 70 else WARNING if taux < 90 else ERROR_C

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(width=6, bgcolor=z.get("couleur_carte", "#60a5fa"),
                                 border_radius=ft.BorderRadius.only(top_left=8, bottom_left=8)),
                    ft.Column(
                        controls=[
                            ft.Row(controls=[
                                ft.Text(z.get("code", ""), size=16, weight=ft.FontWeight.BOLD, color=ACCENT),
                                ft.Text("—", color=TEXT_SUB),
                                ft.Text(z.get("nom", ""), size=14, color=TEXT_MAIN),
                                ft.Container(
                                    content=ft.Text(z.get("type_zone", ""), size=11, color=TEXT_SUB),
                                    bgcolor=INPUT_BG, border_radius=14,
                                    padding=ft.Padding(left=8, top=3, right=8, bottom=3),
                                ),
                            ], spacing=8),
                            ft.Row(controls=[
                                self._badge(f"🪦 {z.get('nombre_caveaux', 0)} caveaux", INPUT_BG),
                                self._badge(f"✅ {z.get('caveaux_disponibles', 0)} disponibles", "rgba(52,211,153,0.15)"),
                                ft.Text(f"Occupation : {taux}%", size=12, color=couleur_taux),
                            ], spacing=8),
                        ],
                        spacing=6,
                        expand=True,
                    ),
                ],
                spacing=0,
            ),
            bgcolor=CARD_BG,
            border_radius=14,
            border=ft.Border.all(1, CARD_BORDER),
            height=80,
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=6,
                                color=ft.colors.with_opacity(0.1, "#000000"),
                                offset=ft.Offset(0, 4)),
        )

    def _ouvrir_form_zone(self, e):
        """Ouvre un dialogue pour créer une zone (style sombre)"""
        f_nom = ft.TextField(label="Nom de la zone", bgcolor=INPUT_BG, color=TEXT_MAIN,
                              border_color=CARD_BORDER, focused_border_color=ACCENT,
                              label_style=ft.TextStyle(color=TEXT_SUB), border_radius=12)
        f_code = ft.TextField(label="Code (ex: A, B, BL1)", bgcolor=INPUT_BG, color=TEXT_MAIN,
                               border_color=CARD_BORDER, focused_border_color=ACCENT,
                               label_style=ft.TextStyle(color=TEXT_SUB), border_radius=12)
        f_type = ft.Dropdown(
            label="Type",
            options=[
                ft.dropdown.Option("SECTION", "Section"),
                ft.dropdown.Option("BLOC", "Bloc"),
                ft.dropdown.Option("ALLEE", "Allée principale"),
                ft.dropdown.Option("NON_EXPLOITABLE", "Non exploitable"),
            ],
            value="SECTION",
            bgcolor=INPUT_BG, color=TEXT_MAIN,
            border_color=CARD_BORDER, focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=TEXT_SUB), border_radius=12,
        )
        msg = ft.Text("", color=ERROR_C, size=12)

        def sauvegarder(e):
            if not f_nom.value or not f_code.value:
                msg.value = "Nom et code obligatoires"
                self.page.update()
                return
            try:
                api.post("terrain/zones/", data={
                    "nom": f_nom.value,
                    "code": f_code.value.upper(),
                    "type_zone": f_type.value,
                })
                self.page.close(dlg)
                self._charger_donnees()
            except APIError as ex:
                msg.value = str(ex)
                self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Nouvelle Zone", color=TEXT_MAIN, weight=ft.FontWeight.BOLD),
            bgcolor=CARD_BG,
            shape=ft.RoundedRectangleBorder(radius=16),
            content=ft.Column(controls=[f_nom, f_code, f_type, msg], spacing=12, width=360),
            actions=[
                ft.TextButton(content=ft.Text("Annuler", color=TEXT_SUB),
                              on_click=lambda e: self.page.close(dlg)),
                ft.Container(
                    content=ft.Text("Créer", color="#ffffff", weight=ft.FontWeight.BOLD),
                    bgcolor=ACCENT, border_radius=14,
                    padding=ft.Padding(left=20, top=8, right=20, bottom=8),
                    on_click=sauvegarder, ink=True,
                ),
            ],
        )
        self.page.open(dlg)

    # ─── Onglet Caveaux (grille adaptée, fond sombre) ────────────────────
    def _build_caveaux(self) -> ft.Column:
        if not self.zones:
            return ft.Column(controls=[
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Icon(ft.Icons.GRID_OFF, size=48, color=TEXT_SUB),
                        ft.Text("Créez d'abord des zones", color=TEXT_SUB, size=14),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                    alignment=ft.Alignment(x=0, y=0), height=200,
                )
            ])

        self.sel_zone = ft.Dropdown(
            label="Sélectionner une zone",
            options=[ft.dropdown.Option(z["id"], f"{z['code']} — {z['nom']}") for z in self.zones],
            bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
            focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
            on_change=self._charger_caveaux_zone,
            width=300,
            border_radius=12,
        )

        self.grille_caveaux = ft.Row(wrap=True, spacing=6, run_spacing=6)

        return ft.Column(
            controls=[
                ft.Row(controls=[self.sel_zone], alignment=ft.MainAxisAlignment.START),
                ft.Divider(height=1, color=CARD_BORDER),
                ft.Text("Légende :", color=TEXT_SUB, size=12),
                ft.Row(controls=[
                    self._badge_etat("DISPONIBLE", "#34d399"),
                    self._badge_etat("RÉSERVÉ", "#fbbf24"),
                    self._badge_etat("OCCUPÉ", "#f87171"),
                    self._badge_etat("NON EXPLOIT.", "#6b7280"),
                ], spacing=8),
                ft.Divider(height=1, color=CARD_BORDER),
                self.grille_caveaux,
            ],
            spacing=12,
        )

    def _charger_caveaux_zone(self, e):
        zone_id = self.sel_zone.value
        if not zone_id:
            return
        try:
            caveaux = api.get("terrain/caveaux/", params={"zone_id": zone_id}) or []
            self.grille_caveaux.controls.clear()
            for cv in caveaux:
                self.grille_caveaux.controls.append(self._case_caveau(cv))
            self.page.update()
        except Exception:
            pass

    def _case_caveau(self, cv: dict) -> ft.Container:
        couleurs = {
            'DISPONIBLE': '#34d399', 'RESERVE': '#fbbf24',
            'OCCUPE': '#f87171', 'NON_EXPLOITABLE': '#6b7280', 'ENTRETIEN': '#c084fc',
        }
        couleur = couleurs.get(cv.get("etat", ""), "#6b7280")
        return ft.Container(
            content=ft.Text(cv.get("numero", ""), size=9, color=ft.Colors.WHITE,
                            text_align=ft.TextAlign.CENTER),
            width=52, height=32,
            bgcolor=couleur,
            border_radius=14,
            alignment=ft.Alignment(x=0, y=0),
            tooltip=f"{cv.get('numero')} — {cv.get('etat')}",
        )

    # ─── Onglet Stats ─────────────────────────────────────────────────────
    def _build_stats(self) -> ft.Column:
        try:
            stats = api.get("terrain/stats/") or {}
        except Exception:
            stats = {}

        total = stats.get("total_caveaux", 0)
        dispo = stats.get("disponibles", 0)
        reserve = stats.get("reserves", 0)
        occupe = stats.get("occupes", 0)
        taux = stats.get("taux_occupation_global", 0)

        return ft.Column(
            controls=[
                self._titre_section("📊 Statistiques du Terrain"),
                ft.Row(
                    controls=[
                        self._stat_card("Total caveaux", str(total), ft.Icons.GRID_VIEW, ACCENT),
                        self._stat_card("Disponibles", str(dispo), ft.Icons.CHECK_CIRCLE, SUCCESS),
                        self._stat_card("Réservés", str(reserve), ft.Icons.SCHEDULE, WARNING),
                        self._stat_card("Occupés", str(occupe), ft.Icons.BLOCK, ERROR_C),
                    ],
                    spacing=12,
                    wrap=True,
                ),
                self._carte(ft.Column(controls=[
                    ft.Text("Taux d'occupation global", color=TEXT_SUB, size=13),
                    ft.Text(f"{taux}%", size=36, weight=ft.FontWeight.BOLD,
                            color=SUCCESS if taux < 70 else WARNING if taux < 90 else ERROR_C),
                    ft.ProgressBar(value=taux/100, bgcolor=INPUT_BG, color=ACCENT, height=12,
                                   border_radius=10),
                    ft.Text(f"Zones actives : {stats.get('total_zones', 0)}  •  "
                            f"Places calculées : {stats.get('places_calculees', 0)}",
                            size=12, color=TEXT_SUB),
                ], spacing=10)),
            ],
            spacing=14,
        )

    # ─── Helpers UI (adaptés au thème sombre) ─────────────────────────────
    def _titre_section(self, texte: str) -> ft.Text:
        return ft.Text(texte, size=15, weight=ft.FontWeight.BOLD, color=TEXT_MAIN)

    def _carte(self, content) -> ft.Container:
        return ft.Container(
            content=content,
            bgcolor=CARD_BG,
            border_radius=18,
            padding=ft.Padding(left=20, top=20, right=20, bottom=20),
            border=ft.Border.all(1, CARD_BORDER),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=15,
                                color=ft.colors.with_opacity(0.1, "#000000"),
                                offset=ft.Offset(0, 8)),
        )

    def _badge(self, texte: str, bgcolor: str) -> ft.Container:
        return ft.Container(
            content=ft.Text(texte, size=11, color=TEXT_SUB if bgcolor == INPUT_BG else TEXT_MAIN),
            bgcolor=bgcolor, border_radius=14,
            padding=ft.Padding(left=8, top=3, right=8, bottom=3),
        )

    def _badge_etat(self, label: str, couleur: str) -> ft.Row:
        return ft.Row(controls=[
            ft.Container(width=12, height=12, bgcolor=couleur, border_radius=2),
            ft.Text(label, size=11, color=TEXT_SUB),
        ], spacing=4)

    def _stat_card(self, label: str, valeur: str, icon, couleur: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Icon(icon, color=couleur, size=28),
                ft.Text(valeur, size=28, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                ft.Text(label, size=12, color=TEXT_SUB),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            bgcolor=CARD_BG, border_radius=18,
            padding=ft.Padding(left=20, top=20, right=20, bottom=20),
            border=ft.Border.all(1, CARD_BORDER),
            width=160,
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=10,
                                color=ft.colors.with_opacity(0.1, "#000000"),
                                offset=ft.Offset(0, 4)),
        )