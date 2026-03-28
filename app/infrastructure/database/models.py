from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    Date,
    UniqueConstraint,
    Index,
    ForeignKey,
    SmallInteger,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, NUMERIC, BYTEA
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base

# ---------- identity.users ----------


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "identity"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    google_sub: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    plan: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    plan_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("email", name="uq_identity_users_email"),
        UniqueConstraint("google_sub", name="uq_identity_users_google_sub"),
        {"schema": "identity"},
    )

    __mapper_args__ = {"eager_defaults": True}

Index("idx_users_google_sub", User.google_sub)
Index("idx_users_email", User.email)
Index("idx_users_stripe_customer_id", User.stripe_customer_id)

# ---------- subscriptions.subscription_events ----------


class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"
    __table_args__ = {"schema": "subscriptions"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_plan: Mapped[Optional[str]] = mapped_column(String(20))
    to_plan: Mapped[Optional[str]] = mapped_column(String(20))
    stripe_event_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    event_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

# ---------- calculations.calculation_requests ----------


class CalculationRequest(Base):
    __tablename__ = "calculation_requests"
    __table_args__ = {"schema": "calculations"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=False
    )
    plan_snapshot: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    shipment_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    lines_data: Mapped[list] = mapped_column(JSONB, nullable=False)
    requested_engines: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

Index("idx_calc_requests_user_id", CalculationRequest.user_id)
Index("idx_calc_requests_status", CalculationRequest.status)
Index("idx_calc_requests_created_at", CalculationRequest.created_at)

# ---------- calculations.calculation_results ----------


class CalculationResult(Base):
    __tablename__ = "calculation_results"
    __table_args__ = {"schema": "calculations"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True)
    request_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calculations.calculation_requests.id"), unique=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.users.id"), nullable=False
    )
    line_results: Mapped[dict] = mapped_column(JSONB, nullable=False)
    engine_results: Mapped[dict] = mapped_column(JSONB, nullable=False)
    totals: Mapped[dict] = mapped_column(JSONB, nullable=False)
    audit_trail: Mapped[list] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(NUMERIC(4, 3), nullable=False)
    warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

Index("idx_calc_results_user_id", CalculationResult.user_id)
Index("idx_calc_results_created_at", CalculationResult.created_at)

# ---------- calculations.calculation_profiles ----------


FREE_TIER_PROFILE_LIMIT = 5


