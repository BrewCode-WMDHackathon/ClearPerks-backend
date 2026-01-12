
import sys
import os
from sqlalchemy import desc

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.models import Notification

def check_notifications():
    print("--- 5 Most Recent Notifications in DB ---")
    db = SessionLocal()
    try:
        notifs = db.query(Notification).order_by(desc(Notification.created_at)).limit(5).all()
        if not notifs:
            print("No notifications found.")
        else:
            for n in notifs:
                print(f"ID: {n.id}")
                print(f"Title: {n.title}")
                print(f"Body: {n.body}")
                print(f"Category: {n.category}")
                print(f"Type: {n.type}")
                print(f"Created At: {n.created_at}")
                print("-" * 30)
    finally:
        db.close()

if __name__ == "__main__":
    check_notifications()
