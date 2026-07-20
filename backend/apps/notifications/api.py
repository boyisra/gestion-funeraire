"""
API Notifications — Django Ninja — GI2 2026
"""
from typing import List, Optional
from ninja import Router, Schema
from django.shortcuts import get_object_or_404

from apps.auth_users.api import AuthBearer
from .models import Notification

router = Router(tags=["Notifications"])


class NotificationSchema(Schema):
    id: str
    type_notif: str
    sujet: str
    contenu: str
    envoyee: bool
    lue: bool
    date_envoi: Optional[str] = None
    cree_le: str


@router.get("/", response=List[NotificationSchema], auth=AuthBearer())
def mes_notifications(request, non_lues: bool = False):
    """Retourne les notifications de l'utilisateur connecté"""
    qs = Notification.objects.filter(destinataire=request.auth)
    if non_lues:
        qs = qs.filter(lue=False)
    return [_to_dict(n) for n in qs[:50]]


@router.post("/{notif_id}/lire/", auth=AuthBearer())
def marquer_lue(request, notif_id: str):
    notif = get_object_or_404(Notification, id=notif_id, destinataire=request.auth)
    notif.lue = True
    notif.save(update_fields=['lue'])
    return {"success": True}


@router.post("/lire-toutes/", auth=AuthBearer())
def marquer_toutes_lues(request):
    Notification.objects.filter(destinataire=request.auth, lue=False).update(lue=True)
    return {"success": True}


@router.get("/non-lues/count/", auth=AuthBearer())
def count_non_lues(request):
    count = Notification.objects.filter(destinataire=request.auth, lue=False).count()
    return {"count": count}


def _to_dict(n: Notification) -> dict:
    return {
        'id': str(n.id),
        'type_notif': n.type_notif,
        'sujet': n.sujet,
        'contenu': n.contenu,
        'envoyee': n.envoyee,
        'lue': n.lue,
        'date_envoi': n.date_envoi.strftime('%d/%m/%Y %H:%M') if n.date_envoi else None,
        'cree_le': n.cree_le.strftime('%d/%m/%Y %H:%M'),
    }