class CalculationProfile(Base):
    """
    A named, saved calculation that a user can revisit and edit.
    Free-tier users are capped at FREE_TIER_PROFILE_LIMIT profiles.
    """

    __tablename__ = "calculation_profiles"
    __table_args__ = {"schema": "calculations"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    # Mirror of CalculationRequest fields
    shipment_data: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {origin, destination, fx_date}
    lines_data: Mapped[list] = mapped_column(JSONB, nullable=False)     # [{hs_code, description, ...}]
    # Cached result from the most recent run (may be null if never executed)
    last_result: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


Index("idx_calc_profiles_user_id", CalculationProfile.user_id)
Index("idx_calc_profiles_updated_at", CalculationProfile.updated_at)

# ---------- tariff.hs_codes ----------


class HSCode(Base):
    __tablename__ = "hs_codes"
    __table_args__ = {"schema": "tariff"}

    code: Mapped[str] = mapped_column(String(12), primary_key=True)
    jurisdiction: Mapped[str] = mapped_column(String(5), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    parent_code: Mapped[Optional[str]] = mapped_column(String(12), ForeignKey("tariff.hs_codes.code"))
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    supplementary_unit: Mapped[Optional[str]] = mapped_column(String(50))
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[Optional[date]] = mapped_column(Date)

# ---------- tariff.tariff_measures ----------


class TariffMeasure(Base):
    __tablename__ = "tariff_measures"
    __table_args__ = {"schema": "tariff"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    hs_code: Mapped[str] = mapped_column(String(12), ForeignKey("tariff.hs_codes.code"), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(5), nullable=False)
    measure_type: Mapped[str] = mapped_column(String(50), nullable=False)
    country_of_origin: Mapped[Optional[str]] = mapped_column(String(5))
    preferential_agreement: Mapped[Optional[str]] = mapped_column(String(100))
    rate_ad_valorem: Mapped[Optional[Decimal]] = mapped_column(NUMERIC(8, 4))
    rate_specific_amount: Mapped[Optional[Decimal]] = mapped_column(NUMERIC(14, 4))
    rate_specific_unit: Mapped[Optional[str]] = mapped_column(String(50))
    rate_minimum: Mapped[Optional[Decimal]] = mapped_column(NUMERIC(14, 4))
    rate_maximum: Mapped[Optional[Decimal]] = mapped_column(NUMERIC(14, 4))
    agricultural_component: Mapped[Optional[Decimal]] = mapped_column(NUMERIC(14, 4))
    quota_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("tariff.tariff_quotas.id"))
    suspension: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    measure_condition: Mapped[Optional[dict]] = mapped_column(JSONB)
    raw_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[Optional[date]] = mapped_column(Date)
    source_dataset: Mapped[str] = mapped_column(String(20), nullable=False)
    source_measure_id: Mapped[Optional[str]] = mapped_column(String(100))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

Index("idx_tariff_measures_hs_code", TariffMeasure.hs_code)
Index(
    "idx_tariff_measures_lookup",
    TariffMeasure.hs_code,
    TariffMeasure.jurisdiction,
    TariffMeasure.country_of_origin,
    TariffMeasure.valid_from,
    TariffMeasure.valid_to,
)
Index("idx_tariff_measures_valid", TariffMeasure.valid_to)

# ---------- tariff.vat_rates ----------


class VATRate(Base):
    __tablename__ = "vat_rates"
    __table_args__ = {"schema": "tariff"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(5), nullable=False)
    rate_type: Mapped[str] = mapped_column(String(20), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(NUMERIC(6, 3), nullable=False)
    hs_code_prefix: Mapped[Optional[str]] = mapped_column(String(6))
    valid_from: Mapped[Optional[date]] = mapped_column(Date)
    valid_to: Mapped[Optional[date]] = mapped_column(Date)
    source: Mapped[Optional[str]] = mapped_column(String(30))
    raw_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


Index("idx_vat_rates_country", VATRate.country_code)
Index("idx_vat_rates_lookup", VATRate.country_code, VATRate.jurisdiction, VATRate.hs_code_prefix)

# ---------- tariff.tariff_quotas ----------


class TariffQuota(Base):
    __tablename__ = "tariff_quotas"
    __table_args__ = {"schema": "tariff"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    quota_order_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(5), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    volume: Mapped[Decimal] = mapped_column(NUMERIC(18, 4), nullable=False)
    volume_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    balance: Mapped[Optional[Decimal]] = mapped_column(NUMERIC(18, 4))
    last_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

# ---------- tariff.origin_rules ----------


class OriginRule(Base):
    __tablename__ = "origin_rules"
    __table_args__ = {"schema": "tariff"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agreement: Mapped[str] = mapped_column(String(100), nullable=False)
    hs_code_start: Mapped[str] = mapped_column(String(12), nullable=False)
    hs_code_end: Mapped[str] = mapped_column(String(12), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False)
    rvc_threshold: Mapped[Optional[Decimal]] = mapped_column(NUMERIC(5, 2))
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[Optional[date]] = mapped_column(Date)

# ---------- fx.fx_rates ----------


class FXRate(Base):
    __tablename__ = "fx_rates"
    __table_args__ = {"schema": "fx"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(NUMERIC(18, 8), nullable=False)
    rate_type: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(100))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

Index(
    "uq_fx_rates_unique",
    FXRate.base_currency,
    FXRate.quote_currency,
    FXRate.rate_type,
    FXRate.effective_date,
    unique=True,
)
Index(
    "idx_fx_rates_lookup",
    FXRate.base_currency,
    FXRate.quote_currency,
    FXRate.rate_type,
    FXRate.effective_date.desc(),
)

# ---------- compliance.restricted_goods ----------


class RestrictedGood(Base):
    __tablename__ = "restricted_goods"
    __table_args__ = {"schema": "compliance"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    hs_code_pattern: Mapped[str] = mapped_column(String(12), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(5), nullable=False)
    restriction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    license_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    certificate_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    outright_prohibited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[Optional[date]] = mapped_column(Date)

# ---------- compliance.sanctions ----------


class Sanction(Base):
    __tablename__ = "sanctions"
    __table_args__ = {"schema": "compliance"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(5), nullable=False)
    sanction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    hs_code_scope: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[Optional[date]] = mapped_column(Date)

# ---------- ingestion.ingestion_runs ----------


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = {"schema": "ingestion"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    records_processed: Mapped[Optional[int]] = mapped_column(Integer)
    records_inserted: Mapped[Optional[int]] = mapped_column(Integer)
    records_updated: Mapped[Optional[int]] = mapped_column(Integer)
    error_details: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
