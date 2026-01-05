import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Profile, NotificationPreference, Notification, DeviceToken
from app.schemas.schemas import (
    UserContext, ProfileOut, ProfileUpdate,
    NotificationPreferencesOut, NotificationPreferencesUpdate,
    NotificationOut, DeviceTokenIn
)

router = APIRouter()

@router.get("/me", response_model=dict)
def get_me(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()
    prefs = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == current_user.user_id)
        .first()
    )
    return {
        "profile": ProfileOut.from_orm(profile),
        "notification_preferences": NotificationPreferencesOut.from_orm(prefs),
    }

@router.patch("/me", response_model=ProfileOut)
def update_me(
    payload: ProfileUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()
    if not profile:
        raise HTTPException(404, "Profile not found")

    if payload.full_name is not None:
        profile.full_name = payload.full_name
    if payload.timezone is not None:
        profile.timezone = payload.timezone
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile

@router.delete("/me", status_code=204)
def delete_me(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()
    if not profile:
        raise HTTPException(404, "Profile not found")
    db.delete(profile)
    db.commit()
    return None

@router.get("/notifications", response_model=List[NotificationOut])
def list_notifications(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notifications = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.user_id,
            Notification.is_cleared == 0
        )
        .order_by(Notification.created_at.desc())
        .all()
    )
    return notifications

@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.user_id,
        )
        .first()
    )
    if not notif:
        raise HTTPException(404, "Notification not found")
    notif.read_at = datetime.utcnow()
    db.commit()
    db.refresh(notif)
    return notif

@router.get("/notification-preferences", response_model=NotificationPreferencesOut)
def get_notification_preferences(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == current_user.user_id)
        .first()
    )
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs

@router.patch("/notification-preferences", response_model=NotificationPreferencesOut)
def update_notification_preferences(
    payload: NotificationPreferencesUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == current_user.user_id)
        .first()
    )
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.user_id)
        db.add(prefs)

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(prefs, field, value)

    prefs.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prefs)
    return prefs

@router.post("/notifications/device-token", status_code=201)
def save_device_token(
    payload: DeviceTokenIn,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(DeviceToken)
        .filter(
            DeviceToken.user_id == current_user.user_id,
            DeviceToken.token == payload.token,
        )
        .first()
    )
    if existing:
        existing.platform = payload.platform
        existing.last_used_at = datetime.utcnow()
        db.commit()
        return {"message": "Token updated"}

    token = DeviceToken(
        user_id=current_user.user_id,
        token=payload.token,
        platform=payload.platform,
    )
    db.add(token)
    db.commit()
    return {"message": "Token stored"}
