import uuid
import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.models import Notification, Profile, NotificationPreference, DeviceToken
from app.services.push_notification_service import push_service

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def create_notification(
        db: Session,
        user_id: uuid.UUID,
        title: str,
        body: str,
        category: str = "manual",
        priority: str = "medium",
        scheduled_for: Optional[datetime] = None,
        skip_push: bool = False
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
        
        # Trigger push notification if enabled and notification is sent immediately
        if notif.sent_at and not skip_push:
            try:
                result = push_service.send_push_to_user(
                    db=db,
                    user_id=user_id,
                    title=title,
                    body=body,
                    data={
                        "notification_id": str(notif.id),
                        "category": category,
                        "priority": priority
                    }
                )
                
                if result["success"] > 0:
                    notif.push_sent = True
                    logger.info(f"Push sent for notification {notif.id}: {result['success']} devices")
                elif result["failed"] > 0:
                    error_msg = f"Failed to send to {result['failed']} devices"
                    notif.push_error = error_msg
                    logger.warning(f"Push failed for notification {notif.id}: {error_msg}")
                    
            except Exception as e:
                notif.push_error = str(e)
                logger.error(f"Push notification error for {notif.id}: {e}")
                # Don't fail notification creation if push fails
            
            db.commit()
            db.refresh(notif)
        
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
        user_ids_to_push = []
        
        for user in users:
            res = NotificationService.create_notification(
                db, user.user_id, title, body, category, priority, scheduled_for,
                skip_push=True  # Skip individual push, we'll batch send instead
            )
            if res:
                count += 1
                user_ids_to_push.append(user.user_id)
        
        # Send batch push notification
        if user_ids_to_push and not scheduled_for:
            try:
                result = push_service.send_batch_push(
                    db=db,
                    user_ids=user_ids_to_push,
                    title=title,
                    body=body,
                    data={"category": category, "priority": priority}
                )
                logger.info(f"Batch push sent: {result['success']} success, {result['failed']} failed")
            except Exception as e:
                logger.error(f"Batch push notification error: {e}")
        
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
