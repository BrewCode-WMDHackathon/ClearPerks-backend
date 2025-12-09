import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Paystub, BenefitSummary, Recommendation
from app.schemas.schemas import UserContext, BenefitSummaryOut, DashboardSnapshot, RecommendationOut
from app.services.llm_service import llm_extract_benefits_from_paystub, llm_generate_recommendations

router = APIRouter()

@router.post("/parse/{paystub_id}", response_model=BenefitSummaryOut)
def parse_benefits_for_paystub(
    paystub_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    paystub = (
        db.query(Paystub)
        .filter(Paystub.id == paystub_id, Paystub.user_id == current_user.user_id)
        .first()
    )
    if not paystub:
        raise HTTPException(404, "Paystub not found")

    if paystub.status != "done":
        raise HTTPException(
            status_code=400,
            detail=f"Paystub is not ready for parsing. Current status: {paystub.status}",
        )

    extracted = llm_extract_benefits_from_paystub(paystub)

    summary = BenefitSummary(
        user_id=current_user.user_id,
        paystub_id=paystub.id,
        hsa_balance=extracted.get("hsa_balance"),
        hsa_contribution_ytd=extracted.get("hsa_contribution_ytd"),
        fsa_balance=extracted.get("fsa_balance"),
        fsa_deadline=extracted.get("fsa_deadline"),
        pto_balance_hours=extracted.get("pto_balance_hours"),
        pto_accrual_hours_per_period=extracted.get("pto_accrual_hours_per_period"),
        k401_contribution_percent=extracted.get("k401_contribution_percent"),
        k401_employer_match_percent=extracted.get("k401_employer_match_percent"),
        deductible_total=extracted.get("deductible_total"),
        deductible_used=extracted.get("deductible_used"),
        raw_summary=extracted.get("raw_summary"),
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)

    # Generate recommendations
    rec_dicts = llm_generate_recommendations(summary)
    for r in rec_dicts:
        rec = Recommendation(
            user_id=current_user.user_id,
            benefit_summary_id=summary.id,
            title=r["title"],
            description=r["description"],
            estimated_savings=r.get("estimated_savings"),
            category=r.get("category"),
            priority=r.get("priority"),
        )
        db.add(rec)
    db.commit()

    return summary

@router.get("/dashboard", response_model=DashboardSnapshot)
def get_dashboard_snapshot(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    latest = (
        db.query(BenefitSummary)
        .filter(BenefitSummary.user_id == current_user.user_id)
        .order_by(BenefitSummary.created_at.desc())
        .first()
    )
    return {"latest_summary": BenefitSummaryOut.from_orm(latest) if latest else None}

@router.get("/summaries", response_model=List[BenefitSummaryOut])
def list_benefit_summaries(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summaries = (
        db.query(BenefitSummary)
        .filter(BenefitSummary.user_id == current_user.user_id)
        .order_by(BenefitSummary.created_at.desc())
        .all()
    )
    return summaries

@router.get("/summaries/{summary_id}", response_model=BenefitSummaryOut)
def get_benefit_summary(
    summary_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summary = (
        db.query(BenefitSummary)
        .filter(
            BenefitSummary.id == summary_id,
            BenefitSummary.user_id == current_user.user_id,
        )
        .first()
    )
    if not summary:
        raise HTTPException(404, "Summary not found")
    return summary

@router.get("/recommendations/latest", response_model=List[RecommendationOut])
def get_latest_recommendations(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    latest_summary = (
        db.query(BenefitSummary)
        .filter(BenefitSummary.user_id == current_user.user_id)
        .order_by(BenefitSummary.created_at.desc())
        .first()
    )
    if not latest_summary:
        return []

    recs = (
        db.query(Recommendation)
        .filter(Recommendation.benefit_summary_id == latest_summary.id)
        .order_by(Recommendation.created_at.desc())
        .all()
    )
    return recs
