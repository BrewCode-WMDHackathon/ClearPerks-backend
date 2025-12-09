"""
app/main.py

FastAPI backend implementing all APIs from the AI Benefits Optimizer + Trends Engine spec.

Notes:
- Uses a simple header-based auth (X-User-Id) for hackathon speed.
  Replace `get_current_user` with real Supabase JWT verification.
- OCR and LLM integrations are stubbed; plug in PaddleOCR + OpenAI where marked TODO.
"""

import os
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    BackgroundTasks,
    Header,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, AnyHttpUrl, Field
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Numeric,
    Integer,
    Date,
    JSON,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    sessionmaker,
    declarative_base,
    relationship,
    Session,
)

# ---------------------------------------------------------------------------
# DB SETUP
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:ClearPerks#2025@db.iineirmxjuevguwhcxjv.supabase.co:5432/postgres",
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# ORM MODELS (mirror Supabase schema)
# ---------------------------------------------------------------------------


class Profile(Base):
    __tablename__ = "profiles"

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    full_name = Column(Text, nullable=True)
    email = Column(Text, nullable=True)
    timezone = Column(Text, nullable=False, server_default="America/New_York")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    paystubs = relationship("Paystub", back_populates="user", cascade="all, delete")
    benefit_summaries = relationship(
        "BenefitSummary", back_populates="user", cascade="all, delete"
    )
    recommendations = relationship(
        "Recommendation", back_populates="user", cascade="all, delete"
    )
    notification_preferences = relationship(
        "NotificationPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete",
    )
    notifications = relationship(
        "Notification", back_populates="user", cascade="all, delete"
    )
    device_tokens = relationship(
        "DeviceToken", back_populates="user", cascade="all, delete"
    )


class Paystub(Base):
    __tablename__ = "paystubs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.user_id", ondelete="CASCADE")
    )
    file_url = Column(Text, nullable=True)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    ocr_text = Column(Text, nullable=True)
    parsed_data = Column(JSON, nullable=True)
    status = Column(
        Text, nullable=False, server_default="uploaded"
    )  # uploaded|processing|done|error
    error_message = Column(Text, nullable=True)

    user = relationship("Profile", back_populates="paystubs")
    benefit_summaries = relationship(
        "BenefitSummary", back_populates="paystub", cascade="all, delete"
    )


class BenefitSummary(Base):
    __tablename__ = "benefit_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.user_id", ondelete="CASCADE")
    )
    paystub_id = Column(
        UUID(as_uuid=True), ForeignKey("paystubs.id", ondelete="CASCADE")
    )

    hsa_balance = Column(Numeric, nullable=True)
    hsa_contribution_ytd = Column(Numeric, nullable=True)
    fsa_balance = Column(Numeric, nullable=True)
    fsa_deadline = Column(Date, nullable=True)
    pto_balance_hours = Column(Numeric, nullable=True)
    pto_accrual_hours_per_period = Column(Numeric, nullable=True)
    k401_contribution_percent = Column(Numeric, nullable=True)
    k401_employer_match_percent = Column(Numeric, nullable=True)
    deductible_total = Column(Numeric, nullable=True)
    deductible_used = Column(Numeric, nullable=True)
    raw_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("Profile", back_populates="benefit_summaries")
    paystub = relationship("Paystub", back_populates="benefit_summaries")
    recommendations = relationship(
        "Recommendation", back_populates="benefit_summary", cascade="all, delete"
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.user_id", ondelete="CASCADE")
    )
    benefit_summary_id = Column(
        UUID(as_uuid=True), ForeignKey("benefit_summaries.id", ondelete="CASCADE")
    )
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    estimated_savings = Column(Numeric, nullable=True)
    category = Column(Text, nullable=True)
    priority = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("Profile", back_populates="recommendations")
    benefit_summary = relationship("BenefitSummary", back_populates="recommendations")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    pto_alerts = Column(Boolean, nullable=False, server_default="true")
    fsa_alerts = Column(Boolean, nullable=False, server_default="true")
    hsa_alerts = Column(Boolean, nullable=False, server_default="true")
    k401_alerts = Column(Boolean, nullable=False, server_default="true")
    deductible_alerts = Column(Boolean, nullable=False, server_default="true")
    trend_alerts = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("Profile", back_populates="notification_preferences")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.user_id", ondelete="CASCADE")
    )
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    type = Column(Text, nullable=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("Profile", back_populates="notifications")


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("profiles.user_id", ondelete="CASCADE")
    )
    token = Column(Text, nullable=False)
    platform = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("Profile", back_populates="device_tokens")


