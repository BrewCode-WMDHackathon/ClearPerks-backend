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

INTERNAL_API_KEY = os.getenv("INTERNAL_KESRA_API_KEY")
if not INTERNAL_API_KEY:
    INTERNAL_API_KEY = "changeme"

def verify_internal_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@router.post(
    "/internal/kestra/trends",
    dependencies=[Depends(verify_internal_api_key)],
)
def ingest_trends_from_kestra(
    payload: List[TrendIn],
    db: Session = Depends(get_db),
):
    created_ids = []

    for t in payload:
        trend = BenefitTrend(
            topic_id=t.topic_id,
            title=t.title,
            summary=t.summary,
            category=t.category,
            relevance_score=t.relevance_score,
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

@router.post(
    "/internal/kestra/trends/notify",
    dependencies=[Depends(verify_internal_api_key)],
)
def trigger_trend_notifications(
    payload: TrendNotifyIn,
    db: Session = Depends(get_db),
):
    """
    Simple strategy:
    - Find trends with relevance_score >= 8 (or the provided IDs).
    - For each user with trend_alerts=true, create a Notification row.
    - FCM push sending can be handled by a separate worker reading from notifications table.
    """
    query = db.query(BenefitTrend)
    if payload.trend_ids:
        query = query.filter(BenefitTrend.id.in_(payload.trend_ids))
    else:
        query = query.filter(BenefitTrend.relevance_score >= 8)

    trends = query.all()

    if not trends:
        return {"message": "No trends to notify"}

    users = (
        db.query(Profile)
        .join(NotificationPreference, NotificationPreference.user_id == Profile.user_id)
        .filter(NotificationPreference.trend_alerts == True)  # noqa
        .all()
    )

    created = 0
    for user in users:
        for trend in trends:
            notif = Notification(
                user_id=user.user_id,
                title=f"Benefits Trend: {trend.title}",
                body=trend.summary[:300],
                type="trend",
                scheduled_for=None,
                sent_at=datetime.utcnow(),  # in real system, set when FCM push actually sent
            )
            db.add(notif)
            created += 1

    db.commit()
    return {"message": f"Created {created} notifications"}

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
