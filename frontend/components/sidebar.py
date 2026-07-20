"""
Sidebar de navigation partagée — GI2 2026 (nouveau design)
Menu latéral fixe, dégradé violet/rose, utilisé par toutes les vues
authentifiées à la place de l'ancienne barre du haut (AppBar).
Compatible Flet 0.85+
"""
import flet as ft
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.config import session

# ─── Palette partagée (même thème que les vues) ───────────────────────────
PAGE_BG      = "#f6f3ff"
CARD         = "#ffffff"
ACCENT       = "#8b5cf6"
ACCENT_2     = "#ec4899"
TEXT_MAIN    = "#241f3d"
TEXT_SUB     = "#726c94"
BORDER       = "#e6ddff"
ERROR_C      = "#f43f5e"

SIDEBAR_GRAD_TOP    = "#3b0764"
SIDEBAR_GRAD_BOTTOM = "#7c3aed"
SIDEBAR_ITEM_ACTIVE = "#ffffff"
SIDEBAR_TEXT        = "#d9c9ff"
SIDEBAR_TEXT_ACTIVE = "#4c1d95"

MENU_ITEMS = [
    ("/dashboard",     ft.Icons.SPACE_DASHBOARD_ROUNDED, "Tableau de bord"),
    ("/terrain",       ft.Icons.TERRAIN_ROUNDED,          "Terrain & Zones"),
    ("/carte",         ft.Icons.TRAVEL_EXPLORE_ROUNDED,   "Carte Interactive"),
    ("/reservations",  ft.Icons.EVENT_AVAILABLE_ROUNDED,  "Réservations"),
    ("/paiements",     ft.Icons.WALLET_ROUNDED,           "Paiements"),
    ("/concessions",   ft.Icons.ARTICLE_ROUNDED,          "Concessions"),
    ("/documents",     ft.Icons.FOLDER_COPY_ROUNDED,      "Documents PDF"),
    ("/notifications", ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED, "Notifications"),
    ("/rapports",      ft.Icons.INSIGHTS_ROUNDED,         "Rapports"),
]

ROLES_CLIENT_ROUTES = ('/dashboard', '/reservations', '/paiements', '/documents', '/notifications')


