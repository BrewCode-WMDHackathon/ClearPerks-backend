import os
import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import BenefitTrend, BenefitTrendItem, Profile, NotificationPreference, Notification
from app.schemas.schemas import TrendIn, TrendNotifyIn, TrendOut

router = APIRouter()

INTERNAL_API_KEY = os.getenv("INTERNAL_OPS_API_KEY") or os.getenv("INTERNAL_KESRA_API_KEY")
if not INTERNAL_API_KEY:
    INTERNAL_API_KEY = "changeme"

def verify_internal_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@router.post(
    "/internal/ops/trends",
    dependencies=[Depends(verify_internal_api_key)],
)
def ingest_trends_from_kestra(
    payload: List[TrendIn],
    db: Session = Depends(get_db),
):
    """
    Ingest trends from Kestra/n8n workflows.
    
    Now populates domain_tags and signals using SLMClassifier,
    and computes composite relevance scores.
    """
    from app.services.slm_classifier import SLMClassifier
    from app.services.category_service import CategoryService
    
    created_ids = []

    for t in payload:
        # Classify text to extract domain tags and signals
        classification = SLMClassifier.classify_text(f"{t.title}. {t.summary}")
        
        # Compute relevance components
        relevance_components = SLMClassifier.compute_relevance_components(
            t.summary, 
            classification['signals']
        )
        
        # Compute freshness (brand new)
        freshness_score = 10.0
        
        # Compute total relevance
        relevance_score = CategoryService.compute_relevance_score(
            freshness_score=freshness_score,
            urgency_score=relevance_components['urgency_score'],
            money_score=relevance_components['money_score'],
            confidence_score=relevance_components['confidence_score'],
        )
        
        # Use provided domain_tags if available, else use classified ones
        domain_tags = t.domain_tags if t.domain_tags else classification['domain_tags']
        signals = t.signals if t.signals else classification['signals']
        
        trend = BenefitTrend(
            topic_id=t.topic_id,
            title=t.title,
            summary=t.summary,
            category=t.category,  # Keep for backward compatibility
            domain_tags=domain_tags,
            signals=signals,
            freshness_score=freshness_score,
            urgency_score=relevance_components['urgency_score'],
            money_score=relevance_components['money_score'],
            confidence_score=relevance_components['confidence_score'],
            relevance_score=relevance_score,
        )
        db.add(trend)
        db.flush()  # get trend.id

        for item in t.items:
            ti = BenefitTrendItem(
                trend_id=trend.id,
                source=item.source,
                external_id=item.external_id,
                url=str(item.url) if item.url else None,
                text_snippet=item.text_snippet,
            )
            db.add(ti)

        created_ids.append(str(trend.id))

    db.commit()
    return {"created_trend_ids": created_ids}

from app.services.notification_service import NotificationService
from app.services.slm_classifier import SLMClassifier

@router.post(
    "/internal/ops/trends/notify",
    dependencies=[Depends(verify_internal_api_key)],
)
def trigger_trend_notifications(
    payload: TrendNotifyIn,
    db: Session = Depends(get_db),
):
    """
    Refactored to use NotificationService.
    """
    query = db.query(BenefitTrend)
    if payload.trend_ids:
        query = query.filter(BenefitTrend.id.in_(payload.trend_ids))
    else:
        query = query.filter(BenefitTrend.relevance_score >= 8)

    trends = query.all()

    if not trends:
        return {"message": "No trends to notify"}

    users = db.query(Profile).all()

    created = 0
    for user in users:
        for trend in trends:
            # Use SLM to classify
            slm_res = SLMClassifier.classify_text(f"{trend.title}. {trend.summary}")
            
            res = NotificationService.create_notification(
                db, 
                user.user_id, 
                title=f"Benefits Trend: {trend.title}",
                body=trend.summary[:300],
                category=slm_res["category"],
                priority=slm_res["priority"]
            )
            if res:
                created += 1

    db.commit()
    return {"message": f"Dispatched {created} notifications based on user preferences"}

@router.get("/trends", response_model=List[TrendOut])
def list_trends(
    limit: int = 20,
    db: Session = Depends(get_db),
):
    trends = (
        db.query(BenefitTrend)
        .order_by(BenefitTrend.created_at.desc())
        .limit(limit)
        .all()
    )
    return trends

@router.get("/trends/{trend_id}", response_model=TrendOut)
def get_trend(
    trend_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    trend = db.query(BenefitTrend).filter(BenefitTrend.id == trend_id).first()
    if not trend:
        raise HTTPException(404, "Trend not found")
    return trend
