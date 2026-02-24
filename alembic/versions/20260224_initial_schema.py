from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260224_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS identity")
    op.execute("CREATE SCHEMA IF NOT EXISTS subscriptions")
    op.execute("CREATE SCHEMA IF NOT EXISTS calculations")
    op.execute("CREATE SCHEMA IF NOT EXISTS tariff")
    op.execute("CREATE SCHEMA IF NOT EXISTS fx")
    op.execute("CREATE SCHEMA IF NOT EXISTS compliance")
    op.execute("CREATE SCHEMA IF NOT EXISTS ingestion")

    # identity.users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("google_sub", sa.String(length=255), nullable=False, unique=True),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("plan", sa.String(length=20), nullable=False, server_default="free"),
        sa.Column("plan_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True, unique=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        schema="identity",
    )
    op.create_index("idx_users_google_sub", "users", ["google_sub"], unique=False, schema="identity")
    op.create_index("idx_users_email", "users", ["email"], unique=False, schema="identity")
    op.create_index("idx_users_stripe_customer_id", "users", ["stripe_customer_id"], unique=False, schema="identity")

    # subscriptions.subscription_events
    op.create_table(
        "subscription_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("from_plan", sa.String(length=20), nullable=True),
        sa.Column("to_plan", sa.String(length=20), nullable=True),
        sa.Column("stripe_event_id", sa.String(length=255), nullable=True, unique=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="subscriptions",
    )

    # calculations.calculation_requests
    op.create_table(
        "calculation_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("plan_snapshot", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("shipment_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("lines_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requested_engines", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        schema="calculations",
    )
    op.create_index("idx_calc_requests_user_id", "calculation_requests", ["user_id"], schema="calculations")
    op.create_index("idx_calc_requests_status", "calculation_requests", ["status"], schema="calculations")
    op.create_index("idx_calc_requests_created_at", "calculation_requests", ["created_at"], schema="calculations")

    # calculations.calculation_results
    op.create_table(
        "calculation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calculations.calculation_requests.id"), unique=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=False),
        sa.Column("line_results", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("engine_results", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("totals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("audit_trail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence_score", postgresql.NUMERIC(4, 3), nullable=False),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="calculations",
    )
    op.create_index("idx_calc_results_user_id", "calculation_results", ["user_id"], schema="calculations")
    op.create_index("idx_calc_results_created_at", "calculation_results", ["created_at"], schema="calculations")

    # tariff.hs_codes
    op.create_table(
        "hs_codes",
        sa.Column("code", sa.String(length=12), primary_key=True),
        sa.Column("jurisdiction", sa.String(length=5), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("parent_code", sa.String(length=12), sa.ForeignKey("tariff.hs_codes.code"), nullable=True),
        sa.Column("level", sa.SmallInteger(), nullable=False),
        sa.Column("supplementary_unit", sa.String(length=50), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        schema="tariff",
    )

    # tariff.tariff_quotas
    op.create_table(
        "tariff_quotas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quota_order_number", sa.String(length=20), unique=True, nullable=False),
        sa.Column("jurisdiction", sa.String(length=5), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("volume", postgresql.NUMERIC(18, 4), nullable=False),
        sa.Column("volume_unit", sa.String(length=20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("balance", postgresql.NUMERIC(18, 4), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
        schema="tariff",
    )

    # tariff.tariff_measures
    op.create_table(
        "tariff_measures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hs_code", sa.String(length=12), sa.ForeignKey("tariff.hs_codes.code"), nullable=False),
        sa.Column("jurisdiction", sa.String(length=5), nullable=False),
        sa.Column("measure_type", sa.String(length=50), nullable=False),
        sa.Column("country_of_origin", sa.String(length=5), nullable=True),
        sa.Column("preferential_agreement", sa.String(length=100), nullable=True),
        sa.Column("rate_ad_valorem", postgresql.NUMERIC(8, 4), nullable=True),
        sa.Column("rate_specific_amount", postgresql.NUMERIC(14, 4), nullable=True),
        sa.Column("rate_specific_unit", sa.String(length=50), nullable=True),
        sa.Column("rate_minimum", postgresql.NUMERIC(14, 4), nullable=True),
        sa.Column("rate_maximum", postgresql.NUMERIC(14, 4), nullable=True),
        sa.Column("agricultural_component", postgresql.NUMERIC(14, 4), nullable=True),
        sa.Column("quota_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tariff.tariff_quotas.id"), nullable=True),
        sa.Column("suspension", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("measure_condition", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("source_dataset", sa.String(length=20), nullable=False),
        sa.Column("source_measure_id", sa.String(length=100), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="tariff",
    )
    op.create_index("idx_tariff_measures_hs_code", "tariff_measures", ["hs_code"], schema="tariff")
    op.create_index(
        "idx_tariff_measures_lookup",
        "tariff_measures",
        ["hs_code", "jurisdiction", "country_of_origin", "valid_from", "valid_to"],
        schema="tariff",
    )
    op.create_index("idx_tariff_measures_valid", "tariff_measures", ["valid_to"], schema="tariff")

    # tariff.origin_rules
    op.create_table(
        "origin_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agreement", sa.String(length=100), nullable=False),
        sa.Column("hs_code_start", sa.String(length=12), nullable=False),
        sa.Column("hs_code_end", sa.String(length=12), nullable=False),
        sa.Column("rule_type", sa.String(length=30), nullable=False),
        sa.Column("rvc_threshold", postgresql.NUMERIC(5, 2), nullable=True),
        sa.Column("rule_text", sa.Text(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        schema="tariff",
    )

    # fx.fx_rates
    op.create_table(
        "fx_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("quote_currency", sa.String(length=3), nullable=False),
        sa.Column("rate", postgresql.NUMERIC(18, 8), nullable=False),
        sa.Column("rate_type", sa.String(length=20), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="fx",
    )
    op.create_index(
        "uq_fx_rates_unique",
        "fx_rates",
        ["base_currency", "quote_currency", "rate_type", "effective_date"],
        unique=True,
        schema="fx",
    )
    op.create_index(
        "idx_fx_rates_lookup",
        "fx_rates",
        ["base_currency", "quote_currency", "rate_type", sa.text("effective_date DESC")],
        schema="fx",
    )

    # compliance.restricted_goods
    op.create_table(
        "restricted_goods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hs_code_pattern", sa.String(length=12), nullable=False),
        sa.Column("jurisdiction", sa.String(length=5), nullable=False),
        sa.Column("restriction_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("license_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("certificate_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("outright_prohibited", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        schema="compliance",
    )

    # compliance.sanctions
    op.create_table(
        "sanctions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("jurisdiction", sa.String(length=5), nullable=False),
        sa.Column("sanction_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("hs_code_scope", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        schema="compliance",
    )

    # ingestion.ingestion_runs
    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("records_processed", sa.Integer(), nullable=True),
        sa.Column("records_inserted", sa.Integer(), nullable=True),
        sa.Column("records_updated", sa.Integer(), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        schema="ingestion",
    )


def downgrade() -> None:
    op.drop_table("ingestion_runs", schema="ingestion")
    op.drop_table("sanctions", schema="compliance")
    op.drop_table("restricted_goods", schema="compliance")
    op.drop_index("idx_fx_rates_lookup", table_name="fx_rates", schema="fx")
    op.drop_index("uq_fx_rates_unique", table_name="fx_rates", schema="fx")
    op.drop_table("fx_rates", schema="fx")
    op.drop_table("origin_rules", schema="tariff")
    op.drop_index("idx_tariff_measures_valid", table_name="tariff_measures", schema="tariff")
    op.drop_index("idx_tariff_measures_lookup", table_name="tariff_measures", schema="tariff")
    op.drop_index("idx_tariff_measures_hs_code", table_name="tariff_measures", schema="tariff")
    op.drop_table("tariff_measures", schema="tariff")
    op.drop_table("tariff_quotas", schema="tariff")
    op.drop_table("hs_codes", schema="tariff")
    op.drop_index("idx_calc_results_created_at", table_name="calculation_results", schema="calculations")
    op.drop_index("idx_calc_results_user_id", table_name="calculation_results", schema="calculations")
    op.drop_table("calculation_results", schema="calculations")
    op.drop_index("idx_calc_requests_created_at", table_name="calculation_requests", schema="calculations")
    op.drop_index("idx_calc_requests_status", table_name="calculation_requests", schema="calculations")
    op.drop_index("idx_calc_requests_user_id", table_name="calculation_requests", schema="calculations")
    op.drop_table("calculation_requests", schema="calculations")
    op.drop_table("subscription_events", schema="subscriptions")
    op.drop_index("idx_users_stripe_customer_id", table_name="users", schema="identity")
    op.drop_index("idx_users_email", table_name="users", schema="identity")
    op.drop_index("idx_users_google_sub", table_name="users", schema="identity")
    op.drop_table("users", schema="identity")
    op.execute("DROP SCHEMA IF EXISTS ingestion CASCADE")
    op.execute("DROP SCHEMA IF EXISTS compliance CASCADE")
    op.execute("DROP SCHEMA IF EXISTS fx CASCADE")
    op.execute("DROP SCHEMA IF EXISTS tariff CASCADE")
    op.execute("DROP SCHEMA IF EXISTS calculations CASCADE")
    op.execute("DROP SCHEMA IF EXISTS subscriptions CASCADE")
    op.execute("DROP SCHEMA IF EXISTS identity CASCADE")
