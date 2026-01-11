"""
Push Notification Service using Firebase Cloud Messaging (FCM)

This service handles all push notification operations including:
- FCM client initialization
- Sending push notifications to individual users
- Batch sending to multiple users
- Token validation and cleanup
- Error handling and logging
"""

import os
import json
import logging
from typing import List, Dict, Optional
import uuid
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Firebase Admin SDK imports (will be installed)
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("Firebase Admin SDK not installed. Push notifications disabled.")


class PushNotificationService:
    """Service for handling FCM push notifications"""
    
    _fcm_app = None
    _initialized = False
    
    @classmethod
    def initialize_fcm(cls) -> bool:
        """
        Initialize Firebase Cloud Messaging client.
        
        Supports two methods for credentials:
        1. FIREBASE_CREDENTIALS_JSON env var (JSON string) - for HuggingFace/cloud
        2. FIREBASE_CREDENTIALS_PATH env var (file path) - for local development
        
        Returns True if successful, False otherwise.
        """
        if cls._initialized:
            return True
            
        if not FIREBASE_AVAILABLE:
            logger.warning("Firebase SDK not available")
            return False
        
        # Check if FCM is enabled via environment variable
        fcm_enabled = os.getenv("FIREBASE_ENABLED", "true").lower() == "true"
        if not fcm_enabled:
            logger.info("Firebase push notifications disabled via FIREBASE_ENABLED env var")
            return False
        
        try:
            cred = None
            
            # Method 1: Try FIREBASE_CREDENTIALS_JSON env var (for HuggingFace Secrets)
            cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
            if cred_json:
                try:
                    cred_dict = json.loads(cred_json)
                    cred = credentials.Certificate(cred_dict)
                    logger.info("Using Firebase credentials from FIREBASE_CREDENTIALS_JSON env var")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in FIREBASE_CREDENTIALS_JSON: {e}")
                    return False
            
            # Method 2: Try FIREBASE_CREDENTIALS_PATH file (for local development)
            if cred is None:
                cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-credentials.json")
                
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    logger.info(f"Using Firebase credentials from file: {cred_path}")
                else:
                    logger.error(f"Firebase credentials not found. Set FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_PATH")
                    return False
            
            # Initialize Firebase Admin SDK
            cls._fcm_app = firebase_admin.initialize_app(cred)
            cls._initialized = True
            
            logger.info("Firebase Cloud Messaging initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            return False
    
    @classmethod
    def is_enabled(cls) -> bool:
        """Check if push notifications are enabled and initialized"""
        if not cls._initialized:
            cls.initialize_fcm()
        return cls._initialized
    
    @classmethod
    def send_push_to_user(
        cls,
        db: Session,
        user_id: uuid.UUID,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, any]:
        """
        Send push notification to all devices of a specific user.
        
        Args:
            db: Database session
            user_id: User's UUID
            title: Notification title
            body: Notification body
            data: Optional data payload (key-value pairs)
        
        Returns:
            Dict with success count, failure count, and errors
        """
        if not cls.is_enabled():
            logger.debug("Push notifications disabled, skipping send")
            return {"success": 0, "failed": 0, "errors": []}
        
        from app.models.models import DeviceToken
        
        # Get all device tokens for user
        tokens = db.query(DeviceToken).filter(DeviceToken.user_id == user_id).all()
        
        if not tokens:
            logger.debug(f"No device tokens found for user {user_id}")
            return {"success": 0, "failed": 0, "errors": []}
        
        token_strings = [t.token for t in tokens]
        
        # Send to all user's devices
        result = cls._send_multicast(token_strings, title, body, data)
        
        # Clean up invalid tokens
        if result["invalid_tokens"]:
            cls._remove_invalid_tokens(db, result["invalid_tokens"])
        
        return {
            "success": result["success_count"],
            "failed": result["failure_count"],
            "errors": result["errors"]
        }
    
    @classmethod
    def send_batch_push(
        cls,
        db: Session,
        user_ids: List[uuid.UUID],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, any]:
        """
        Send push notification to multiple users efficiently.
        
        Args:
            db: Database session
            user_ids: List of user UUIDs
            title: Notification title
            body: Notification body
            data: Optional data payload
        
        Returns:
            Dict with success count, failure count, and errors
        """
        if not cls.is_enabled():
            logger.debug("Push notifications disabled, skipping batch send")
            return {"success": 0, "failed": 0, "errors": []}
        
        from app.models.models import DeviceToken
        
        # Get all device tokens for all users
        tokens = db.query(DeviceToken).filter(DeviceToken.user_id.in_(user_ids)).all()
        
        if not tokens:
            logger.debug(f"No device tokens found for {len(user_ids)} users")
            return {"success": 0, "failed": 0, "errors": []}
        
        token_strings = [t.token for t in tokens]
        
        # FCM supports up to 500 tokens per batch
        # Split into chunks if needed
        batch_size = 500
        total_success = 0
        total_failed = 0
        all_errors = []
        all_invalid_tokens = []
        
        for i in range(0, len(token_strings), batch_size):
            batch_tokens = token_strings[i:i + batch_size]
            result = cls._send_multicast(batch_tokens, title, body, data)
            
            total_success += result["success_count"]
            total_failed += result["failure_count"]
            all_errors.extend(result["errors"])
            all_invalid_tokens.extend(result["invalid_tokens"])
        
        # Clean up invalid tokens
        if all_invalid_tokens:
            cls._remove_invalid_tokens(db, all_invalid_tokens)
        
        logger.info(f"Batch push sent to {len(user_ids)} users: {total_success} success, {total_failed} failed")
        
        return {
            "success": total_success,
            "failed": total_failed,
            "errors": all_errors
        }
    
    @classmethod
    def _send_multicast(
        cls,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, any]:
        """
        Internal method to send multicast message via FCM.
        
        Returns:
            Dict with success_count, failure_count, errors, and invalid_tokens
        """
        if not tokens:
            return {
                "success_count": 0,
                "failure_count": 0,
                "errors": [],
                "invalid_tokens": []
            }
        
        try:
            # Prepare message
            message_data = data or {}
            
            # Ensure all data values are strings
            message_data = {k: str(v) for k, v in message_data.items()}
            
            # Create multicast message
            multicast_message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=message_data,
                tokens=tokens
            )
            
            # Send message
            response = messaging.send_multicast(multicast_message)
            
            # Collect invalid tokens
            invalid_tokens = []
            errors = []
            
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    error_code = resp.exception.code if resp.exception else "unknown"
                    
                    # Invalid or unregistered tokens
                    if error_code in ["invalid-argument", "registration-token-not-registered"]:
                        invalid_tokens.append(tokens[idx])
                    
                    errors.append({
                        "token_index": idx,
                        "error": str(resp.exception) if resp.exception else "unknown error"
                    })
            
            logger.info(f"Multicast push: {response.success_count} success, {response.failure_count} failed")
            
            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "errors": errors,
                "invalid_tokens": invalid_tokens
            }
            
        except Exception as e:
            logger.error(f"Failed to send multicast push: {e}")
            return {
                "success_count": 0,
                "failure_count": len(tokens),
                "errors": [{"error": str(e)}],
                "invalid_tokens": []
            }
    
    @classmethod
    def _remove_invalid_tokens(cls, db: Session, invalid_tokens: List[str]):
        """
        Remove invalid/expired device tokens from database.
        
        Args:
            db: Database session
            invalid_tokens: List of invalid token strings
        """
        if not invalid_tokens:
            return
        
        from app.models.models import DeviceToken
        
        try:
            deleted = db.query(DeviceToken).filter(
                DeviceToken.token.in_(invalid_tokens)
            ).delete(synchronize_session=False)
            
            db.commit()
            logger.info(f"Removed {deleted} invalid device tokens")
            
        except Exception as e:
            logger.error(f"Failed to remove invalid tokens: {e}")
            db.rollback()


# Initialize FCM on module import
push_service = PushNotificationService()