class BenefitTrend(Base):
    __tablename__ = "benefit_trends"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id = Column(Text, nullable=True)
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    category = Column(Text, nullable=True)
    relevance_score = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship(
        "BenefitTrendItem", back_populates="trend", cascade="all, delete"
    )


class BenefitTrendItem(Base):
    __tablename__ = "benefit_trend_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trend_id = Column(
        UUID(as_uuid=True), ForeignKey("benefit_trends.id", ondelete="CASCADE")
    )
    source = Column(Text, nullable=True)
    external_id = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    text_snippet = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    trend = relationship("BenefitTrend", back_populates="items")


# ---------------------------------------------------------------------------
# Pydantic Schemas (Pydantic v2 compatible)
# ---------------------------------------------------------------------------


# Base schema enabling attribute access (replaces v1 `orm_mode`)
class BaseSchema(BaseModel):
    model_config = {"from_attributes": True}


class UserContext(BaseSchema):
    user_id: uuid.UUID
    email: Optional[str] = None


class ProfileOut(BaseSchema):
    user_id: uuid.UUID
    full_name: Optional[str]
    email: Optional[str]
    timezone: str


class ProfileUpdate(BaseSchema):
    full_name: Optional[str] = None
    timezone: Optional[str] = None


class NotificationPreferencesOut(BaseSchema):
    pto_alerts: bool
    fsa_alerts: bool
    hsa_alerts: bool
    k401_alerts: bool
    deductible_alerts: bool
    trend_alerts: bool


class NotificationPreferencesUpdate(BaseSchema):
    pto_alerts: Optional[bool] = None
    fsa_alerts: Optional[bool] = None
    hsa_alerts: Optional[bool] = None
    k401_alerts: Optional[bool] = None
    deductible_alerts: Optional[bool] = None
    trend_alerts: Optional[bool] = None


class PaystubOut(BaseSchema):
    id: uuid.UUID
    file_url: Optional[str]
    upload_date: datetime
    ocr_text: Optional[str]
    parsed_data: Optional[dict]
    status: str
    error_message: Optional[str]


class BenefitSummaryOut(BaseSchema):
    id: uuid.UUID
    paystub_id: uuid.UUID
    hsa_balance: Optional[float]
    hsa_contribution_ytd: Optional[float]
    fsa_balance: Optional[float]
    fsa_deadline: Optional[datetime]
    pto_balance_hours: Optional[float]
    pto_accrual_hours_per_period: Optional[float]
    k401_contribution_percent: Optional[float]
    k401_employer_match_percent: Optional[float]
    deductible_total: Optional[float]
    deductible_used: Optional[float]
    raw_summary: Optional[dict]
    created_at: datetime


class DashboardSnapshot(BaseSchema):
    latest_summary: Optional[BenefitSummaryOut] = None


class RecommendationOut(BaseSchema):
    id: uuid.UUID
    title: str
    description: str
    estimated_savings: Optional[float]
    category: Optional[str]
    priority: Optional[str]
    created_at: datetime


class DeviceTokenIn(BaseSchema):
    token: str
    platform: Optional[str] = None


class NotificationOut(BaseSchema):
    id: uuid.UUID
    title: str
    body: str
    type: Optional[str]
    scheduled_for: Optional[datetime]
    sent_at: Optional[datetime]
    read_at: Optional[datetime]
    created_at: datetime


