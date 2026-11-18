"""
Router Notifications.
Acteur Secondaire : Service de notification (notifier l'atteinte de l'objectif).
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from database.repository import NotificationRepository

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


class MarkReadRequest(BaseModel):
    sportif_id: int


@router.get("")
def list_notifications(sportif_id: int = Query(...)):
    """Consulter les notifications envoyées au sportif."""
    return NotificationRepository.get_by_sportif(sportif_id)


@router.post("/read")
def mark_read(req: MarkReadRequest):
    """Marquer toutes les notifications comme lues."""
    NotificationRepository.mark_all_read(req.sportif_id)
    return {"message": "Notifications marquées comme lues"}
