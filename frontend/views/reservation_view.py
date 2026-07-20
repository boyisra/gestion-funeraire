"""
Vue Réservation — GI2 2026
Formulaire de réservation client + liste de validation admin
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

COULEURS_STATUTS = {
    'EN_ATTENTE': ('#fbbf24', 'rgba(251,191,36,0.15)'),
    'VALIDEE':    ('#34d399', 'rgba(52,211,153,0.15)'),
    'ANNULEE':    ('#f87171', 'rgba(248,113,113,0.15)'),
    'EXPIREE':    ('#94a3b8', 'rgba(148,163,184,0.15)'),
}


class ReservationView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.reservations = []
        self.onglet_actif = "liste" if session.est_staff() else "nouvelle"
        self.caveau_preselectionne = None

    def build(self) -> ft.View:
        self._charger_reservations()
        self.contenu = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        self._rafraichir_contenu()

        corps = ft.Column(
            controls=[
                build_topbar(
                    self.page, ft.Icons.EVENT_AVAILABLE_ROUNDED, "Réservations",
                    extra_controls=[
                        self._badge_stat("En attente",
                                         sum(1 for r in self.reservations if r['statut'] == 'EN_ATTENTE'),
                                         WARNING),
                        self._badge_stat("Validées",
                                         sum(1 for r in self.reservations if r['statut'] == 'VALIDEE'),
                                         SUCCESS),
                    ],
                ),
                self._build_onglets(),
                ft.Container(
                    content=self.contenu,
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
            route="/reservations",
            bgcolor=BG_DARK,
            padding=0,
            controls=[
                ft.Stack(
                    controls=[
                        fond,
                        ft.Row(
                            controls=[
                                build_sidebar(self.page, "/reservations"),
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
        onglets = [("nouvelle", ft.Icons.ADD_CIRCLE, "Nouvelle réservation")]
        if session.est_staff():
            onglets = [
                ("liste", ft.Icons.LIST_ALT, "Toutes les réservations"),
                ("en_attente", ft.Icons.HOURGLASS_EMPTY, "En attente"),
                ("nouvelle", ft.Icons.ADD_CIRCLE, "Nouvelle"),
            ]

        boutons = []
        for key, icon, label in onglets:
            actif = self.onglet_actif == key
            boutons.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(icon, size=15, color=ACCENT if actif else TEXT_SUB),
                        ft.Text(label, size=13,
                                color=ACCENT if actif else TEXT_SUB,
                                weight=ft.FontWeight.BOLD if actif else ft.FontWeight.NORMAL),
                    ], spacing=6),
                    padding=ft.Padding(left=16, top=10, right=16, bottom=10),
                    border=ft.Border.only(
                        bottom=ft.BorderSide(2, ACCENT if actif else "transparent")
                    ),
                    on_click=lambda e, k=key: self._changer_onglet(k),
                    ink=True,
                )
            )

        return ft.Container(
            content=ft.Row(controls=boutons, spacing=0),
            bgcolor=CARD_BG,  # fond sombre pour la barre d'onglets
            border=ft.Border.only(bottom=ft.BorderSide(1, CARD_BORDER)),
        )

    def _changer_onglet(self, key: str):
        self.onglet_actif = key
        self._rafraichir_contenu()

    def _rafraichir_contenu(self):
        self.contenu.controls.clear()
        if self.onglet_actif == "liste":
            self.contenu.controls.append(self._build_liste(self.reservations))
        elif self.onglet_actif == "en_attente":
            en_attente = [r for r in self.reservations if r['statut'] == 'EN_ATTENTE']
            self.contenu.controls.append(self._build_liste(en_attente))
        elif self.onglet_actif == "nouvelle":
            self.contenu.controls.append(self._build_formulaire())
        self.page.update()

    def _charger_reservations(self):
        try:
            self.reservations = api.get("reservations/") or []
        except Exception:
            self.reservations = []

    # ─── Liste des réservations ───────────────────────────────────────────
    def _build_liste(self, reservations: list) -> ft.Column:
        if not reservations:
            return ft.Column(controls=[
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Icon(ft.Icons.INBOX, size=48, color=TEXT_SUB),
                        ft.Text("Aucune réservation", color=TEXT_SUB, size=14),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                    alignment=ft.Alignment(x=0, y=0), height=200,
                )
            ])

        lignes = [self._ligne_reservation(r) for r in reservations]
        return ft.Column(controls=lignes, spacing=8)

    def _ligne_reservation(self, r: dict) -> ft.Container:
        statut = r.get('statut', '')
        couleur_txt, couleur_bg = COULEURS_STATUTS.get(statut, (TEXT_SUB, INPUT_BG))

        actions = []
        if statut == 'EN_ATTENTE' and session.est_staff():
            actions.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color="#ffffff", size=14),
                        ft.Text("Valider", color="#ffffff", size=12,
                                weight=ft.FontWeight.BOLD),
                    ], spacing=4),
                    bgcolor=SUCCESS, border_radius=10,
                    padding=ft.Padding(left=12, top=6, right=12, bottom=6),
                    on_click=lambda e, rid=r['id']: self._ouvrir_validation(rid),
                    ink=True,
                )
            )
        if statut == 'EN_ATTENTE':
            actions.append(
                ft.Container(
                    content=ft.Text("Annuler", color=ERROR_C, size=12),
                    border=ft.Border.all(1, ERROR_C), border_radius=10,
                    padding=ft.Padding(left=12, top=6, right=12, bottom=6),
                    on_click=lambda e, rid=r['id']: self._annuler(rid),
                    ink=True,
                )
            )

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=6, bgcolor=couleur_txt,
                        border_radius=ft.BorderRadius.only(top_left=8, bottom_left=8),
                    ),
                    ft.Column(
                        controls=[
                            ft.Row(controls=[
                                ft.Text(r.get('reference', ''), size=14,
                                        weight=ft.FontWeight.BOLD, color=ACCENT),
                                ft.Container(
                                    content=ft.Text(statut.replace('_', ' '), size=11,
                                                    color=couleur_txt),
                                    bgcolor=couleur_bg, border_radius=16,
                                    padding=ft.Padding(left=8, top=3, right=8, bottom=3),
                                ),
                            ], spacing=10),
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.PERSON, size=13, color=TEXT_SUB),
                                ft.Text(r.get('client_nom', ''), size=12, color=TEXT_MAIN),
                                ft.Text("·", color=TEXT_SUB),
                                ft.Icon(ft.Icons.LOCATION_ON, size=13, color=TEXT_SUB),
                                ft.Text(f"Caveau {r.get('caveau_numero','')}", size=12, color=TEXT_MAIN),
                                ft.Text("·", color=TEXT_SUB),
                                ft.Icon(ft.Icons.CALENDAR_TODAY, size=13, color=TEXT_SUB),
                                ft.Text(r.get('date_soumission', ''), size=12, color=TEXT_SUB),
                            ], spacing=6),
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.PERSON_OUTLINE, size=13, color=TEXT_SUB),
                                ft.Text(
                                    f"Défunt : {r.get('defunt_prenom','')} {r.get('defunt_nom','')}",
                                    size=12, color=TEXT_SUB,
                                ),
                                ft.Text("·", color=TEXT_SUB),
                                ft.Text(
                                    f"Inhumation : {r.get('date_inhumation','')}",
                                    size=12, color=TEXT_SUB,
                                ),
                            ], spacing=6),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Row(controls=actions, spacing=8),
                ],
                spacing=0,
            ),
            bgcolor=CARD_BG,
            border_radius=14,
            border=ft.Border.all(1, CARD_BORDER),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=10,
                                color=ft.colors.with_opacity(0.1, "#000000"),
                                offset=ft.Offset(0, 4)),
            padding=ft.Padding(left=0, top=12, right=16, bottom=12),
        )

    def _ouvrir_validation(self, reservation_id: str):
        f_montant = ft.TextField(
            label="Montant total (XAF)", value="150000",
            bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
            focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
            keyboard_type=ft.KeyboardType.NUMBER, border_radius=12,
        )
        f_notes = ft.TextField(
            label="Notes (optionnel)",
            bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
            focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
            multiline=True, min_lines=2, border_radius=12,
        )
        msg = ft.Text("", color=ERROR_C, size=12)

        def confirmer(e):
            try:
                api.post(f"reservations/{reservation_id}/valider/", data={
                    "montant_total": float(f_montant.value or 0),
                    "notes_admin": f_notes.value or "",
                })
                self.page.close(dlg)
                self._charger_reservations()
                self._rafraichir_contenu()
            except APIError as ex:
                msg.value = str(ex)
                self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Valider la réservation", color=TEXT_MAIN,
                          weight=ft.FontWeight.BOLD),
            bgcolor=CARD_BG,
            shape=ft.RoundedRectangleBorder(radius=16),
            content=ft.Column(controls=[
                ft.Text("Confirmez la validation et définissez le montant :",
                        color=TEXT_SUB, size=13),
                f_montant, f_notes, msg,
            ], spacing=12, width=380),
            actions=[
                ft.TextButton(
                    content=ft.Text("Annuler", color=TEXT_SUB),
                    on_click=lambda e: self.page.close(dlg),
                ),
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color="#ffffff", size=16),
                        ft.Text("Valider", color="#ffffff", weight=ft.FontWeight.BOLD),
                    ], spacing=6),
                    bgcolor=SUCCESS, border_radius=14,
                    padding=ft.Padding(left=16, top=8, right=16, bottom=8),
                    on_click=confirmer, ink=True,
                ),
            ],
        )
        self.page.open(dlg)

    def _annuler(self, reservation_id: str):
        try:
            api.post(f"reservations/{reservation_id}/annuler/")
            self._charger_reservations()
            self._rafraichir_contenu()
        except APIError as ex:
            pass

    # ─── Formulaire nouvelle réservation ─────────────────────────────────
    def _build_formulaire(self) -> ft.Column:
        try:
            caveaux_dispo = api.get("terrain/caveaux/", params={"etat": "DISPONIBLE"}) or []
        except Exception:
            caveaux_dispo = []

        self.f_caveau = ft.Dropdown(
            label="Caveau disponible",
            options=[
                ft.dropdown.Option(c['id'], f"{c.get('caveau_zone', c.get('zone_code',''))} — {c['numero']}")
                for c in caveaux_dispo
            ],
            bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
            focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
            hint_text="Sélectionner un caveau",
            border_radius=12,
        )

        self.f_def_nom    = self._champ("Nom du défunt")
        self.f_def_prenom = self._champ("Prénom du défunt")
        self.f_def_deces  = self._champ("Date de décès (AAAA-MM-JJ)")
        self.f_def_naiss  = self._champ("Date de naissance (optionnel)")
        self.f_def_acte   = self._champ("N° acte de décès (optionnel)")
        self.f_def_lieu   = self._champ("Lieu de décès (optionnel)")
        self.f_inhumation = self._champ("Date d'inhumation (AAAA-MM-JJ)")

        self.msg = ft.Container(visible=False)

        return ft.Column(
            controls=[
                self._titre("📋 Nouvelle Réservation"),

                self._carte(ft.Column(controls=[
                    ft.Text("Sélection du caveau", color=TEXT_SUB, size=13),
                    self.f_caveau,
                    ft.Row(controls=[
                        ft.Icon(ft.Icons.INFO_OUTLINE, color=ACCENT, size=14),
                        ft.Text(f"{len(caveaux_dispo)} caveau(x) disponible(s)",
                                color=TEXT_SUB, size=12),
                    ], spacing=6),
                ], spacing=10)),

                self._titre("⚰️ Informations du Défunt"),
                self._carte(ft.Column(controls=[
                    ft.Row(controls=[self.f_def_nom, self.f_def_prenom], spacing=12),
                    ft.Row(controls=[self.f_def_deces, self.f_def_naiss], spacing=12),
                    ft.Row(controls=[self.f_def_acte, self.f_def_lieu], spacing=12),
                ], spacing=12)),

                self._titre("📅 Date d'Inhumation"),
                self._carte(self.f_inhumation),

                self.msg,

                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Row(controls=[
                                ft.Icon(ft.Icons.SEND, color="#ffffff", size=18),
                                ft.Text("Soumettre la réservation", color="#ffffff",
                                        weight=ft.FontWeight.BOLD),
                            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                            width=280, height=48, bgcolor=ACCENT, border_radius=18,
                            on_click=self._soumettre, ink=True,
                            shadow=ft.BoxShadow(spread_radius=0, blur_radius=12,
                                                color=ft.colors.with_opacity(0.3, ACCENT),
                                                offset=ft.Offset(0, 6)),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=12,
        )

    def _soumettre(self, e):
        if not self.f_caveau.value:
            self._msg_erreur("Veuillez sélectionner un caveau.")
            return
        if not self.f_def_nom.value or not self.f_def_prenom.value:
            self._msg_erreur("Nom et prénom du défunt obligatoires.")
            return
        if not self.f_def_deces.value or not self.f_inhumation.value:
            self._msg_erreur("Date de décès et date d'inhumation obligatoires.")
            return

        try:
            data = {
                "caveau_id": self.f_caveau.value,
                "date_inhumation": self.f_inhumation.value,
                "defunt": {
                    "nom": self.f_def_nom.value,
                    "prenom": self.f_def_prenom.value,
                    "date_deces": self.f_def_deces.value,
                    "date_naissance": self.f_def_naiss.value or None,
                    "numero_acte_deces": self.f_def_acte.value or "",
                    "lieu_deces": self.f_def_lieu.value or "",
                },
            }
            reponse = api.post("reservations/", data=data)
            self._msg_succes(
                f"✅ Réservation {reponse.get('reference','')} soumise ! "
                f"En attente de validation."
            )
            for f in [self.f_def_nom, self.f_def_prenom, self.f_def_deces,
                      self.f_def_naiss, self.f_def_acte, self.f_def_lieu, self.f_inhumation]:
                f.value = ""
            self.f_caveau.value = None
            self.page.update()

        except APIError as ex:
            self._msg_erreur(str(ex))

    def _msg_erreur(self, texte: str):
        self.msg.content = ft.Row(controls=[
            ft.Icon(ft.Icons.ERROR_OUTLINE, color=ERROR_C, size=16),
            ft.Text(texte, color=ERROR_C, size=13),
        ], spacing=8)
        self.msg.bgcolor = "rgba(248,113,113,0.1)"
        self.msg.border_radius = 12
        self.msg.padding = ft.Padding(left=12, top=10, right=12, bottom=10)
        self.msg.visible = True
        self.page.update()

    def _msg_succes(self, texte: str):
        self.msg.content = ft.Row(controls=[
            ft.Icon(ft.Icons.CHECK_CIRCLE, color=SUCCESS, size=16),
            ft.Text(texte, color=SUCCESS, size=13),
        ], spacing=8)
        self.msg.bgcolor = "rgba(52,211,153,0.1)"
        self.msg.border_radius = 12
        self.msg.padding = ft.Padding(left=12, top=10, right=12, bottom=10)
        self.msg.visible = True
        self.page.update()

    # ─── Helpers UI (sombre) ──────────────────────────────────────────────
    def _champ(self, label: str, **kwargs) -> ft.TextField:
        return ft.TextField(
            label=label, bgcolor=INPUT_BG, color=TEXT_MAIN,
            border_color=CARD_BORDER, focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=TEXT_SUB),
            border_radius=12,
            expand=True, **kwargs,
        )

    def _titre(self, texte: str) -> ft.Text:
        return ft.Text(texte, size=15, weight=ft.FontWeight.BOLD, color=TEXT_MAIN)

    def _carte(self, content) -> ft.Container:
        return ft.Container(
            content=content,
            bgcolor=CARD_BG, border_radius=18,
            padding=ft.Padding(left=20, top=20, right=20, bottom=20),
            border=ft.Border.all(1, CARD_BORDER),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=15,
                                color=ft.colors.with_opacity(0.1, "#000000"),
                                offset=ft.Offset(0, 8)),
        )

    def _badge_stat(self, label: str, valeur: int, couleur: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Text(str(valeur), size=18, weight=ft.FontWeight.BOLD, color=couleur),
                ft.Text(label, size=10, color=TEXT_SUB),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            bgcolor=CARD_BG, border_radius=14,
            padding=ft.Padding(left=14, top=6, right=14, bottom=6),
            border=ft.Border.all(1, CARD_BORDER),
        )