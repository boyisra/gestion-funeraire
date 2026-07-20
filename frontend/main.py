"""
Point d'entrée — Application Flet GI2 2026
Gestion de Cimetière — Compatible Flet 0.85+
"""
import flet as ft
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from utils.config import session


def main(page: ft.Page):
    page.title = "GI2 2026 — Gestion de Cimetière"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 1280
    page.window.height = 800
    page.window.min_width = 900
    page.window.min_height = 600
    page.padding = 0
    page.bgcolor = "#f6f3ff"
    page.fonts = {}
    page.theme = ft.Theme(color_scheme_seed="#8b5cf6")

    def route_change(route):
        page.views.clear()

        if page.route in ("/", "/login"):
            from views.login_view import LoginView
            page.views.append(LoginView(page).build())

        elif page.route == "/mfa":
            from views.mfa_view import MFAView
            page.views.append(MFAView(page).build())

        elif page.route.startswith("/mfa/confirmer"):
            from views.mfa_link_view import MFALinkView
            page.views.append(MFALinkView(page).build())

        elif page.route == "/dashboard":
            if not session.est_connecte():
                page.go("/login")
                return
            from views.dashboard_view import DashboardView
            page.views.append(DashboardView(page).build())

        elif page.route == "/terrain":
            if not session.est_connecte():
                page.go("/login")
                return
            from views.terrain_view import TerrainView
            page.views.append(TerrainView(page).build())

        elif page.route == "/carte":
            if not session.est_connecte():
                page.go("/login")
                return
            from views.carte_view import CarteView
            page.views.append(CarteView(page).build())

        elif page.route == "/reservations":
            if not session.est_connecte():
                page.go("/login")
                return
            from views.reservation_view import ReservationView
            page.views.append(ReservationView(page).build())

        elif page.route == "/paiements":
            if not session.est_connecte():
                page.go("/login")
                return
            from views.paiement_view import PaiementView
            page.views.append(PaiementView(page).build())

        elif page.route == "/concessions":
            if not session.est_connecte():
                page.go("/login")
                return
            from views.concession_view import ConcessionView
            page.views.append(ConcessionView(page).build())


        elif page.route == "/notifications":
            if not session.est_connecte():
                page.go("/login")
                return
            from views.notification_view import NotificationView
            page.views.append(NotificationView(page).build())
        elif page.route == "/documents":
            if not session.est_connecte():
                page.go("/login")
                return
            from views.document_view import DocumentView
            page.views.append(DocumentView(page).build())

        elif page.route == "/rapports":
            if not session.est_connecte():
                page.go("/login")
                return
            from views.rapport_view import RapportView
            page.views.append(RapportView(page).build())

        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    def on_resize(e):
        # Recalcule la mise en page responsive des écrans d'authentification
        # (connexion / MFA) à chaque redimensionnement, pas seulement au chargement.
        if page.route in ("/", "/login", "/mfa"):
            route_change(e)

    page.on_resized = on_resize
    page.go("/login")


if __name__ == "__main__":
    ft.app(main, view=ft.AppView.WEB_BROWSER, port=8550)
