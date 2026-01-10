"""
Device Management API Endpoints

Handles registration, deletion, and listing of user device tokens
for push notifications via Firebase Cloud Messaging (FCM).
"""

import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import DeviceToken
from app.schemas.schemas import UserContext, DeviceTokenIn

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post("/register", status_code=201)
def register_device_token(
    payload: DeviceTokenIn,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Register or update a device token for push notifications.
    
    - **token**: FCM device token from mobile app
    - **platform**: Device platform (ios, android, web)
    
    Returns a success message indicating token was registered or updated.
    """
    # Check if token already exists for this user
    existing = (
        db.query(DeviceToken)
        .filter(
            DeviceToken.user_id == current_user.user_id,
            DeviceToken.token == payload.token,
        )
        .first()
    )
    
    if existing:
        # Update existing token
        existing.platform = payload.platform
        existing.last_used_at = datetime.utcnow()
        db.commit()
        return {"message": "Device token updated", "device_id": str(existing.id)}
    
    # Create new token
    token = DeviceToken(
        user_id=current_user.user_id,
        token=payload.token,
        platform=payload.platform,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    
    return {"message": "Device token registered", "device_id": str(token.id)}


@router.delete("/{token}", status_code=204)
def unregister_device_token(
    token: str,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a device token (e.g., on logout).
    
    - **token**: The FCM device token to remove
    
    Returns 204 No Content on success, 404 if token not found.
    """
    device = (
        db.query(DeviceToken)
        .filter(
            DeviceToken.user_id == current_user.user_id,
            DeviceToken.token == token,
        )
        .first()
    )
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device token not found"
        )
    
    db.delete(device)
    db.commit()
    return None


@router.get("/", response_model=List[dict])
def list_user_devices(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all registered devices for the current user.
    
    Returns a list of devices with masked tokens (last 4 characters only)
    for security purposes.
    """
    devices = (
        db.query(DeviceToken)
        .filter(DeviceToken.user_id == current_user.user_id)
        .order_by(DeviceToken.last_used_at.desc())
        .all()
    )
    
    # Mask tokens for security (show only last 4 chars)
    result = []
    for device in devices:
        masked_token = "..." + device.token[-4:] if len(device.token) > 4 else "****"
        result.append({
            "id": str(device.id),
            "token": masked_token,
            "platform": device.platform,
            "created_at": device.created_at,
            "last_used_at": device.last_used_at,
        })
    
    return result
