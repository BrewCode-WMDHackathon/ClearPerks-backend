import uuid
from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Profile, NotificationPreference
from app.schemas.schemas import UserContext

def get_current_user(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_user_email: Optional[str] = Header(default=None, alias="X-User-Email"),
    db: Session = Depends(get_db),
) -> UserContext:
    """
    Hackathon-friendly auth:
    - Accepts X-User-Id header as UUID string.
    - Optionally X-User-Email.
    - Ensures a Profile exists for this user.

    Replace this with proper Supabase JWT verification in production.
    """
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-Id header required (stub auth).",
        )
    try:
        user_id = uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-User-Id UUID")

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        profile = Profile(user_id=user_id, email=x_user_email)
        db.add(profile)
        # initialize default notification prefs
        prefs = NotificationPreference(user=profile)
        db.add(prefs)
        db.commit()
        db.refresh(profile)

    return UserContext(user_id=profile.user_id, email=profile.email)
