"""
Vue Paiements — GI2 2026
Interface Mobile Money, Airtel Money, Espèces, Virement
Compatible Flet 0.85+
"""
import flet as ft
import threading
import time
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api_client import api, APIError
from utils.config import session
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

# Couleurs des canaux
CANAUX_CONFIG = {
    'MOBILE_MONEY': {'couleur': '#f59e0b', 'icon': ft.Icons.PHONE_ANDROID,
                      'label': 'Mobile Money MTN', 'bg': '#fef3c7'},
    'AIRTEL_MONEY': {'couleur': '#ef4444', 'icon': ft.Icons.PHONE_ANDROID,
                      'label': 'Airtel Money', 'bg': '#ffe4e6'},
    'ESPECES':      {'couleur': '#10b981', 'icon': ft.Icons.PAYMENTS,
                      'label': 'Espèces', 'bg': '#d1fae5'},
    'VIREMENT':     {'couleur': '#8b5cf6', 'icon': ft.Icons.ACCOUNT_BALANCE,
                      'label': 'Virement bancaire', 'bg': '#ede9fe'},
}

COULEURS_STATUTS = {
    'EN_ATTENTE': ('#f59e0b', '#fef3c7'),
    'INITIE':     ('#8b5cf6', '#ede9fe'),
    'CONFIRME':   ('#10b981', '#d1fae5'),
    'ECHOUE':     ('#f43f5e', '#ffe4e6'),
    'REMBOURSE':  ('#726c94', '#efeaff'),
}


