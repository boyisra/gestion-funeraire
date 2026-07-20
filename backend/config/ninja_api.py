"""
Router Ninja Principal — GI2 2026
Tous les routers API assemblés ici
"""
from ninja import NinjaAPI
from ninja.security import HttpBearer

from apps.auth_users.api import router as auth_router
from apps.terrain.api import router as terrain_router
from apps.reservations.api import router as reservation_router
from apps.paiements.api import router as paiement_router
from apps.concessions.api import router as concession_router
from apps.notifications.api import router as notification_router
from apps.documents.api import router as document_router
from apps.rapports.api import router as rapport_router

api = NinjaAPI(
    title="GI2 — API Gestion de Cimetière",
    description="API RESTful documentée — Application GI2 2026",
    version="1.0.0",
    docs_url="/docs",
)

api.add_router("/auth/",          auth_router)
api.add_router("/terrain/",       terrain_router)
api.add_router("/reservations/",  reservation_router)
api.add_router("/paiements/",     paiement_router)
api.add_router("/concessions/",   concession_router)
api.add_router("/notifications/", notification_router)
api.add_router("/documents/",     document_router)
api.add_router("/rapports/",      rapport_router)
