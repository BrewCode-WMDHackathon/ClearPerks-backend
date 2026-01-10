import sys
import os
import uuid
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.main import app
from app.core.database import SessionLocal
from app.models.models import Profile, NotificationPreference

def ensure_schema(db: Session):
    try:
        # profiles
        db.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;"))
        
        # notification_preferences
        db.execute(text("ALTER TABLE notification_preferences ADD COLUMN IF NOT EXISTS news_frequency TEXT DEFAULT 'daily';"))
        db.execute(text("ALTER TABLE notification_preferences ADD COLUMN IF NOT EXISTS social_updates TEXT DEFAULT 'yes';"))
        db.execute(text("ALTER TABLE notification_preferences ADD COLUMN IF NOT EXISTS gov_notifications BOOLEAN DEFAULT TRUE;"))
        db.execute(text("ALTER TABLE notification_preferences ADD COLUMN IF NOT EXISTS all_disabled BOOLEAN DEFAULT FALSE;"))
        
        # notifications
        db.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS category TEXT;"))
        db.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS priority TEXT DEFAULT 'medium';"))
        db.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS is_cleared INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMP WITH TIME ZONE;"))
        db.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS sent_at TIMESTAMP WITH TIME ZONE;"))
        db.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS read_at TIMESTAMP WITH TIME ZONE;"))
        
        db.commit()
    except Exception as e:
        print(f"Schema patch warning: {e}")
        db.rollback()

def setup_users(db: Session):
    ensure_schema(db)
    
    print("--- Fetching Existing Users ---")
    profiles = db.query(Profile).all()
    if not profiles:
        raise Exception("No profiles found in DB. Please sign up/login via frontend first to create a user.")
        
    admin_id = profiles[0].user_id
    # Set first user as admin
    profiles[0].is_admin = True
    db.commit()
    print(f"Promoted {profiles[0].email or profiles[0].user_id} to Admin.")
    
    user_id = profiles[0].user_id
    if len(profiles) > 1:
        user_id = profiles[1].user_id
        
    # Ensure prefs exist
    for pid in [admin_id, user_id]:
        if not db.query(NotificationPreference).filter_by(user_id=pid).first():
            db.add(NotificationPreference(user_id=pid))
    db.commit()
    
    return admin_id, user_id

def test_notification_flow():
    client = TestClient(app)
    db = SessionLocal()
    
    print("--- Setting up Test Users ---")
    try:
        admin_id, user_id = setup_users(db)
        print(f"Admin ID: {admin_id}")
        print(f"User ID:  {user_id}")
    except Exception as e:
        print(f"Setup failed (users might already exist): {e}")
        return
    finally:
        db.close()
        
    print("\n--- Step 1: Admin sends notification ---")
    payload = {
        "user_id": str(user_id),
        "title": "Hello from Test Script",
        "body": "This is a test notification",
        "category": "manual",
        "priority": "high"
    }
    
    headers = {
        "X-User-Id": str(admin_id),
        "X-User-Email": "admin@example.com"
    }
    
    response = client.post("/api/v1/admin/notifications/send", json=payload, headers=headers)
    
    if response.status_code == 200:
        print("PASS: Notification Sent Successfully")
        print("Response:", response.json())
    else:
        print("FAIL: Failed to send notification")
        print(response.status_code, response.text)
        return

    print("\n--- Step 2: User checks notifications ---")
    user_headers = {
        "X-User-Id": str(user_id),
        "X-User-Email": "user@example.com"
    }
    
    response = client.get("/api/v1/notifications", headers=user_headers)
    
    if response.status_code == 200:
        notifs = response.json()
        print(f"PASS: User retrieved {len(notifs)} notifications")
        found = False
        for n in notifs:
            if n["title"] == "Hello from Test Script":
                print(f"   Found expected notification: {n['id']}")
                found = True
                break
        
        if not found:
            print("FAIL: Expected notification not found in list")
    else:
        print("FAIL: Failed to retrieve notifications")
        print(response.status_code, response.text)

if __name__ == "__main__":
    test_notification_flow()
