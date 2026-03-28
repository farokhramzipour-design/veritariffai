"""Add tariff.vat_rates table and raw_json storage for tariff measures

Revision ID: 20260328_vat_rates_and_raw_json
Revises: 20260321_calculation_profiles
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260328_vat_rates_and_raw_json"
down_revision = "20260321_calculation_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tariff_measures",
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="tariff",
    )
    op.create_index(
        "uq_tariff_measures_source_id",
        "tariff_measures",
        ["source_dataset", "source_measure_id"],
        unique=True,
        schema="tariff",
        postgresql_where=sa.text("source_measure_id IS NOT NULL"),
    )

    op.create_table(
        "vat_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("jurisdiction", sa.String(length=5), nullable=False),
        sa.Column("rate_type", sa.String(length=20), nullable=False),
        sa.Column("vat_rate", postgresql.NUMERIC(6, 3), nullable=False),
        sa.Column("hs_code_prefix", sa.String(length=6), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="tariff",
    )
    op.create_index(
        "idx_vat_rates_country",
        "vat_rates",
        ["country_code"],
        unique=False,
        schema="tariff",
    )
    op.create_index(
        "idx_vat_rates_lookup",
        "vat_rates",
        ["country_code", "jurisdiction", "hs_code_prefix"],
        unique=False,
        schema="tariff",
    )
    op.create_index(
        "uq_vat_rates_unique",
        "vat_rates",
        [
            "country_code",
            "jurisdiction",
            "rate_type",
            sa.text("COALESCE(hs_code_prefix, '')"),
            sa.text("COALESCE(valid_from, '0001-01-01'::date)"),
        ],
        unique=True,
        schema="tariff",
    )


def downgrade() -> None:
    op.drop_index("uq_vat_rates_unique", table_name="vat_rates", schema="tariff")
    op.drop_index("idx_vat_rates_lookup", table_name="vat_rates", schema="tariff")
    op.drop_index("idx_vat_rates_country", table_name="vat_rates", schema="tariff")
    op.drop_table("vat_rates", schema="tariff")

    op.drop_index("uq_tariff_measures_source_id", table_name="tariff_measures", schema="tariff")
    op.drop_column("tariff_measures", "raw_json", schema="tariff")

