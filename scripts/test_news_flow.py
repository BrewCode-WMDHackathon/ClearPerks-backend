
import sys
import os
import uuid
from sqlalchemy import text
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.models import Profile, NewsArticle, Notification
from app.services.ai_service import AINotificationService
from app.services.news_notification_service import NewsNotificationService

def seed_data(db):
    print("--- Seeding Data ---")
    
    # 1. Create Dummy User if needed
    user = db.query(Profile).first()
    if not user:
        print("No users found. Creating a test user...")
        user_id = uuid.uuid4()
        user = Profile(
            user_id=user_id,
            full_name="Test User",
            email="test@example.com",
            is_admin=True
        )
        db.add(user)
        db.commit()
    else:
        print(f"Using existing user: {user.user_id}")

    # 2. Insert News Articles from SQL file
    # We use IGNORING duplicates logic or just try/except
    sql_path = os.path.join(os.path.dirname(__file__), 'seed_news.sql')
    if os.path.exists(sql_path):
        print(f" executing SQL from {sql_path}...")
        with open(sql_path, 'r') as f:
            sql_content = f.read()
        
        # Simple execution. If IDs conflict, it might fail.
        # We can try to clear table first or just catch error.
        # For a clean test, let's just attempt and ignore error (assuming populated).
        try:
            db.execute(text(sql_content))
            db.commit()
            print(" News articles inserted.")
        except Exception as e:
            db.rollback()
            print(f" Warning during SQL insert (might be duplicates): {e}")
    else:
        print(" seed_news.sql not found. Skipping SQL insert.")

def run_test():
    print("\n--- Starting End-to-End News Notification Test ---")
    db = SessionLocal()
    try:
        seed_data(db)
        
        print("\n--- Processing Notifications ---")
        # Reuse the logic
        ai_service = AINotificationService()
        service = NewsNotificationService(db, ai_service)
        
        # We might need to adjust the time window in fetch logic if the SQL dates are old.
        # The SQL has dates like '2025-11-26' and '2026-01-10'. 
        # Current time in user metadata is '2026-01-10'.
        # The service defaults to past 24 hours.
        # The SQL 'created_at' is 2026-01-10 19:16:29.
        # 'published_at' is 2025/2023.
        # fetch_top_news_per_category filters by `published_at >= cutoff`.
        # Wait, if published_at is 2025, and cutoff is 2026-01-09 (24h ago), then NO news will be picked up!
        
        # I need to verify how `fetch_top_news_per_category` uses fields.
        # It uses `NewsArticle.published_at`.
        # The provided SQL has `published_at` in 2025 (e.g., '2025-11-26').
        # So the default 24h window will find NOTHING.
        # I should override `hours` to be larger, e.g., 8760 (1 year) or more.
        
        results = service.fetch_top_news_per_category(hours=24 * 365 * 5) # 5 years
        # But `process_daily_news_notifications` calls it with default args...
        # I should modify the service or subclass it or just call the method manually in this test.
        
        print(" Fetching news (overriding time window for test data)...")
        news_map = service.fetch_top_news_per_category(hours=24 * 365 * 10) # 10 years to be safe
        
        if not news_map:
            print(" No news found even with 10 year window! Check DB data.")
        else:
            print(f" Found news in categories: {list(news_map.keys())}")
            
            # Manually trigger the generation part to see output
            for cat, articles in news_map.items():
                print(f"\n Processing category: {cat}")
                context_lines = [f"- {a.title}" for a in articles]
                context = "\n".join(context_lines)
                print(f" Context (first 3 lines): {context_lines[:3]}")
                
                # Generate
                generated = ai_service.generate_notification_content(context)
                print(f" AI Output: {generated}")
                
                # Store (Optional for test, but good to verify)
                # We won't call dispatch_to_all to avoid spamming if running repeatedly,
                # but we can check if we want to.
                # Let's just print the AI output which validates the requirement.

    finally:
        db.close()
    print("\n--- Test Completed ---")

if __name__ == "__main__":
    run_test()