class TrendItemIn(BaseSchema):
    source: Optional[str] = None
    external_id: Optional[str] = None
    url: Optional[AnyHttpUrl] = None
    text_snippet: Optional[str] = None


class TrendIn(BaseSchema):
    topic_id: Optional[str] = None
    title: str
    summary: str
    category: Optional[str] = None
    relevance_score: Optional[int] = None
    items: List[TrendItemIn] = Field(default_factory=list)


class TrendNotifyIn(BaseSchema):
    trend_ids: Optional[List[uuid.UUID]] = None  # if None, use all high-scoring


class TrendItemOut(BaseSchema):
    id: uuid.UUID
    source: Optional[str]
    external_id: Optional[str]
    url: Optional[str]
    text_snippet: Optional[str]


class TrendOut(BaseSchema):
    id: uuid.UUID
    topic_id: Optional[str]
    title: str
    summary: str
    category: Optional[str]
    relevance_score: Optional[int]
    created_at: datetime
    items: List[TrendItemOut]


# ---------------------------------------------------------------------------
# Auth dependency (replace with Supabase JWT verification later)
# ---------------------------------------------------------------------------


def get_current_user(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_user_email: Optional[str] = Header(default=None, alias="X-User-Email"),
    db: Session = Depends(get_db),
) -> UserContext:
    """
    Hackathon-friendly auth:
    - Accepts X-User-Id header as UUID string.
    - Optionally X-User-Email.
    - Ensures a Profile exists for this user.

    Replace this with proper Supabase JWT verification in production.
    """
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-Id header required (stub auth).",
        )
    try:
        user_id = uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-User-Id UUID")

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        profile = Profile(user_id=user_id, email=x_user_email)
        db.add(profile)
        # initialize default notification prefs
        prefs = NotificationPreference(user=profile)
        db.add(prefs)
        db.commit()
        db.refresh(profile)

    return UserContext(user_id=profile.user_id, email=profile.email)


# ---------------------------------------------------------------------------
# Helper: OCR + LLM STUBS
# ---------------------------------------------------------------------------


def run_ocr_and_parse(paystub_id: uuid.UUID, file_path: str, db: Session):
    """
    TODO: replace with real PaddleOCR and heuristic parsing.
    """
    paystub = db.query(Paystub).filter(Paystub.id == paystub_id).first()
    if not paystub:
        return

    try:
        # Fake OCR text
        ocr_text = f"FAKE OCR TEXT for file {file_path}"
        parsed_data = {
            "gross_pay": 5000,
            "net_pay": 3800,
            "pto_hours": 40,
            "hsa_balance": 1200,
            "fsa_balance": 500,
        }

        paystub.ocr_text = ocr_text
        paystub.parsed_data = parsed_data
        paystub.status = "done"
        db.commit()
    except Exception as e:
        paystub.status = "error"
        paystub.error_message = str(e)
        db.commit()


def llm_extract_benefits_from_paystub(paystub: Paystub) -> dict:
    """
    TODO: call OpenAI GPT-4.1-mini with a structured extraction prompt.
    For now, derive from parsed_data stub.
    """
    data = paystub.parsed_data or {}
    return {
        "hsa_balance": data.get("hsa_balance", 0),
        "hsa_contribution_ytd": 0,
        "fsa_balance": data.get("fsa_balance", 0),
        "fsa_deadline": None,
        "pto_balance_hours": data.get("pto_hours", 0),
        "pto_accrual_hours_per_period": 4,
        "k401_contribution_percent": 5,
        "k401_employer_match_percent": 4,
        "deductible_total": 2000,
        "deductible_used": 500,
        "raw_summary": {
            "explanation": "Stubbed benefits summary generated by LLM.",
            "source": "stub",
        },
    }


