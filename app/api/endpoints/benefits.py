import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Paystub, BenefitSummary, Recommendation
from app.schemas.schemas import UserContext, BenefitSummaryOut, DashboardSnapshot, RecommendationOut
from app.services.llm_service import llm_extract_benefits_from_paystub, llm_generate_recommendations
from app.services.slm_classifier import SLMClassifier
from app.services.category_service import CategoryService

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
        # Classify text to get domain tags and signals
        classification = SLMClassifier.classify_text(f"{r['title']}. {r['description']}")
        
        # Compute relevance score components
        relevance_components = SLMClassifier.compute_relevance_components(
            r['description'], 
            classification['signals']
        )
        relevance_score = CategoryService.compute_relevance_score(
            money_score=CategoryService.compute_money_score(
                classification['signals'], 
                r.get('estimated_savings')
            ),
            urgency_score=relevance_components['urgency_score'],
            confidence_score=relevance_components['confidence_score'],
        )
        
        rec = Recommendation(
            user_id=current_user.user_id,
            benefit_summary_id=summary.id,
            title=r["title"],
            description=r["description"],
            estimated_savings=r.get("estimated_savings"),
            category=r.get("category"),  # Keep for backward compatibility
            priority=r.get("priority"),
            domain_tags=classification['domain_tags'],
            signals=classification['signals'],
            relevance_score=relevance_score,
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
    ui_category: Optional[str] = Query(None, description="Filter by UI category: Pay, Health, Retirement, Time Off"),
    has_deadline: Optional[bool] = Query(None, description="Filter to items with deadlines"),
    saves_money: Optional[bool] = Query(None, description="Filter to items that save money"),
    sort_by: str = Query("relevance_score", description="Sort field: relevance_score, created_at"),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get latest recommendations with optional filters.
    
    Filter options:
    - ui_category: Filter by derived UI category (Pay, Health, Retirement, Time Off)
    - has_deadline: Filter to items with deadline signal
    - saves_money: Filter to items with saves_money signal
    
    Sort options:
    - relevance_score: Sort by composite relevance (default)
    - created_at: Sort by creation date
    """
    latest_summary = (
        db.query(BenefitSummary)
        .filter(BenefitSummary.user_id == current_user.user_id)
        .order_by(BenefitSummary.created_at.desc())
        .first()
    )
    if not latest_summary:
        return []

    query = db.query(Recommendation).filter(
        Recommendation.benefit_summary_id == latest_summary.id
    )
    
    # Apply signal filters
    if has_deadline:
        query = query.filter(
            Recommendation.signals["has_deadline"].astext == "true"
        )
    if saves_money:
        query = query.filter(
            Recommendation.signals["saves_money"].astext == "true"
        )
    
    # Apply sorting
    if sort_by == "relevance_score":
        query = query.order_by(Recommendation.relevance_score.desc())
    else:
        query = query.order_by(Recommendation.created_at.desc())
    
    recs = query.all()
    
    # Enrich with derived fields and apply ui_category filter
    result = []
    for rec in recs:
        domain_tags = rec.domain_tags or []
        signals = rec.signals or {}
        
        derived_category = CategoryService.derive_ui_category(domain_tags, signals)
        
        # Apply ui_category filter (post-query since it's derived)
        if ui_category and derived_category != ui_category:
            continue
        
        rec_out = RecommendationOut(
            id=rec.id,
            title=rec.title,
            description=rec.description,
            estimated_savings=float(rec.estimated_savings) if rec.estimated_savings else None,
            category=rec.category,
            priority=rec.priority,
            created_at=rec.created_at,
            domain_tags=domain_tags,
            signals=signals,
            relevance_score=float(rec.relevance_score) if rec.relevance_score else 0,
            ui_category=derived_category,
            urgency_level=CategoryService.compute_urgency_level(signals, rec.priority),
        )
        result.append(rec_out)
    
    return result
