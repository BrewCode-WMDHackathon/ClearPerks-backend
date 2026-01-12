from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.models import NewsArticle
from app.services.ai_service import AINotificationService
from app.services.notification_service import NotificationService

class NewsNotificationService:
    def __init__(self, db: Session, ai_service: AINotificationService):
        self.db = db
        self.ai_service = ai_service

    def fetch_top_news_per_category(self, hours: int = 50, limit: int = 10) -> Dict[str, List[NewsArticle]]:
        """
        Fetches top `limit` news articles from the past `hours` for each category.
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # 1. Get distinct categories that have news in the time range
        # Using a set comprehension on a query for optimization
        categories_query = self.db.query(NewsArticle.category).filter(
            NewsArticle.created_at >= cutoff_time
        ).distinct()
        
        category_names = [c[0] for c in categories_query.all() if c[0]]

        news_by_category = {}
        
        for cat in category_names:
            articles = self.db.query(NewsArticle).filter(
                NewsArticle.category == cat,
                NewsArticle.created_at >= cutoff_time
            ).order_by(desc(NewsArticle.created_at)).limit(limit).all()
            
            if articles:
                news_by_category[cat] = articles
        
        return news_by_category

    def process_daily_news_notifications(self, lookback_hours: int = 50) -> List[Dict[str, Any]]:
        """
        Orchestrates the fetching, generating, and storing process.
        Returns a summary of actions taken.
        """
        news_map = self.fetch_top_news_per_category(hours=lookback_hours)
        results = []
        
        if not news_map:
            print(f"No news found in the last {lookback_hours} hours.")
            return results

        for category, articles in news_map.items():
            # Prepare context for LLM
            # Summarize schema: Title and Summary
            context_lines = [f"- {a.title}: {a.summary}" for a in articles]
            context = f"Top {len(articles)} news items for category '{category}':\n" + "\n".join(context_lines)
            
            # Use AI Service to generate title/body
            generated = self.ai_service.generate_notification_content(context)
            
            title = generated.get("title", f"Update: {category}")
            body = generated.get("body", "New updates are available in this category.")
            
            # Dispatch to all users
            # utilizing the 'news' category to respect user preferences
            count = NotificationService.dispatch_to_all(
                db=self.db,
                title=title,
                body=body,
                category="news", 
                priority="medium"
            )
            
            results.append({
                "category": category,
                "generated_title": title,
                "dispatched_count": count
            })
            
        return results
