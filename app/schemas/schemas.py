import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, AnyHttpUrl, Field

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
    news_frequency: str
    social_updates: str
    gov_notifications: bool
    all_disabled: bool


class NotificationPreferencesUpdate(BaseSchema):
    pto_alerts: Optional[bool] = None
    fsa_alerts: Optional[bool] = None
    hsa_alerts: Optional[bool] = None
    k401_alerts: Optional[bool] = None
    deductible_alerts: Optional[bool] = None
    trend_alerts: Optional[bool] = None
    news_frequency: Optional[str] = None
    social_updates: Optional[str] = None
    gov_notifications: Optional[bool] = None
    all_disabled: Optional[bool] = None


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
    category: Optional[str] = None  # DEPRECATED: use ui_category
    priority: Optional[str]
    created_at: datetime
    
    # Domain-driven fields
    domain_tags: List[str] = []
    signals: dict = {}
    relevance_score: float = 0
    
    # Derived fields (computed at runtime)
    ui_category: Optional[str] = None
    urgency_level: Optional[str] = None


class DeviceTokenIn(BaseSchema):
    token: str
    platform: Optional[str] = None


class NotificationOut(BaseSchema):
    id: uuid.UUID
    title: str
    body: str
    type: Optional[str] = None  # DEPRECATED
    category: Optional[str] = None  # DEPRECATED: use ui_category
    priority: str
    is_cleared: int
    scheduled_for: Optional[datetime]
    sent_at: Optional[datetime]
    read_at: Optional[datetime]
    created_at: datetime
    push_sent: Optional[bool] = False
    push_error: Optional[str] = None
    
    # Domain-driven fields
    domain_tags: List[str] = []
    signals: dict = {}
    relevance_score: float = 0
    deadline_date: Optional[datetime] = None
    
    # Derived fields (computed at runtime)
    ui_category: Optional[str] = None
    urgency_level: Optional[str] = None
    is_deadline: Optional[bool] = None


class NotificationCreate(BaseSchema):
    user_id: Optional[uuid.UUID] = None  # if None, send to all (or filtered)
    title: str
    body: str
    category: str = "manual"  # DEPRECATED: kept for backward compatibility
    priority: str = "medium"
    scheduled_for: Optional[datetime] = None
    
    # New domain-driven fields
    domain_tags: List[str] = []
    signals: dict = {}
    deadline_date: Optional[datetime] = None


class TrendItemIn(BaseSchema):
    source: Optional[str] = None
    external_id: Optional[str] = None
    url: Optional[AnyHttpUrl] = None
    text_snippet: Optional[str] = None


class TrendIn(BaseSchema):
    topic_id: Optional[str] = None
    title: str
    summary: str
    category: Optional[str] = None  # DEPRECATED
    relevance_score: Optional[float] = None
    items: List[TrendItemIn] = Field(default_factory=list)
    
    # New domain-driven fields
    domain_tags: List[str] = []
    signals: dict = {}


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
    category: Optional[str] = None  # DEPRECATED: use ui_category
    relevance_score: float = 0
    created_at: datetime
    items: List[TrendItemOut]
    
    # Domain-driven fields
    domain_tags: List[str] = []
    signals: dict = {}
    
    # Derived fields (computed at runtime)
    ui_category: Optional[str] = None
    urgency_level: Optional[str] = None


# Filter query schema for content APIs
class ContentFilterParams(BaseSchema):
    """Filter parameters for content queries."""
    ui_category: Optional[str] = None  # "Pay", "Health", "Retirement", "Time Off"
    has_deadline: Optional[bool] = None
    saves_money: Optional[bool] = None
    urgency: Optional[str] = None  # "high", "medium", "normal"
    sort_by: str = "relevance_score"
    sort_order: str = "desc"
    limit: int = 50
