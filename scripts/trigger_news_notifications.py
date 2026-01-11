import sys
import os

# Add the parent directory to sys.path to allow imports from 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.services.ai_service import AINotificationService
from app.services.news_notification_service import NewsNotificationService

def main():
    print("Starting News Notification Process...")
    db = SessionLocal()
    try:
        # Initialize AI Service
        # Ensure OPENAI_API_KEY is in your .env or environment
        ai_service = AINotificationService()
        
        # Initialize News Service
        news_service = NewsNotificationService(db, ai_service)
        
        print("Fetching news and generating notifications...")
        # Process notifications (fetch last 24h)
        results = news_service.process_daily_news_notifications()
        
        if not results:
            print("No notifications generated.")
        else:
            for res in results:
                print(f"Category: {res['category']}")
                print(f"  Title: {res['generated_title']}")
                print(f"  Dispatched to: {res['dispatched_count']} users")
                print("-" * 30)
                
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
