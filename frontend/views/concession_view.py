"""
Vue Concessions & Exhumations — GI2 2026
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
ACCENT_HOVER = "#c4b5fd"
TEXT_MAIN    = "#f1f5f9"
TEXT_SUB     = "#94a3b8"
BORDER       = "#2a2a3e"
ERROR_C      = "#f87171"
SUCCESS      = "#34d399"
WARNING      = "#fbbf24"
PURPLE       = "#c084fc"
INFO         = "#60a5fa"

# Couleurs des statuts adaptées au fond sombre
COULEURS_STATUTS_CON = {
    'ACTIVE':            ('#34d399', 'rgba(52, 211, 153, 0.15)'),
    'EXPIREE':           ('#f87171', 'rgba(248, 113, 113, 0.15)'),
    'RESILIEE':          ('#94a3b8', 'rgba(148, 163, 184, 0.15)'),
    'EN_RENOUVELLEMENT': ('#fbbf24', 'rgba(251, 191, 36, 0.15)'),
}

COULEURS_STATUTS_EXH = {
    'SOUMISE':        ('#fbbf24', 'rgba(251, 191, 36, 0.15)'),
    'EN_INSTRUCTION': ('#a78bfa', 'rgba(167, 139, 250, 0.15)'),
    'AUTORISEE':      ('#34d399', 'rgba(52, 211, 153, 0.15)'),
    'REFUSEE':        ('#f87171', 'rgba(248, 113, 113, 0.15)'),
    'EXECUTEE':       ('#94a3b8', 'rgba(148, 163, 184, 0.15)'),
}


class ConcessionView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.concessions = []
        self.exhumations = []
        self.onglet_actif = "concessions"

    def build(self) -> ft.View:
        self._charger_donnees()
        self.contenu = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        self._rafraichir_contenu()

        actives   = sum(1 for c in self.concessions if c.get('statut') == 'ACTIVE')
        expirant  = sum(1 for c in self.concessions
                        if c.get('jours_restants') is not None and 0 < c['jours_restants'] <= 90)
        en_attente_exh = sum(1 for e in self.exhumations if e.get('statut') == 'SOUMISE')

        corps = ft.Column(
            controls=[
                build_topbar(
                    self.page, ft.Icons.ARTICLE_ROUNDED, "Concessions & Exhumations",
                    extra_controls=[
                        self._badge_stat("Actives", actives, SUCCESS),
                        self._badge_stat("Expirant bientôt", expirant, WARNING),
                        self._badge_stat("Exhum. en attente", en_attente_exh, PURPLE),
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

        # Fond avec halos décoratifs identique au login
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
            route="/concessions",
            bgcolor=BG_DARK,
            padding=0,
            controls=[
                ft.Stack(
                    controls=[
                        fond,
                        ft.Row(
                            controls=[
                                build_sidebar(self.page, "/concessions"),
                                ft.Container(content=corps, expand=True, bgcolor=BG_DARK),
                            ],
                            expand=True, spacing=0,
                        ),
                    ],
                    expand=True,
                ),
            ],
        )

    # ----- Onglets (inchangé dans la structure, juste les couleurs) -----
    def _build_onglets(self) -> ft.Container:
        onglets = [
            ("concessions", ft.Icons.DESCRIPTION,      "Concessions"),
            ("expirant",    ft.Icons.WARNING,           "Expirant bientôt"),
            ("exhumations", ft.Icons.REMOVE_CIRCLE,     "Exhumations"),
        ]
        if session.est_staff():
            onglets.append(("nouvelle_con", ft.Icons.ADD_CIRCLE, "Nouvelle concession"))

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
            bgcolor=CARD_BG,
            border=ft.Border.only(bottom=ft.BorderSide(1, CARD_BORDER)),
        )

    def _changer_onglet(self, key: str):
        self.onglet_actif = key
        self._rafraichir_contenu()

    def _charger_donnees(self):
        try:
            self.concessions = api.get("concessions/") or []
        except Exception:
            self.concessions = []
        try:
            self.exhumations = api.get("concessions/exhumations/") or []
        except Exception:
            self.exhumations = []

    def _rafraichir_contenu(self):
        self.contenu.controls.clear()

        if self.onglet_actif == "concessions":
            self.contenu.controls.append(self._build_liste_concessions(self.concessions))
        elif self.onglet_actif == "expirant":
            expirant = [c for c in self.concessions
                        if c.get('jours_restants') is not None and 0 < c['jours_restants'] <= 90]
            self.contenu.controls.append(self._build_liste_concessions(expirant, mode_alerte=True))
        elif self.onglet_actif == "exhumations":
            self.contenu.controls.append(self._build_liste_exhumations())
        elif self.onglet_actif == "nouvelle_con":
            self.contenu.controls.append(self._build_form_concession())

        self.page.update()

    # ─── Liste Concessions ────────────────────────────────────────────────
    def _build_liste_concessions(self, concessions: list, mode_alerte=False) -> ft.Column:
        if not concessions:
            return ft.Column(controls=[
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, size=48, color=TEXT_SUB),
                        ft.Text("Aucune concession", color=TEXT_SUB, size=14),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                    alignment=ft.Alignment(x=0, y=0), height=200,
                )
            ])

        lignes = [self._carte_concession(c, mode_alerte) for c in concessions]
        return ft.Column(controls=lignes, spacing=8)

    def _carte_concession(self, c: dict, mode_alerte=False) -> ft.Container:
        statut = c.get('statut', '')
        couleur_txt, couleur_bg = COULEURS_STATUTS_CON.get(statut, (TEXT_SUB, 'rgba(148,163,184,0.15)'))
        jours = c.get('jours_restants')

        # Alerte expiration
        alerte = ft.Container(visible=False)
        if jours is not None and 0 < jours <= 90:
            alerte = ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.WARNING, color=WARNING, size=14),
                    ft.Text(f"Expire dans {jours} jours !", color=WARNING, size=12),
                ], spacing=6),
                bgcolor='rgba(251,191,36,0.1)',
                border_radius=10,
                padding=ft.Padding(left=10, top=4, right=10, bottom=4),
                visible=True,
            )

        type_labels = {
            'TEMPORAIRE': '5 ans', 'RENOUVELABLE': '15 ans', 'PERPETUELLE': 'Perpétuelle'
        }

        actions = []
        if statut in ('ACTIVE', 'EN_RENOUVELLEMENT') and session.est_staff():
            actions.append(self._btn_action(
                "Renouveler", ft.Icons.REFRESH, ACCENT,
                lambda e, cid=c['id']: self._ouvrir_renouvellement(cid)
            ))
        if session.est_staff():
            actions.append(self._btn_action(
                "Exhumation", ft.Icons.REMOVE_CIRCLE, PURPLE,
                lambda e, cid=c['id']: self._ouvrir_demande_exhumation(cid)
            ))

        # Carte sombre avec barre colorée à gauche
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
                                ft.Text(c.get('reference', ''), size=14,
                                        weight=ft.FontWeight.BOLD, color=ACCENT),
                                ft.Container(
                                    content=ft.Text(statut.replace('_', ' '), size=11,
                                                    color=couleur_txt),
                                    bgcolor=couleur_bg, border_radius=16,
                                    padding=ft.Padding(left=8, top=3, right=8, bottom=3),
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        type_labels.get(c.get('type_concession', ''), ''),
                                        size=11, color=TEXT_SUB,
                                    ),
                                    bgcolor=INPUT_BG, border_radius=14,
                                    padding=ft.Padding(left=8, top=3, right=8, bottom=3),
                                ),
                                alerte,
                            ], spacing=8, wrap=True),
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.PERSON, size=13, color=TEXT_SUB),
                                ft.Text(c.get('titulaire_nom', ''), size=12, color=TEXT_MAIN),
                                ft.Text("·", color=TEXT_SUB),
                                ft.Icon(ft.Icons.LOCATION_ON, size=13, color=TEXT_SUB),
                                ft.Text(f"Caveau {c.get('caveau_numero','')}", size=12, color=TEXT_MAIN),
                            ], spacing=6),
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.DATE_RANGE, size=13, color=TEXT_SUB),
                                ft.Text(
                                    f"Début : {c.get('date_debut','')}  "
                                    f"{'— Fin : ' + str(c.get('date_fin','')) if c.get('date_fin') else '— Perpétuelle'}",
                                    size=12, color=TEXT_SUB,
                                ),
                                ft.Text("·", color=TEXT_SUB),
                                ft.Icon(ft.Icons.PAYMENTS, size=13, color=TEXT_SUB),
                                ft.Text(f"{int(c.get('prix_total',0)):,} XAF", size=12, color=SUCCESS),
                            ], spacing=6),
                        ],
                        spacing=5,
                        expand=True,
                    ),
                    ft.Row(controls=actions, spacing=8),
                ],
                spacing=0,
            ),
            bgcolor=CARD_BG,
            border_radius=14,
            border=ft.Border.all(1, CARD_BORDER),
            padding=ft.Padding(left=0, top=12, right=16, bottom=12),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=10,
                                color=ft.Colors.with_opacity(0.1, "#000000"),
                                offset=ft.Offset(0, 4)),
        )

    # ─── Liste Exhumations ────────────────────────────────────────────────
    def _build_liste_exhumations(self) -> ft.Column:
        titre_row = ft.Row(
            controls=[
                ft.Text("Demandes d'Exhumation", size=15,
                        weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.Icons.ADD, color="#ffffff", size=15),
                        ft.Text("Nouvelle demande", color="#ffffff",
                                size=12, weight=ft.FontWeight.BOLD),
                    ], spacing=6),
                    bgcolor=PURPLE, border_radius=14,
                    padding=ft.Padding(left=12, top=6, right=12, bottom=6),
                    on_click=lambda e: self._ouvrir_demande_exhumation(None),
                    ink=True,
                    shadow=ft.BoxShadow(spread_radius=0, blur_radius=8,
                                        color=ft.Colors.with_opacity(0.3, PURPLE),
                                        offset=ft.Offset(0, 4)),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        if not self.exhumations:
            return ft.Column(controls=[
                titre_row,
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Icon(ft.Icons.REMOVE_CIRCLE_OUTLINE, size=48, color=TEXT_SUB),
                        ft.Text("Aucune demande d'exhumation", color=TEXT_SUB, size=14),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                    alignment=ft.Alignment(x=0, y=0), height=200,
                ),
            ], spacing=12)

        lignes = [self._carte_exhumation(e) for e in self.exhumations]
        return ft.Column(controls=[titre_row] + lignes, spacing=8)

    def _carte_exhumation(self, e: dict) -> ft.Container:
        statut = e.get('statut', '')
        couleur_txt, couleur_bg = COULEURS_STATUTS_EXH.get(statut, (TEXT_SUB, 'rgba(148,163,184,0.15)'))

        actions = []
        if statut == 'SOUMISE' and session.est_admin():
            actions.append(self._btn_action(
                "Autoriser", ft.Icons.CHECK_CIRCLE, SUCCESS,
                lambda ev, eid=e['id']: self._autoriser_exhumation(eid)
            ))
            actions.append(self._btn_action(
                "Refuser", ft.Icons.CANCEL, ERROR_C,
                lambda ev, eid=e['id']: self._refuser_exhumation(eid)
            ))
        if statut == 'AUTORISEE' and session.est_staff():
            actions.append(self._btn_action(
                "Exécutée", ft.Icons.DONE_ALL, PURPLE,
                lambda ev, eid=e['id']: self._executer_exhumation(eid)
            ))

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
                                ft.Text(e.get('reference', ''), size=14,
                                        weight=ft.FontWeight.BOLD, color=PURPLE),
                                ft.Container(
                                    content=ft.Text(statut, size=11, color=couleur_txt),
                                    bgcolor=couleur_bg, border_radius=16,
                                    padding=ft.Padding(left=8, top=3, right=8, bottom=3),
                                ),
                            ], spacing=8),
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.PERSON, size=13, color=TEXT_SUB),
                                ft.Text(e.get('demandeur_nom', ''), size=12, color=TEXT_MAIN),
                                ft.Text("·", color=TEXT_SUB),
                                ft.Text(f"Concession {e.get('concession_ref','')}", size=12, color=TEXT_SUB),
                                ft.Text("·", color=TEXT_SUB),
                                ft.Text(f"Caveau {e.get('caveau_numero','')}", size=12, color=TEXT_MAIN),
                            ], spacing=6),
                            ft.Text(
                                f"Motif : {e.get('motif', '')[:80]}{'...' if len(e.get('motif','')) > 80 else ''}",
                                size=12, color=TEXT_SUB,
                            ),
                        ],
                        spacing=5, expand=True,
                    ),
                    ft.Row(controls=actions, spacing=8),
                ],
                spacing=0,
            ),
            bgcolor=CARD_BG, border_radius=14,
            border=ft.Border.all(1, CARD_BORDER),
            padding=ft.Padding(left=0, top=12, right=16, bottom=12),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=10,
                                color=ft.Colors.with_opacity(0.1, "#000000"),
                                offset=ft.Offset(0, 4)),
        )

    # ─── Formulaire nouvelle concession ──────────────────────────────────
    def _build_form_concession(self) -> ft.Column:
        try:
            reservations_validees = api.get("reservations/", params={"statut": "VALIDEE"}) or []
        except Exception:
            reservations_validees = []

        self.f_res = ft.Dropdown(
            label="Réservation validée",
            options=[
                ft.dropdown.Option(r['id'], f"{r['reference']} — {r['client_nom']} — Caveau {r['caveau_numero']}")
                for r in reservations_validees
            ],
            bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
            focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
            border_radius=12,
        )
        self.f_type = ft.Dropdown(
            label="Type de concession",
            options=[
                ft.dropdown.Option("TEMPORAIRE",   "Temporaire — 5 ans"),
                ft.dropdown.Option("RENOUVELABLE", "Renouvelable — 15 ans"),
                ft.dropdown.Option("PERPETUELLE",  "Perpétuelle"),
            ],
            value="TEMPORAIRE",
            bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
            focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
            border_radius=12,
        )
        self.f_debut  = self._champ("Date de début (AAAA-MM-JJ)")
        self.f_prix   = self._champ("Prix total (XAF)", keyboard_type=ft.KeyboardType.NUMBER)
        self.msg_form = ft.Container(visible=False)

        return ft.Column(
            controls=[
                ft.Text("Nouvelle Concession", size=16,
                        weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                self._carte(ft.Column(controls=[
                    self.f_res, self.f_type,
                    ft.Row(controls=[self.f_debut, self.f_prix], spacing=12),
                    self.msg_form,
                ], spacing=14)),
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Row(controls=[
                                ft.Icon(ft.Icons.SAVE, color="#ffffff", size=18),
                                ft.Text("Créer la concession", color="#ffffff",
                                        weight=ft.FontWeight.BOLD),
                            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                            width=240, height=48, bgcolor=ACCENT, border_radius=14,
                            on_click=self._creer_concession, ink=True,
                            shadow=ft.BoxShadow(spread_radius=0, blur_radius=12,
                                                color=ft.Colors.with_opacity(0.3, ACCENT),
                                                offset=ft.Offset(0, 6)),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=14,
        )

    def _creer_concession(self, e):
        if not self.f_res.value or not self.f_debut.value or not self.f_prix.value:
            self._show_msg(self.msg_form, "Tous les champs sont obligatoires.", ERROR_C, "rgba(248,113,113,0.1)")
            return
        try:
            api.post("concessions/", data={
                "reservation_id": self.f_res.value,
                "type_concession": self.f_type.value,
                "date_debut": self.f_debut.value,
                "prix_total": float(self.f_prix.value),
            })
            self._show_msg(self.msg_form, "✅ Concession créée avec succès !", SUCCESS, "rgba(52,211,153,0.1)")
            self._charger_donnees()
        except APIError as ex:
            self._show_msg(self.msg_form, str(ex), ERROR_C, "rgba(248,113,113,0.1)")

    # ─── Dialogues (renouvellement, exhumation) ──────────────────────────
    def _ouvrir_renouvellement(self, concession_id: str):
        f_type = ft.Dropdown(
            label="Nouveau type",
            options=[
                ft.dropdown.Option("TEMPORAIRE",   "Temporaire — 5 ans"),
                ft.dropdown.Option("RENOUVELABLE", "Renouvelable — 15 ans"),
                ft.dropdown.Option("PERPETUELLE",  "Perpétuelle"),
            ],
            value="RENOUVELABLE",
            bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
            focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
            border_radius=12,
        )
        f_prix = ft.TextField(
            label="Nouveau prix (XAF)", value="200000",
            bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
            focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
            keyboard_type=ft.KeyboardType.NUMBER, border_radius=12,
        )

        def confirmer(e):
            try:
                api.post(f"concessions/{concession_id}/renouveler/",
                         data={"nouveau_type": f_type.value, "prix": float(f_prix.value or 0)})
                self.page.close(dlg)
                self._charger_donnees()
                self._rafraichir_contenu()
            except APIError as ex:
                pass

        dlg = ft.AlertDialog(
            title=ft.Text("Renouveler la concession", color=TEXT_MAIN,
                          weight=ft.FontWeight.BOLD),
            bgcolor=CARD_BG,
            shape=ft.RoundedRectangleBorder(radius=16),
            content=ft.Column(controls=[f_type, f_prix], spacing=12, width=340),
            actions=[
                ft.TextButton(content=ft.Text("Annuler", color=TEXT_SUB),
                              on_click=lambda e: self.page.close(dlg)),
                ft.Container(
                    content=ft.Text("Renouveler", color="#ffffff", weight=ft.FontWeight.BOLD),
                    bgcolor=ACCENT, border_radius=14,
                    padding=ft.Padding(left=16, top=8, right=16, bottom=8),
                    on_click=confirmer, ink=True,
                ),
            ],
        )
        self.page.open(dlg)

    def _ouvrir_demande_exhumation(self, concession_id: str = None):
        options = []
        if not concession_id:
            for c in self.concessions:
                options.append(ft.dropdown.Option(c['id'], f"{c['reference']} — Caveau {c['caveau_numero']}"))

        f_con = ft.Dropdown(
            label="Concession",
            options=options,
            value=concession_id,
            bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
            focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
            border_radius=12,
        ) if not concession_id else ft.Container(visible=False)

        f_motif = ft.TextField(
            label="Motif de la demande",
            bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
            focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
            multiline=True, min_lines=3, border_radius=12,
        )
        f_date = ft.TextField(
            label="Date prévue (AAAA-MM-JJ, optionnel)",
            bgcolor=INPUT_BG, color=TEXT_MAIN, border_color=CARD_BORDER,
            focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
            border_radius=12,
        )
        msg = ft.Text("", color=ERROR_C, size=12)

        def soumettre(e):
            cid = concession_id or (f_con.value if hasattr(f_con, 'value') else None)
            if not cid or not f_motif.value:
                msg.value = "Concession et motif obligatoires."
                self.page.update()
                return
            try:
                api.post("concessions/exhumations/", data={
                    "concession_id": cid,
                    "motif": f_motif.value,
                    "date_execution_prevue": f_date.value or None,
                })
                self.page.close(dlg)
                self._charger_donnees()
                self._rafraichir_contenu()
            except APIError as ex:
                msg.value = str(ex)
                self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Demande d'Exhumation", color=TEXT_MAIN,
                          weight=ft.FontWeight.BOLD),
            bgcolor=CARD_BG,
            shape=ft.RoundedRectangleBorder(radius=16),
            content=ft.Column(controls=[f_con, f_motif, f_date, msg],
                              spacing=12, width=380),
            actions=[
                ft.TextButton(content=ft.Text("Annuler", color=TEXT_SUB),
                              on_click=lambda e: self.page.close(dlg)),
                ft.Container(
                    content=ft.Text("Soumettre", color="#ffffff", weight=ft.FontWeight.BOLD),
                    bgcolor=PURPLE, border_radius=14,
                    padding=ft.Padding(left=16, top=8, right=16, bottom=8),
                    on_click=soumettre, ink=True,
                ),
            ],
        )
        self.page.open(dlg)

    # ----- Actions admin (inchangées) -----
    def _autoriser_exhumation(self, exh_id: str):
        try:
            api.post(f"concessions/exhumations/{exh_id}/autoriser/", data={"notes_admin": ""})
            self._charger_donnees()
            self._rafraichir_contenu()
        except Exception:
            pass

    def _refuser_exhumation(self, exh_id: str):
        try:
            api.post(f"concessions/exhumations/{exh_id}/refuser/")
            self._charger_donnees()
            self._rafraichir_contenu()
        except Exception:
            pass

    def _executer_exhumation(self, exh_id: str):
        try:
            api.post(f"concessions/exhumations/{exh_id}/executer/")
            self._charger_donnees()
            self._rafraichir_contenu()
        except Exception:
            pass

    # ─── Helpers UI (mis à jour avec le thème sombre) ─────────────────────
    def _champ(self, label: str, **kwargs) -> ft.TextField:
        return ft.TextField(
            label=label, bgcolor=INPUT_BG, color=TEXT_MAIN,
            border_color=CARD_BORDER, focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=TEXT_SUB),
            border_radius=12,
            expand=True, **kwargs,
        )

    def _carte(self, content) -> ft.Container:
        return ft.Container(
            content=content,
            bgcolor=CARD_BG, border_radius=18,
            padding=ft.Padding(left=20, top=20, right=20, bottom=20),
            border=ft.Border.all(1, CARD_BORDER),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=15,
                                color=ft.Colors.with_opacity(0.1, "#000000"),
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

    def _btn_action(self, label: str, icon, couleur: str, handler) -> ft.Container:
        return ft.Container(
            content=ft.Row(controls=[
                ft.Icon(icon, color=couleur, size=14),
                ft.Text(label, color=couleur, size=12),
            ], spacing=4),
            border=ft.Border.all(1, couleur), border_radius=10,
            padding=ft.Padding(left=10, top=5, right=10, bottom=5),
            on_click=handler, ink=True,
        )

    def _show_msg(self, container: ft.Container, texte: str, couleur: str, bg: str):
        container.content = ft.Row(controls=[
            ft.Icon(ft.Icons.INFO_OUTLINE, color=couleur, size=15),
            ft.Text(texte, color=couleur, size=13),
        ], spacing=8)
        container.bgcolor = bg
        container.border_radius = 12
        container.padding = ft.Padding(left=12, top=10, right=12, bottom=10)
        container.visible = True
        self.page.update()

    def est_admin(self) -> bool:
        return session.role == 'ADMIN'