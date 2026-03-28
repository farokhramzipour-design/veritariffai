from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260328_certificate_codes_and_pipeline_config"
down_revision = "20260328_vat_rates_and_raw_json"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "certificate_codes",
        sa.Column("code", sa.String(length=10), primary_key=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="tariff",
    )
    op.create_table(
        "pipeline_config",
        sa.Column("key", sa.String(length=50), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="tariff",
    )


def downgrade() -> None:
    op.drop_table("pipeline_config", schema="tariff")
    op.drop_table("certificate_codes", schema="tariff")