def llm_generate_recommendations(summary: BenefitSummary) -> List[dict]:
    """
    TODO: call LLM to generate recommendations based on summary.
    """
    recs = []

    if summary.k401_contribution_percent and summary.k401_employer_match_percent:
        if float(summary.k401_contribution_percent) < float(
            summary.k401_employer_match_percent
        ):
            recs.append(
                {
                    "title": "Increase 401(k) contribution",
                    "description": "You are below your employer match rate. Consider increasing to at least the match to avoid leaving money on the table.",
                    "estimated_savings": 500,
                    "category": "401k",
                    "priority": "high",
                }
            )

    if summary.fsa_balance and summary.fsa_balance > 0:
        recs.append(
            {
                "title": "Use your FSA balance",
                "description": "You have unused FSA balance. Schedule eligible health expenses before it expires.",
                "estimated_savings": float(summary.fsa_balance),
                "category": "FSA",
                "priority": "medium",
            }
        )

    if summary.pto_balance_hours and summary.pto_balance_hours > 80:
        recs.append(
            {
                "title": "Take some PTO",
                "description": "Your PTO balance is high. Consider taking time off to avoid hitting accrual caps.",
                "estimated_savings": None,
                "category": "PTO",
                "priority": "medium",
            }
        )

    if not recs:
        recs.append(
            {
                "title": "Your benefits look on track",
                "description": "We didn’t find any urgent actions. Review your benefits annually or when your life situation changes.",
                "estimated_savings": None,
                "category": "general",
                "priority": "low",
            }
        )

    return recs


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Benefits Optimizer API",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock down in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve local frontend files (helpful during development so frontend isn't opened via file://)
# Place static frontend files under a `static/` directory at the repo root and visit
# http://localhost:8000/static/index.html to load them via HTTP (avoids file:// CORS errors).
# Ensure a `static/` directory exists at the project root (avoid runtime error
# when `StaticFiles` is mounted). Use the repository root (parent of `app/`).
project_root = Path(__file__).resolve().parent.parent
static_path = project_root / "static"
static_path.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# A simple root endpoint with pointers to docs/openapi for quick checks
@app.get("/", include_in_schema=False)
def root():
    return JSONResponse(
        {"message": "AI Benefits Optimizer API", "docs": f"{API_PREFIX}/docs", "openapi": f"{API_PREFIX}/openapi.json"}
    )


# Create tables (for local dev; skip if using Supabase migrations)
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


API_PREFIX = "/api/v1"


# ---------------------------------------------------------------------------
# /me: profile + preferences
# ---------------------------------------------------------------------------


@app.get(f"{API_PREFIX}/me", response_model=dict)
def get_me(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()
    prefs = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == current_user.user_id)
        .first()
    )
    return {
        "profile": ProfileOut.from_orm(profile),
        "notification_preferences": NotificationPreferencesOut.from_orm(prefs),
    }


