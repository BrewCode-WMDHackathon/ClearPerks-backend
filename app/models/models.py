import uuid
from datetime import datetime
from sqlalchemy import (
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
from sqlalchemy.orm import relationship
from app.core.database import Base

class Profile(Base):
    __tablename__ = "profiles"

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    full_name = Column(Text, nullable=True)
    email = Column(Text, nullable=True)
    timezone = Column(Text, nullable=False, server_default="America/New_York")
    is_admin = Column(Boolean, nullable=False, server_default="false")
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
    
    # New preference fields
    news_frequency = Column(Text, nullable=False, server_default="daily") # daily|weekly|off
    social_updates = Column(Text, nullable=False, server_default="yes") # yes|no|vimp-only
    gov_notifications = Column(Boolean, nullable=False, server_default="true")
    all_disabled = Column(Boolean, nullable=False, server_default="false")

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
    type = Column(Text, nullable=True) # deprecated if category is used
    category = Column(Text, nullable=True) # news|social|gov|manual
    priority = Column(Text, nullable=False, server_default="medium") # high|medium|low
    is_cleared = Column(Integer, nullable=False, server_default="0") # 0=not cleared, 1=cleared
    
    # Push notification tracking
    push_sent = Column(Boolean, nullable=False, server_default="false")
    push_error = Column(Text, nullable=True)
    should_push = Column(Boolean, nullable=False, server_default="true")
    
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


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    iso_date = Column(DateTime(timezone=True), nullable=True)
    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    category = Column(Text, nullable=True)
    raw_id = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