class PaiementView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.paiements = []
        self.onglet_actif = "nouveau" if not session.est_staff() else "liste"
        self.canal_selectionne = "MOBILE_MONEY"
        self.paiement_en_cours_id = None
        self._timer_verif = None

    def build(self) -> ft.View:
        self._charger_paiements()
        self.contenu = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        self._rafraichir_contenu()

        confirmes = sum(1 for p in self.paiements if p.get('statut') == 'CONFIRME')
        en_attente = sum(1 for p in self.paiements if p.get('statut') in ('EN_ATTENTE', 'INITIE'))
        total_xaf = sum(p.get('montant', 0) for p in self.paiements if p.get('statut') == 'CONFIRME')

        corps = ft.Column(
            controls=[
                build_topbar(
                    self.page, ft.Icons.WALLET_ROUNDED, "Paiements",
                    extra_controls=[
                        self._badge_stat("Confirmés", confirmes, SUCCESS),
                        self._badge_stat("En attente", en_attente, WARNING),
                        self._badge_stat(f"{int(total_xaf):,} XAF", 0, ACCENT, show_val=False),
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

        return ft.View(
            route="/paiements",
            bgcolor=BG_DARK,
            padding=0,
            controls=[
                ft.Row(
                    controls=[
                        build_sidebar(self.page, "/paiements"),
                        ft.Container(content=corps, expand=True, bgcolor=BG_DARK),
                    ],
                    expand=True, spacing=0,
                )
            ],
        )

    def _build_onglets(self) -> ft.Container:
        onglets = [("nouveau", ft.Icons.ADD_CIRCLE, "Nouveau paiement")]
        if session.est_staff():
            onglets = [
                ("liste",   ft.Icons.LIST_ALT,  "Historique"),
                ("stats",   ft.Icons.BAR_CHART, "Statistiques"),
                ("nouveau", ft.Icons.ADD_CIRCLE, "Nouveau"),
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
            bgcolor="#ffffff",
            border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
        )

    def _changer_onglet(self, key: str):
        self.onglet_actif = key
        self._rafraichir_contenu()

    def _charger_paiements(self):
        try:
            self.paiements = api.get("paiements/") or []
        except Exception:
            self.paiements = []

    def _rafraichir_contenu(self):
        self.contenu.controls.clear()
        if self.onglet_actif == "liste":
            self.contenu.controls.append(self._build_liste())
        elif self.onglet_actif == "stats":
            self.contenu.controls.append(self._build_stats())
        elif self.onglet_actif == "nouveau":
            self.contenu.controls.append(self._build_form_paiement())
        self.page.update()

    # ─── Formulaire nouveau paiement ──────────────────────────────────────
    def _build_form_paiement(self) -> ft.Column:
        # Charger les réservations validées non payées
        try:
            reservations = api.get("reservations/", params={"statut": "VALIDEE"}) or []
        except Exception:
            reservations = []

        self.f_reservation = ft.Dropdown(
            label="Réservation validée",
            options=[
                ft.dropdown.Option(
                    r['id'],
                    f"{r['reference']} — {r['client_nom']} — {int(r.get('montant_total',0)):,} XAF"
                )
                for r in reservations
            ],
            bgcolor=BG_INPUT, color=TEXT_MAIN, border_color=BORDER,
            focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
            on_change=self._on_reservation_change,
        )

        self.f_montant = ft.TextField(
            label="Montant (XAF)", value="150000",
            bgcolor=BG_INPUT, color=TEXT_MAIN, border_color=BORDER,
            focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
            keyboard_type=ft.KeyboardType.NUMBER, expand=True,
        )

        self.f_telephone = ft.TextField(
            label="Numéro Mobile Money / Airtel",
            hint_text="Ex: 06 123 45 67",
            bgcolor=BG_INPUT, color=TEXT_MAIN, border_color=BORDER,
            focused_border_color=ACCENT, label_style=ft.TextStyle(color=TEXT_SUB),
            keyboard_type=ft.KeyboardType.PHONE,
            prefix_icon=ft.Icons.PHONE, expand=True,
        )

        # Sélecteur de canal — boutons visuels
        self.canal_selectionne = "MOBILE_MONEY"
        self.boutons_canal = {}
        canal_row = ft.Row(spacing=10, wrap=True)

        for canal, cfg in CANAUX_CONFIG.items():
            btn = ft.Container(
                content=ft.Column(controls=[
                    ft.Icon(cfg['icon'], size=28, color=cfg['couleur']),
                    ft.Text(cfg['label'], size=12, color=TEXT_MAIN,
                            text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                width=150, height=80,
                bgcolor=cfg['bg'] if canal == "MOBILE_MONEY" else BG_CARD,
                border_radius=18,
                border=ft.Border.all(2, cfg['couleur'] if canal == "MOBILE_MONEY" else BORDER),
                padding=ft.Padding(left=12, top=12, right=12, bottom=12),
                alignment=ft.Alignment(x=0, y=0),
                on_click=lambda e, c=canal: self._selectionner_canal(c),
                ink=True,
            )
            self.boutons_canal[canal] = btn
            canal_row.controls.append(btn)

        # Zone numéro téléphone (visible seulement mobile money / airtel)
        self.zone_telephone = ft.Container(
            content=self.f_telephone,
            visible=True,
        )

        self.msg_paiement = ft.Container(visible=False)

        # Zone de suivi du paiement en cours
        self.zone_suivi = ft.Container(visible=False)

        return ft.Column(
            controls=[
                ft.Text("Initier un Paiement", size=16,
                        weight=ft.FontWeight.BOLD, color=TEXT_MAIN),

                # Réservation
                self._carte(ft.Column(controls=[
                    ft.Text("Réservation à payer", color=TEXT_SUB, size=13),
                    self.f_reservation,
                ], spacing=10)),

                # Canal de paiement
                ft.Text("Choisir le mode de paiement", size=14,
                        weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                canal_row,

                # Détails
                self._carte(ft.Column(controls=[
                    ft.Row(controls=[self.f_montant], spacing=12),
                    self.zone_telephone,
                ], spacing=12)),

                self.msg_paiement,
                self.zone_suivi,

                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Row(controls=[
                                ft.Icon(ft.Icons.SEND, color=BG_DARK, size=18),
                                ft.Text("Lancer le paiement", color=BG_DARK,
                                        weight=ft.FontWeight.BOLD),
                            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                            width=240, height=48, bgcolor=ACCENT, border_radius=18,
                            on_click=self._lancer_paiement, ink=True,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=12,
        )

    def _on_reservation_change(self, e):
        """Pré-remplit le montant depuis la réservation"""
        pass  # Le montant sera récupéré depuis la réservation

    def _selectionner_canal(self, canal: str):
        self.canal_selectionne = canal

        # Mettre à jour visuellement les boutons
        for c, btn in self.boutons_canal.items():
            cfg = CANAUX_CONFIG[c]
            if c == canal:
                btn.bgcolor = cfg['bg']
                btn.border = ft.Border.all(2, cfg['couleur'])
            else:
                btn.bgcolor = BG_CARD
                btn.border = ft.Border.all(1, BORDER)

        # Afficher/masquer le champ téléphone
        self.zone_telephone.visible = canal in ('MOBILE_MONEY', 'AIRTEL_MONEY')
        self.page.update()

    def _lancer_paiement(self, e):
        if not self.f_reservation.value:
            self._show_msg(self.msg_paiement, "Sélectionnez une réservation.", ERROR_C, "#ffe4e6")
            return
        if not self.f_montant.value:
            self._show_msg(self.msg_paiement, "Montant obligatoire.", ERROR_C, "#ffe4e6")
            return
        if self.canal_selectionne in ('MOBILE_MONEY', 'AIRTEL_MONEY') and not self.f_telephone.value:
            self._show_msg(self.msg_paiement, "Numéro de téléphone obligatoire.", ERROR_C, "#ffe4e6")
            return

        try:
            reponse = api.post("paiements/initier/", data={
                "reservation_id": self.f_reservation.value,
                "canal": self.canal_selectionne,
                "montant": float(self.f_montant.value),
                "numero_telephone": self.f_telephone.value or "",
            })

            if reponse and reponse.get('success'):
                self.paiement_en_cours_id = reponse.get('paiement_id')

                if self.canal_selectionne in ('MOBILE_MONEY', 'AIRTEL_MONEY'):
                    # Afficher la zone de suivi avec vérification automatique
                    self._afficher_suivi_mobile(reponse)
                else:
                    # Espèces / Virement — confirmé immédiatement
                    self._show_msg(
                        self.msg_paiement,
                        f"✅ {reponse.get('message', 'Paiement confirmé !')}  "
                        f"Réf: {reponse.get('reference', '')}",
                        SUCCESS, "#d1fae5",
                    )
                    self._charger_paiements()
            else:
                msg = reponse.get('message', 'Erreur lors du paiement.') if reponse else 'Erreur.'
                self._show_msg(self.msg_paiement, msg, ERROR_C, "#ffe4e6")

        except APIError as ex:
            self._show_msg(self.msg_paiement, str(ex), ERROR_C, "#ffe4e6")

    def _afficher_suivi_mobile(self, reponse: dict):
        """Affiche le panneau de suivi avec vérification automatique toutes les 5 sec"""
        canal_cfg = CANAUX_CONFIG.get(self.canal_selectionne, {})

        self.label_statut_suivi = ft.Text(
            "⏳ En attente de confirmation...",
            size=14, color=WARNING, weight=ft.FontWeight.BOLD,
        )
        self.label_timer = ft.Text("Vérification dans 5s...", size=12, color=TEXT_SUB)

        self.zone_suivi.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(controls=[
                        ft.Icon(canal_cfg.get('icon', ft.Icons.PHONE_ANDROID),
                                color=canal_cfg.get('couleur', ACCENT), size=28),
                        ft.Column(controls=[
                            ft.Text(reponse.get('message', ''), size=13, color=TEXT_MAIN),
                            ft.Text(f"Référence : {reponse.get('reference', '')}",
                                    size=12, color=TEXT_SUB),
                        ], spacing=2),
                    ], spacing=12),
                    ft.Divider(height=1, color=BORDER),
                    self.label_statut_suivi,
                    self.label_timer,
                    ft.Row(controls=[
                        ft.Container(
                            content=ft.Row(controls=[
                                ft.Icon(ft.Icons.REFRESH, color=BG_DARK, size=16),
                                ft.Text("Vérifier maintenant", color=BG_DARK, size=13,
                                        weight=ft.FontWeight.BOLD),
                            ], spacing=6),
                            bgcolor=ACCENT, border_radius=14,
                            padding=ft.Padding(left=14, top=8, right=14, bottom=8),
                            on_click=lambda e: self._verifier_paiement_maintenant(),
                            ink=True,
                        ),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                ],
                spacing=10,
            ),
            bgcolor="#ede9fe",
            border_radius=18,
            border=ft.Border.all(1, ACCENT),
            padding=ft.Padding(left=20, top=16, right=20, bottom=16),
        )
        self.zone_suivi.visible = True
        self.page.update()

        # Lancer la vérification automatique en arrière-plan
        self._lancer_verif_auto()

    def _lancer_verif_auto(self, compteur: int = 0):
        """Vérifie automatiquement toutes les 5 secondes pendant 2 minutes"""
        if compteur >= 24 or not self.paiement_en_cours_id:
            return

        def verifier():
            for i in range(5, 0, -1):
                if not self.paiement_en_cours_id:
                    return
                self.label_timer.value = f"Vérification dans {i}s..."
                self.page.update()
                time.sleep(1)

            self._verifier_paiement_maintenant()

            # Continuer si toujours en attente
            if self.paiement_en_cours_id:
                self._lancer_verif_auto(compteur + 1)

        t = threading.Thread(target=verifier, daemon=True)
        t.start()

    def _verifier_paiement_maintenant(self):
        if not self.paiement_en_cours_id:
            return
        try:
            reponse = api.post(f"paiements/{self.paiement_en_cours_id}/verifier/")
            statut = reponse.get('statut', '') if reponse else ''

            if statut == 'CONFIRME':
                self.label_statut_suivi.value = "✅ Paiement confirmé !"
                self.label_statut_suivi.color = SUCCESS
                self.label_timer.value = ""
                self.paiement_en_cours_id = None
                self._charger_paiements()
                self.page.update()

            elif statut == 'ECHOUE':
                self.label_statut_suivi.value = "❌ Paiement échoué. Réessayez."
                self.label_statut_suivi.color = ERROR_C
                self.label_timer.value = ""
                self.paiement_en_cours_id = None
                self.page.update()

            else:
                self.label_statut_suivi.value = "⏳ En attente de confirmation..."
                self.label_timer.value = "Vérification dans 5s..."
                self.page.update()

        except Exception:
            pass

    # ─── Liste des paiements ──────────────────────────────────────────────
    def _build_liste(self) -> ft.Column:
        if not self.paiements:
            return ft.Column(controls=[
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Icon(ft.Icons.RECEIPT_LONG, size=48, color=TEXT_SUB),
                        ft.Text("Aucun paiement", color=TEXT_SUB, size=14),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                    alignment=ft.Alignment(x=0, y=0), height=200,
                )
            ])

        return ft.Column(
            controls=[self._ligne_paiement(p) for p in self.paiements],
            spacing=8,
        )

    def _ligne_paiement(self, p: dict) -> ft.Container:
        statut = p.get('statut', '')
        couleur_txt, couleur_bg = COULEURS_STATUTS.get(statut, (TEXT_SUB, BG_INPUT))
        canal = p.get('canal', '')
        canal_cfg = CANAUX_CONFIG.get(canal, {'couleur': ACCENT, 'icon': ft.Icons.PAYMENTS, 'label': canal})

        actions = []
        if statut == 'INITIE':
            actions.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.Icons.REFRESH, color=ACCENT, size=14),
                        ft.Text("Vérifier", color=ACCENT, size=12),
                    ], spacing=4),
                    border=ft.Border.all(1, ACCENT), border_radius=10,
                    padding=ft.Padding(left=10, top=5, right=10, bottom=5),
                    on_click=lambda e, pid=p['id']: self._verifier_direct(pid),
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
                                ft.Text(p.get('reference', ''), size=14,
                                        weight=ft.FontWeight.BOLD, color=ACCENT),
                                ft.Container(
                                    content=ft.Text(statut, size=11, color=couleur_txt),
                                    bgcolor=couleur_bg, border_radius=16,
                                    padding=ft.Padding(left=8, top=3, right=8, bottom=3),
                                ),
                                ft.Container(
                                    content=ft.Row(controls=[
                                        ft.Icon(canal_cfg['icon'], size=12,
                                                color=canal_cfg['couleur']),
                                        ft.Text(canal_cfg['label'], size=11,
                                                color=canal_cfg['couleur']),
                                    ], spacing=4),
                                    bgcolor=canal_cfg.get('bg', BG_INPUT), border_radius=14,
                                    padding=ft.Padding(left=8, top=3, right=8, bottom=3),
                                ),
                            ], spacing=8),
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.PERSON, size=13, color=TEXT_SUB),
                                ft.Text(p.get('client_nom', ''), size=12, color=TEXT_MAIN),
                                ft.Text("·", color=BORDER),
                                ft.Text(
                                    f"{int(p.get('montant', 0)):,} XAF",
                                    size=14, color=SUCCESS, weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text("·", color=BORDER),
                                ft.Text(p.get('date_initiation', ''), size=11, color=TEXT_SUB),
                            ], spacing=6),
                            ft.Row(controls=[
                                ft.Text(f"Réservation : {p.get('reservation_ref', '')}",
                                        size=11, color=TEXT_SUB),
                            ]),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                    ft.Row(controls=actions, spacing=8),
                ],
                spacing=0,
            ),
            bgcolor=BG_CARD, border_radius=14,
            border=ft.Border.all(1, BORDER),
            padding=ft.Padding(left=0, top=12, right=16, bottom=12),
        )

    def _verifier_direct(self, paiement_id: str):
        try:
            reponse = api.post(f"paiements/{paiement_id}/verifier/")
            self._charger_paiements()
            self._rafraichir_contenu()
        except Exception:
            pass

    # ─── Statistiques ─────────────────────────────────────────────────────
    def _build_stats(self) -> ft.Column:
        try:
            stats = api.get("paiements/stats/") or {}
        except Exception:
            stats = {}

        par_canal = stats.get('par_canal', {})
        cartes_canal = []
        for canal, data in par_canal.items():
            cfg = CANAUX_CONFIG.get(canal, {'couleur': ACCENT, 'label': canal,
                                             'icon': ft.Icons.PAYMENTS})
            if data.get('count', 0) > 0:
                cartes_canal.append(
                    ft.Container(
                        content=ft.Column(controls=[
                            ft.Icon(cfg['icon'], color=cfg['couleur'], size=28),
                            ft.Text(cfg['label'], size=12, color=TEXT_SUB,
                                    text_align=ft.TextAlign.CENTER),
                            ft.Text(f"{int(data.get('total',0)):,} XAF", size=14,
                                    weight=ft.FontWeight.BOLD, color=cfg['couleur'],
                                    text_align=ft.TextAlign.CENTER),
                            ft.Text(f"{data.get('count',0)} transaction(s)", size=11,
                                    color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                        bgcolor=BG_CARD, border_radius=18,
                        border=ft.Border.all(1, cfg['couleur']),
                        padding=ft.Padding(left=16, top=16, right=16, bottom=16),
                        width=170,
                    )
                )

        return ft.Column(
            controls=[
                ft.Text("Statistiques Financières", size=16,
                        weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                ft.Row(controls=[
                    self._stat_card("Total revenus",
                                    f"{int(stats.get('total_revenus',0)):,} XAF",
                                    ft.Icons.ACCOUNT_BALANCE_WALLET, SUCCESS),
                    self._stat_card("Transactions",
                                    str(stats.get('total_transactions', 0)),
                                    ft.Icons.RECEIPT, ACCENT),
                    self._stat_card("En attente",
                                    str(stats.get('en_attente', 0)),
                                    ft.Icons.HOURGLASS_EMPTY, WARNING),
                    self._stat_card("Échoués",
                                    str(stats.get('echoues', 0)),
                                    ft.Icons.ERROR_OUTLINE, ERROR_C),
                ], spacing=12, wrap=True),
                ft.Text("Par canal de paiement", size=14,
                        weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                ft.Row(controls=cartes_canal, spacing=12, wrap=True)
                if cartes_canal else
                ft.Text("Aucune transaction confirmée", color=TEXT_SUB, size=13),
            ],
            spacing=14,
        )

    # ─── Helpers UI ───────────────────────────────────────────────────────
    def _carte(self, content) -> ft.Container:
        return ft.Container(
            content=content, bgcolor=BG_CARD, border_radius=18,
            padding=ft.Padding(left=20, top=20, right=20, bottom=20),
            border=ft.Border.all(1, BORDER),
        )

    def _badge_stat(self, label: str, valeur: int, couleur: str,
                    show_val: bool = True) -> ft.Container:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Text(str(valeur) if show_val else label,
                        size=18 if show_val else 14,
                        weight=ft.FontWeight.BOLD, color=couleur),
                ft.Text(label if show_val else "Revenus",
                        size=10, color=TEXT_SUB),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            bgcolor=BG_CARD, border_radius=14,
            padding=ft.Padding(left=14, top=6, right=14, bottom=6),
            border=ft.Border.all(1, BORDER),
        )

    def _stat_card(self, label: str, valeur: str, icon, couleur: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Icon(icon, color=couleur, size=28),
                ft.Text(valeur, size=20, weight=ft.FontWeight.BOLD, color=TEXT_MAIN,
                        text_align=ft.TextAlign.CENTER),
                ft.Text(label, size=12, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            bgcolor=BG_CARD, border_radius=18,
            border=ft.Border.all(1, couleur),
            padding=ft.Padding(left=16, top=16, right=16, bottom=16),
            width=180,
        )

    def _show_msg(self, container: ft.Container, texte: str, couleur: str, bg: str):
        container.content = ft.Row(controls=[
            ft.Icon(ft.Icons.INFO_OUTLINE, color=couleur, size=15),
            ft.Text(texte, color=couleur, size=13),
        ], spacing=8)
        container.bgcolor = bg
        container.border_radius = 8
        container.padding = ft.Padding(left=12, top=10, right=12, bottom=10)
        container.visible = True
        self.page.update()
