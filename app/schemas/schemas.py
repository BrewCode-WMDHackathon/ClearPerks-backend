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
    category: Optional[str]
    priority: str
    is_cleared: int
    scheduled_for: Optional[datetime]
    sent_at: Optional[datetime]
    read_at: Optional[datetime]
    created_at: datetime
    push_sent: Optional[bool] = False
    push_error: Optional[str] = None


class NotificationCreate(BaseSchema):
    user_id: Optional[uuid.UUID] = None  # if None, send to all (or filtered)
    title: str
    body: str
    category: str = "manual"
    priority: str = "medium"
    scheduled_for: Optional[datetime] = None


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
