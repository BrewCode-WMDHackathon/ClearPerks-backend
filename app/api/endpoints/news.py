"""
News Articles API endpoint with domain-driven filters.

Provides filtered access to news articles based on:
- ui_category: Derived from domain_tags
- has_deadline: Signal filter
- saves_money: Signal filter
- sort by relevance_score
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from app.core.database import get_db
from app.models.models import NewsArticle
from app.services.category_service import CategoryService
from app.services.slm_classifier import SLMClassifier

router = APIRouter()


# Response schema (inline to avoid circular imports)
from pydantic import BaseModel

class NewsArticleOut(BaseModel):
    id: uuid.UUID
    title: str
    url: str
    published_at: Optional[datetime]
    summary: Optional[str]
    category: Optional[str]  # DEPRECATED
    domain_tags: List[str] = []
    signals: dict = {}
    relevance_score: float = 0
    created_at: datetime
    
    # Derived fields
    ui_category: Optional[str] = None
    urgency_level: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.get("/news", response_model=List[NewsArticleOut])
def list_news_articles(
    ui_category: Optional[str] = Query(
        None, 
        description="Filter by UI category: Pay, Health, Retirement, Time Off, All"
    ),
    has_deadline: Optional[bool] = Query(
        None, 
        description="Filter to articles with deadline signals"
    ),
    saves_money: Optional[bool] = Query(
        None, 
        description="Filter to articles about saving money"
    ),
    domain_tag: Optional[str] = Query(
        None,
        description="Filter by specific domain tag: HSA, FSA, 401K, PTO, TAX, etc."
    ),
    sort_by: str = Query(
        "relevance_score", 
        description="Sort field: relevance_score, published_at, created_at"
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum results to return"),
    db: Session = Depends(get_db),
):
    """
    Get news articles with optional filters.
    
    ## Filter Options
    
    - **ui_category**: Filter by derived UI category (Pay, Health, Retirement, Time Off)
    - **has_deadline**: Filter to articles with deadline-related signals
    - **saves_money**: Filter to articles about saving money
    - **domain_tag**: Filter by specific domain tag (HSA, FSA, 401K, PTO, TAX)
    
    ## Sort Options
    
    - **relevance_score**: Sort by composite relevance (default)
    - **published_at**: Sort by publication date
    - **created_at**: Sort by when article was added
    
    ## UI Category Mapping
    
    | Domain Tags | UI Category |
    |-------------|-------------|
    | HSA, FSA, INSURANCE | Health |
    | 401K | Retirement |
    | PTO | Time Off |
    | PAYROLL, TAX | Pay |
    
    ## Example Requests
    
    ```
    GET /api/v1/news?ui_category=Health
    GET /api/v1/news?saves_money=true&sort_by=relevance_score
    GET /api/v1/news?domain_tag=HSA&limit=10
    GET /api/v1/news?has_deadline=true
    ```
    """
    query = db.query(NewsArticle)
    
    # Apply domain_tag filter (direct match on JSONB array)
    if domain_tag:
        # Filter where domain_tags array contains the specified tag
        query = query.filter(
            NewsArticle.domain_tags.op("@>")(f'["{domain_tag}"]')
        )
    
    # Apply signal filters
    if has_deadline:
        query = query.filter(
            NewsArticle.signals["has_deadline"].astext == "true"
        )
    if saves_money:
        query = query.filter(
            NewsArticle.signals["saves_money"].astext == "true"
        )
    
    # Apply sorting
    if sort_by == "published_at":
        query = query.order_by(desc(NewsArticle.published_at))
    elif sort_by == "created_at":
        query = query.order_by(desc(NewsArticle.created_at))
    else:  # Default: relevance_score
        query = query.order_by(desc(NewsArticle.relevance_score))
    
    query = query.limit(limit)
    articles = query.all()
    
    # Enrich with derived fields and apply ui_category filter
    result = []
    for article in articles:
        domain_tags = article.domain_tags or []
        signals = article.signals or {}
        
        derived_category = CategoryService.derive_ui_category(domain_tags, signals)
        
        # Apply ui_category filter (post-query since it's derived)
        if ui_category and derived_category != ui_category:
            continue
        
        article_out = NewsArticleOut(
            id=article.id,
            title=article.title,
            url=article.url,
            published_at=article.published_at,
            summary=article.summary,
            category=article.category,
            domain_tags=domain_tags,
            signals=signals,
            relevance_score=float(article.relevance_score) if article.relevance_score else 0,
            created_at=article.created_at,
            ui_category=derived_category,
            urgency_level=CategoryService.compute_urgency_level(signals),
        )
        result.append(article_out)
    
    return result


@router.get("/news/{article_id}", response_model=NewsArticleOut)
def get_news_article(
    article_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get a single news article by ID with derived fields."""
    article = db.query(NewsArticle).filter(NewsArticle.id == article_id).first()
    if not article:
        raise HTTPException(404, "News article not found")
    
    domain_tags = article.domain_tags or []
    signals = article.signals or {}
    
    return NewsArticleOut(
        id=article.id,
        title=article.title,
        url=article.url,
        published_at=article.published_at,
        summary=article.summary,
        category=article.category,
        domain_tags=domain_tags,
        signals=signals,
        relevance_score=float(article.relevance_score) if article.relevance_score else 0,
        created_at=article.created_at,
        ui_category=CategoryService.derive_ui_category(domain_tags, signals),
        urgency_level=CategoryService.compute_urgency_level(signals),
    )


@router.get("/news/deadlines", response_model=List[NewsArticleOut])
def get_deadline_news(
    days_ahead: int = Query(30, ge=1, le=365, description="Days to look ahead"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get news articles related to deadlines.
    
    This is a convenience endpoint for the "Deadlines" tab.
    Returns articles with the has_deadline signal, sorted by urgency.
    """
    articles = (
        db.query(NewsArticle)
        .filter(NewsArticle.signals["has_deadline"].astext == "true")
        .order_by(desc(NewsArticle.relevance_score))
        .limit(limit)
        .all()
    )
    
    result = []
    for article in articles:
        domain_tags = article.domain_tags or []
        signals = article.signals or {}
        
        result.append(NewsArticleOut(
            id=article.id,
            title=article.title,
            url=article.url,
            published_at=article.published_at,
            summary=article.summary,
            category=article.category,
            domain_tags=domain_tags,
            signals=signals,
            relevance_score=float(article.relevance_score) if article.relevance_score else 0,
            created_at=article.created_at,
            ui_category=CategoryService.derive_ui_category(domain_tags, signals),
            urgency_level=CategoryService.compute_urgency_level(signals),
        ))
    
    return result
