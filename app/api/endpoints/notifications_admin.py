import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_admin, UserContext
from app.schemas.schemas import NotificationOut, NotificationCreate
from app.services.notification_service import NotificationService
from app.models.models import Notification

router = APIRouter(prefix="/admin/notifications", tags=["Admin Notifications"])

@router.post("/send", response_model=dict)
def send_notification(
    payload: NotificationCreate,
    admin: UserContext = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if payload.user_id:
        notif = NotificationService.create_notification(
            db, payload.user_id, payload.title, payload.body, 
            payload.category, payload.priority, payload.scheduled_for
        )
        if not notif:
            return {"message": "Notification suppressed by user preferences or user not found"}
        return {"message": "Notification sent to user", "id": str(notif.id)}
    else:
        count = NotificationService.dispatch_to_all(
            db, payload.title, payload.body, 
            payload.category, payload.priority, payload.scheduled_for
        )
        return {"message": f"Notifications dispatched to {count} users"}

@router.get("/", response_model=List[NotificationOut])
def list_all_notifications(
    admin: UserContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
    limit: int = 100
):
    return db.query(Notification).order_by(Notification.created_at.desc()).limit(limit).all()

@router.delete("/{notification_id}")
def delete_notification(
    notification_id: uuid.UUID,
    admin: UserContext = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(404, "Notification not found")
    db.delete(notif)
    db.commit()
    return {"message": "Notification deleted"}

@router.post("/cleanup")
def trigger_cleanup(
    user_id: uuid.UUID = Query(None),
    admin: UserContext = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    count = NotificationService.clear_notifications(db, user_id)
    return {"message": f"Cleared {count} notifications"}