@app.patch(f"{API_PREFIX}/me", response_model=ProfileOut)
def update_me(
    payload: ProfileUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()
    if not profile:
        raise HTTPException(404, "Profile not found")

    if payload.full_name is not None:
        profile.full_name = payload.full_name
    if payload.timezone is not None:
        profile.timezone = payload.timezone
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


@app.delete(f"{API_PREFIX}/me", status_code=204)
def delete_me(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.user_id).first()
    if not profile:
        raise HTTPException(404, "Profile not found")
    db.delete(profile)
    db.commit()
    return JSONResponse(status_code=204, content=None)


# ---------------------------------------------------------------------------
# PAYSTUB APIs
# ---------------------------------------------------------------------------


@app.post(f"{API_PREFIX}/paystubs", response_model=PaystubOut)
def upload_paystub(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Save file locally for now; replace with Supabase storage / S3.
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(upload_dir, f"{file_id}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    paystub = Paystub(
        user_id=current_user.user_id,
        file_url=file_path,  # in prod, use public URL
        status="processing",
    )
    db.add(paystub)
    db.commit()
    db.refresh(paystub)

    # Kick off OCR in background
    background_tasks.add_task(run_ocr_and_parse, paystub.id, file_path, SessionLocal())

    return paystub


@app.get(f"{API_PREFIX}/paystubs", response_model=List[PaystubOut])
def list_paystubs(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    paystubs = (
        db.query(Paystub)
        .filter(Paystub.user_id == current_user.user_id)
        .order_by(Paystub.upload_date.desc())
        .all()
    )
    return paystubs


@app.get(f"{API_PREFIX}/paystubs/{{paystub_id}}", response_model=PaystubOut)
def get_paystub(
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
    return paystub


@app.delete(f"{API_PREFIX}/paystubs/{{paystub_id}}", status_code=204)
def delete_paystub(
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
    db.delete(paystub)
    db.commit()
    return JSONResponse(status_code=204, content=None)


# ---------------------------------------------------------------------------
# BENEFIT ANALYSIS APIs
# ---------------------------------------------------------------------------


@app.post(
    f"{API_PREFIX}/benefits/parse/{{paystub_id}}", response_model=BenefitSummaryOut
)
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


@app.get(f"{API_PREFIX}/benefits/dashboard", response_model=DashboardSnapshot)
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


@app.get(f"{API_PREFIX}/benefits/summaries", response_model=List[BenefitSummaryOut])
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


@app.get(
    f"{API_PREFIX}/benefits/summaries/{{summary_id}}", response_model=BenefitSummaryOut
)
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


# ---------------------------------------------------------------------------
# RECOMMENDATIONS
# ---------------------------------------------------------------------------


@app.get(f"{API_PREFIX}/recommendations/latest", response_model=List[RecommendationOut])
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


# ---------------------------------------------------------------------------
# DEVICE TOKENS
# ---------------------------------------------------------------------------


@app.post(f"{API_PREFIX}/notifications/device-token", status_code=201)
def save_device_token(
    payload: DeviceTokenIn,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(DeviceToken)
        .filter(
            DeviceToken.user_id == current_user.user_id,
            DeviceToken.token == payload.token,
        )
        .first()
    )
    if existing:
        existing.platform = payload.platform
        existing.last_used_at = datetime.utcnow()
        db.commit()
        return {"message": "Token updated"}

    token = DeviceToken(
        user_id=current_user.user_id,
        token=payload.token,
        platform=payload.platform,
    )
    db.add(token)
    db.commit()
    return {"message": "Token stored"}


# ---------------------------------------------------------------------------
# USER NOTIFICATION CENTER + PREFERENCES
# ---------------------------------------------------------------------------


@app.get(f"{API_PREFIX}/notifications", response_model=List[NotificationOut])
def list_notifications(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.user_id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return notifications


@app.patch(
    f"{API_PREFIX}/notifications/{{notification_id}}/read",
    response_model=NotificationOut,
)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.user_id,
        )
        .first()
    )
    if not notif:
        raise HTTPException(404, "Notification not found")
    notif.read_at = datetime.utcnow()
    db.commit()
    db.refresh(notif)
    return notif


@app.get(
    f"{API_PREFIX}/notification-preferences",
    response_model=NotificationPreferencesOut,
)
def get_notification_preferences(
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == current_user.user_id)
        .first()
    )
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@app.patch(
    f"{API_PREFIX}/notification-preferences",
    response_model=NotificationPreferencesOut,
)
def update_notification_preferences(
    payload: NotificationPreferencesUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == current_user.user_id)
        .first()
    )
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.user_id)
        db.add(prefs)

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(prefs, field, value)

    prefs.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prefs)
    return prefs


# ---------------------------------------------------------------------------
# TRENDS FEATURE APIs
# ---------------------------------------------------------------------------


INTERNAL_API_KEY = os.getenv("INTERNAL_KESRA_API_KEY", "changeme")


def verify_internal_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.post(
    f"{API_PREFIX}/internal/kestra/trends",
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


@app.post(
    f"{API_PREFIX}/internal/kestra/trends/notify",
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


@app.get(f"{API_PREFIX}/trends", response_model=List[TrendOut])
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


@app.get(f"{API_PREFIX}/trends/{{trend_id}}", response_model=TrendOut)
def get_trend(
    trend_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    trend = db.query(BenefitTrend).filter(BenefitTrend.id == trend_id).first()
    if not trend:
        raise HTTPException(404, "Trend not found")
    return trend