def build_sidebar(page: ft.Page, active_route: str, notif_count: int = 0) -> ft.Container:
    """Construit le menu latéral fixe, dégradé, avec l'item actif surligné."""

    menus = MENU_ITEMS
    if session.role == 'CLIENT':
        menus = [m for m in menus if m[0] in ROLES_CLIENT_ROUTES]

    items = []
    for route, icon, label in menus:
        actif = active_route == route
        badge = None
        if route == "/notifications" and notif_count > 0:
            badge = ft.Container(
                content=ft.Text(str(notif_count), size=9, color="#ffffff", weight=ft.FontWeight.BOLD),
                bgcolor=ACCENT_2, border_radius=20,
                padding=ft.Padding(left=6, top=1, right=6, bottom=1),
            )
        row_controls = [
            ft.Icon(icon, size=19, color=SIDEBAR_TEXT_ACTIVE if actif else SIDEBAR_TEXT),
            ft.Text(
                label, size=13, expand=True,
                color=SIDEBAR_TEXT_ACTIVE if actif else SIDEBAR_TEXT,
                weight=ft.FontWeight.W_600 if actif else ft.FontWeight.W_400,
            ),
        ]
        if badge:
            row_controls.append(badge)

        items.append(
            ft.Container(
                content=ft.Row(controls=row_controls, spacing=12),
                bgcolor=SIDEBAR_ITEM_ACTIVE if actif else "transparent",
                border_radius=14,
                padding=ft.Padding(left=14, top=11, right=12, bottom=11),
                on_click=(lambda e, r=route: page.go(r)) if not actif else None,
                ink=not actif,
                animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            )
        )

    entete = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text("⚰", size=20),
                    bgcolor=ft.Colors.with_opacity(0.18, "#ffffff"),
                    border_radius=12,
                    padding=ft.Padding(left=10, top=8, right=10, bottom=8),
                ),
                ft.Column(
                    controls=[
                        ft.Text("GI2 · 2026", size=15, weight=ft.FontWeight.BOLD, color="#ffffff"),
                        ft.Text("Gestion Cimetière", size=10, color=SIDEBAR_TEXT),
                    ],
                    spacing=0,
                ),
            ],
            spacing=10,
        ),
        padding=ft.Padding(left=18, top=22, right=18, bottom=22),
    )

    pied = ft.Container(
        content=ft.Column(
            controls=[
                ft.Divider(height=1, color=ft.Colors.with_opacity(0.15, "#ffffff")),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Text(
                                    (session.nom_complet or "?")[:1].upper(),
                                    size=14, weight=ft.FontWeight.BOLD, color=SIDEBAR_TEXT_ACTIVE,
                                ),
                                width=34, height=34, bgcolor="#ffffff", border_radius=17,
                                alignment=ft.Alignment(x=0, y=0),
                            ),
                            ft.Column(
                                controls=[
                                    ft.Text(session.nom_complet or "Utilisateur", size=12,
                                            color="#ffffff", weight=ft.FontWeight.W_600,
                                            overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(session.role or "", size=10, color=SIDEBAR_TEXT),
                                ],
                                spacing=0, expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.LOGOUT_ROUNDED, icon_color=SIDEBAR_TEXT, icon_size=18,
                                tooltip="Déconnexion",
                                on_click=lambda e: _deconnecter(page),
                            ),
                        ],
                        spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding(left=6, top=10, right=2, bottom=4),
                ),
            ],
            spacing=8,
        ),
        padding=ft.Padding(left=14, top=0, right=14, bottom=18),
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                entete,
                ft.Container(
                    content=ft.Column(controls=items, spacing=4),
                    padding=ft.Padding(left=10, top=0, right=10, bottom=0),
                    expand=True,
                ),
                pied,
            ],
            spacing=0,
        ),
        width=232,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(x=-1, y=-1),
            end=ft.Alignment(x=1, y=1),
            colors=[SIDEBAR_GRAD_TOP, SIDEBAR_GRAD_BOTTOM],
        ),
    )


def build_topbar(page: ft.Page, icon, titre: str, on_refresh=None, extra_controls=None) -> ft.Container:
    """Barre supérieure légère (titre de la page + actions), utilisée dans
    chaque vue à la place de l'ancien bandeau sombre avec flèche retour."""
    droite = list(extra_controls or [])
    if on_refresh:
        droite.append(
            ft.IconButton(
                icon=ft.Icons.REFRESH_ROUNDED, icon_color=TEXT_SUB,
                tooltip="Actualiser", on_click=on_refresh,
            )
        )
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Icon(icon, color=ACCENT, size=20),
                            bgcolor="#f1ecff", border_radius=12,
                            padding=ft.Padding(left=9, top=9, right=9, bottom=9),
                        ),
                        ft.Text(titre, size=19, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ],
                    spacing=12,
                ),
                ft.Row(controls=droite, spacing=6),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        bgcolor=CARD,
        padding=ft.Padding(left=24, top=16, right=20, bottom=16),
        border=ft.Border(bottom=ft.BorderSide(1, BORDER)),
    )


def build_shell(page: ft.Page, active_route: str, body: ft.Control) -> ft.Row:
    """Assemble la sidebar + le corps de page (topbar + contenu) déjà construit."""
    return ft.Row(
        controls=[
            build_sidebar(page, active_route),
            ft.Container(content=body, expand=True, bgcolor=PAGE_BG),
        ],
        expand=True,
        spacing=0,
    )


def _deconnecter(page: ft.Page):
    session.deconnecter()
    page.go("/login")
