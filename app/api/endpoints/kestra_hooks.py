import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models.models import BenefitSummary, Notification
from app.schemas.schemas import UserContext

router = APIRouter()

INTERNAL_API_KEY = os.getenv("INTERNAL_KESRA_API_KEY", "changeme")

def verify_internal_key(x_internal_key: str = Header(None)):
    """Verify internal API key for Kestra workflows"""
    if x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid internal API key")
    return True

@router.get("/fsa-audit")
def fsa_deadline_audit(
    _: bool = Depends(verify_internal_key),
    db: Session = Depends(get_db),
):
    """
    Returns users with FSA balances expiring within 60 days.
    Called by Kestra for FSA deadline alerts.
    """
    # Get latest benefit summaries with FSA balance > 0
    sixty_days_from_now = datetime.utcnow() + timedelta(days=60)
    
    summaries = (
        db.query(BenefitSummary)
        .filter(
            and_(
                BenefitSummary.fsa_balance > 0,
                BenefitSummary.fsa_deadline.isnot(None),
                BenefitSummary.fsa_deadline <= sixty_days_from_now
            )
        )
        .all()
    )
    
    users_at_risk = [
        {
            "user_id": str(summary.user_id),
            "fsa_balance": float(summary.fsa_balance),
            "fsa_deadline": summary.fsa_deadline.isoformat() if summary.fsa_deadline else None,
            "days_remaining": (summary.fsa_deadline - datetime.utcnow()).days if summary.fsa_deadline else None
        }
        for summary in summaries
    ]
    
    return {
        "users_at_risk": users_at_risk,
        "total_count": len(users_at_risk),
        "audit_date": datetime.utcnow().isoformat()
    }

@router.post("/aggregate")
def aggregate_trends(
    payload: dict,
    _: bool = Depends(verify_internal_key),
    db: Session = Depends(get_db),
):
    """
    Aggregates benefits usage trends.
    Called by Kestra for weekly analytics.
    """
    period = payload.get("period", "weekly")
    metrics = payload.get("metrics", [])
    
    # Stub implementation - in production, this would aggregate real data
    return {
        "id": "agg_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
        "period": period,
        "metrics": metrics,
        "status": "completed",
        "created_at": datetime.utcnow().isoformat()
    }

@router.post("/insights")
def generate_insights(
    payload: dict,
    _: bool = Depends(verify_internal_key),
    db: Session = Depends(get_db),
):
    """
    Generates insights from aggregated data.
    Called by Kestra after aggregation.
    """
    aggregation_id = payload.get("aggregation_id")
    
    # Stub implementation
    return {
        "report_id": "rpt_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
        "aggregation_id": aggregation_id,
        "insights": [
            {
                "category": "FSA",
                "insight": "30% of users have unused FSA balances",
                "recommendation": "Send reminder notifications"
            }
        ],
        "created_at": datetime.utcnow().isoformat()
    }
