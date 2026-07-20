"""
Vue Documents PDF — GI2 2026
Interface de téléchargement des documents générés
Compatible Flet 0.85+
"""
import flet as ft
import webbrowser
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api_client import api, APIError
from utils.config import session, API_BASE_URL
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


class DocumentView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.reservations = []
        self.paiements    = []
        self.exhumations  = []

    def build(self) -> ft.View:
        self._charger_donnees()

        self.contenu = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self._construire_contenu()

        corps = ft.Column(
            controls=[
                build_topbar(
                    self.page, ft.Icons.FOLDER_COPY_ROUNDED, "Documents & PDFs",
                    on_refresh=lambda e: self._actualiser(),
                ),
                ft.Container(
                    content=self.contenu,
                    expand=True,
                    padding=ft.Padding(left=24, top=16, right=24, bottom=24),
                ),
            ],
            expand=True, spacing=0,
        )

        return ft.View(
            route="/documents",
            bgcolor=BG_DARK,
            padding=0,
            controls=[
                ft.Row(
                    controls=[
                        build_sidebar(self.page, "/documents"),
                        ft.Container(content=corps, expand=True, bgcolor=BG_DARK),
                    ],
                    expand=True, spacing=0,
                )
            ],
        )

    def _charger_donnees(self):
        try:
            self.reservations = api.get("reservations/", params={"statut": "VALIDEE"}) or []
        except Exception:
            self.reservations = []
        try:
            self.paiements = api.get("paiements/", params={"statut": "CONFIRME"}) or []
        except Exception:
            self.paiements = []
        try:
            self.exhumations = api.get("concessions/exhumations/") or []
        except Exception:
            self.exhumations = []

    def _actualiser(self):
        self._charger_donnees()
        self.contenu.controls.clear()
        self._construire_contenu()
        self.page.update()

    def _construire_contenu(self):
        self.contenu.controls = [

            # ── Factures ──────────────────────────────────────────────
            self._titre_section(
                ft.Icons.RECEIPT_LONG, "#f59e0b", "Factures",
                f"{len(self.paiements)} paiement(s) confirmé(s)"
            ),
            self._build_liste_factures(),

            ft.Divider(height=24, color=BORDER),

            # ── Certificats d'inhumation ──────────────────────────────
            self._titre_section(
                ft.Icons.VERIFIED, SUCCESS, "Certificats d'Inhumation",
                f"{len(self.reservations)} réservation(s) validée(s)"
            ),
            self._build_liste_certificats(),

            ft.Divider(height=24, color=BORDER),

            # ── Autorisations & PV d'exhumation ──────────────────────
            self._titre_section(
                ft.Icons.REMOVE_CIRCLE, PURPLE, "Documents d'Exhumation",
                f"{len(self.exhumations)} demande(s)"
            ),
            self._build_liste_exhumations(),
        ]

    # ─── Factures ─────────────────────────────────────────────────────────
    def _build_liste_factures(self) -> ft.Column:
        if not self.paiements:
            return self._vide("Aucun paiement confirmé")

        return ft.Column(
            controls=[self._carte_facture(p) for p in self.paiements],
            spacing=8,
        )

    def _carte_facture(self, p: dict) -> ft.Container:
        canaux = {
            'MOBILE_MONEY': ('MTN Mobile Money', '#f59e0b'),
            'AIRTEL_MONEY': ('Airtel Money', '#ef4444'),
            'ESPECES':      ('Espèces', '#10b981'),
            'VIREMENT':     ('Virement', '#8b5cf6'),
        }
        canal_label, canal_couleur = canaux.get(p.get('canal', ''), (p.get('canal', ''), ACCENT))

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=6, bgcolor="#f59e0b",
                        border_radius=ft.BorderRadius.only(top_left=8, bottom_left=8),
                    ),
                    ft.Column(
                        controls=[
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.RECEIPT_LONG, color="#f59e0b", size=18),
                                ft.Text(p.get('reference', ''), size=14,
                                        weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                                ft.Container(
                                    content=ft.Text(canal_label, size=11, color=canal_couleur),
                                    bgcolor=BG_INPUT, border_radius=14,
                                    padding=ft.Padding(left=8, top=3, right=8, bottom=3),
                                ),
                            ], spacing=8),
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.PERSON, size=13, color=TEXT_SUB),
                                ft.Text(p.get('client_nom', ''), size=12, color=TEXT_MAIN),
                                ft.Text("·", color=BORDER),
                                ft.Text(
                                    f"{int(p.get('montant', 0)):,} XAF",
                                    size=13, color=SUCCESS, weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text("·", color=BORDER),
                                ft.Text(p.get('date_confirmation', p.get('date_initiation', '')),
                                        size=11, color=TEXT_SUB),
                            ], spacing=6),
                        ],
                        spacing=5, expand=True,
                    ),
                    self._btn_telecharger(
                        "Facture PDF",
                        ft.Icons.DOWNLOAD,
                        "#f59e0b",
                        lambda e, pid=p['id']: self._ouvrir_pdf(f"documents/facture/{pid}/"),
                    ),
                ],
                spacing=0,
            ),
            bgcolor=BG_CARD, border_radius=14,
            border=ft.Border.all(1, BORDER),
            padding=ft.Padding(left=0, top=12, right=16, bottom=12),
        )

    # ─── Certificats ──────────────────────────────────────────────────────
    def _build_liste_certificats(self) -> ft.Column:
        if not self.reservations:
            return self._vide("Aucune réservation validée")

        return ft.Column(
            controls=[self._carte_certificat(r) for r in self.reservations],
            spacing=8,
        )

    def _carte_certificat(self, r: dict) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=6, bgcolor=SUCCESS,
                        border_radius=ft.BorderRadius.only(top_left=8, bottom_left=8),
                    ),
                    ft.Column(
                        controls=[
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.VERIFIED, color=SUCCESS, size=18),
                                ft.Text(r.get('reference', ''), size=14,
                                        weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                                ft.Container(
                                    content=ft.Text("VALIDÉE", size=11, color=SUCCESS),
                                    bgcolor="#d1fae5", border_radius=16,
                                    padding=ft.Padding(left=8, top=3, right=8, bottom=3),
                                ),
                            ], spacing=8),
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.PERSON_OUTLINE, size=13, color=TEXT_SUB),
                                ft.Text(
                                    f"Défunt : {r.get('defunt_prenom','')} {r.get('defunt_nom','')}",
                                    size=12, color=TEXT_MAIN,
                                ),
                                ft.Text("·", color=BORDER),
                                ft.Text(f"Caveau {r.get('caveau_numero','')}", size=12, color=TEXT_SUB),
                                ft.Text("·", color=BORDER),
                                ft.Text(f"Inhumation : {r.get('date_inhumation','')}", size=11, color=TEXT_SUB),
                            ], spacing=6),
                        ],
                        spacing=5, expand=True,
                    ),
                    self._btn_telecharger(
                        "Certificat PDF",
                        ft.Icons.DOWNLOAD,
                        SUCCESS,
                        lambda e, rid=r['id']: self._ouvrir_pdf(f"documents/certificat/{rid}/"),
                    ),
                ],
                spacing=0,
            ),
            bgcolor=BG_CARD, border_radius=14,
            border=ft.Border.all(1, BORDER),
            padding=ft.Padding(left=0, top=12, right=16, bottom=12),
        )

    # ─── Documents exhumation ─────────────────────────────────────────────
    def _build_liste_exhumations(self) -> ft.Column:
        exh_avec_docs = [
            e for e in self.exhumations
            if e.get('statut') in ('AUTORISEE', 'EXECUTEE')
        ]

        if not exh_avec_docs:
            return self._vide("Aucune exhumation autorisée")

        return ft.Column(
            controls=[self._carte_exhumation_doc(e) for e in exh_avec_docs],
            spacing=8,
        )

    def _carte_exhumation_doc(self, e: dict) -> ft.Container:
        statut = e.get('statut', '')
        executee = statut == 'EXECUTEE'

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=6, bgcolor=PURPLE,
                        border_radius=ft.BorderRadius.only(top_left=8, bottom_left=8),
                    ),
                    ft.Column(
                        controls=[
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.REMOVE_CIRCLE, color=PURPLE, size=18),
                                ft.Text(e.get('reference', ''), size=14,
                                        weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                                ft.Container(
                                    content=ft.Text(statut, size=11, color=PURPLE),
                                    bgcolor="#1e1b4b", border_radius=16,
                                    padding=ft.Padding(left=8, top=3, right=8, bottom=3),
                                ),
                            ], spacing=8),
                            ft.Row(controls=[
                                ft.Icon(ft.Icons.PERSON, size=13, color=TEXT_SUB),
                                ft.Text(e.get('demandeur_nom', ''), size=12, color=TEXT_MAIN),
                                ft.Text("·", color=BORDER),
                                ft.Text(f"Concession {e.get('concession_ref', '')}", size=12, color=TEXT_SUB),
                                ft.Text("·", color=BORDER),
                                ft.Text(f"Caveau {e.get('caveau_numero', '')}", size=12, color=TEXT_SUB),
                            ], spacing=6),
                        ],
                        spacing=5, expand=True,
                    ),
                    ft.Row(controls=[
                        self._btn_telecharger(
                            "Autorisation",
                            ft.Icons.DOWNLOAD,
                            PURPLE,
                            lambda e2, eid=e['id']: self._ouvrir_pdf(
                                f"documents/autorisation-exhumation/{eid}/"
                            ),
                        ),
                        self._btn_telecharger(
                            "PV",
                            ft.Icons.DOWNLOAD,
                            TEXT_SUB if not executee else WARNING,
                            lambda e2, eid=e['id']: self._ouvrir_pdf(
                                f"documents/pv-exhumation/{eid}/"
                            ),
                        ) if executee else ft.Container(visible=False),
                    ], spacing=8),
                ],
                spacing=0,
            ),
            bgcolor=BG_CARD, border_radius=14,
            border=ft.Border.all(1, BORDER),
            padding=ft.Padding(left=0, top=12, right=16, bottom=12),
        )

    # ─── Helpers UI ───────────────────────────────────────────────────────
    def _ouvrir_pdf(self, endpoint: str):
        """Ouvre le PDF dans le navigateur via l'API backend"""
        token = session.token_acces or ""
        url = f"{API_BASE_URL}/{endpoint}?token={token}"
        webbrowser.open(url)

        self.page.snack_bar = ft.SnackBar(
            content=ft.Text("📄 Ouverture du PDF dans le navigateur...", color=TEXT_MAIN),
            bgcolor=BG_CARD,
        )
        self.page.snack_bar.open = True
        self.page.update()

    def _btn_telecharger(self, label: str, icon, couleur: str, handler) -> ft.Container:
        return ft.Container(
            content=ft.Row(controls=[
                ft.Icon(icon, color=couleur, size=14),
                ft.Text(label, color=couleur, size=12, weight=ft.FontWeight.BOLD),
            ], spacing=6),
            border=ft.Border.all(1, couleur), border_radius=14,
            padding=ft.Padding(left=12, top=6, right=12, bottom=6),
            on_click=handler, ink=True,
        )

    def _titre_section(self, icon, couleur: str, titre: str, sous_titre: str) -> ft.Row:
        return ft.Row(
            controls=[
                ft.Icon(icon, color=couleur, size=22),
                ft.Column(controls=[
                    ft.Text(titre, size=15, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ft.Text(sous_titre, size=12, color=TEXT_SUB),
                ], spacing=2),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _vide(self, message: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Icon(ft.Icons.PICTURE_AS_PDF, size=40, color=TEXT_SUB),
                ft.Text(message, color=TEXT_SUB, size=13),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            alignment=ft.Alignment(x=0, y=0),
            height=120,
        )
