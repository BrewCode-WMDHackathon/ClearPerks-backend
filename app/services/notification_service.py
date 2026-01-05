import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.models import Notification, Profile, NotificationPreference, DeviceToken

class NotificationService:
    @staticmethod
    def create_notification(
        db: Session,
        user_id: uuid.UUID,
        title: str,
        body: str,
        category: str = "manual",
        priority: str = "medium",
        scheduled_for: Optional[datetime] = None
    ) -> Notification:
        # Check if user exists
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        if not profile:
            return None

        # Check preferences unless HIGH priority
        if priority.lower() != "high":
            prefs = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
            if prefs:
                if prefs.all_disabled:
                    return None
                
                if category == "news" and prefs.news_frequency == "off":
                    return None
                if category == "social":
                    if prefs.social_updates == "no":
                        return None
                    if prefs.social_updates == "vimp-only" and priority.lower() != "high":
                        # Note: manual 'high' still counts here, but we already checked global 'high'
                        # This specific check is for category logic
                        return None
                if category == "gov" and not prefs.gov_notifications:
                    return None

        notif = Notification(
            user_id=user_id,
            title=title,
            body=body,
            category=category,
            priority=priority,
            scheduled_for=scheduled_for,
            sent_at=datetime.utcnow() if not scheduled_for else None
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        
        # In a real system, trigger FCM/Push here if sent_at is set
        return notif

    @staticmethod
    def dispatch_to_all(
        db: Session,
        title: str,
        body: str,
        category: str = "manual",
        priority: str = "medium",
        scheduled_for: Optional[datetime] = None
    ) -> int:
        users = db.query(Profile).all()
        count = 0
        for user in users:
            res = NotificationService.create_notification(
                db, user.user_id, title, body, category, priority, scheduled_for
            )
            if res:
                count += 1
        return count

    @staticmethod
    def clear_notifications(db: Session, user_id: Optional[uuid.UUID] = None):
        query = db.query(Notification).filter(Notification.is_cleared == 0)
        if user_id:
            query = query.filter(Notification.user_id == user_id)
        
        notifs = query.all()
        for n in notifs:
            n.is_cleared = 1
        db.commit()
        return len(notifs)
