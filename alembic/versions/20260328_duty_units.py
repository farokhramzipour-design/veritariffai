from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260328_duty_units"
down_revision = "20260328_certificate_codes_and_pipeline_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "duty_units",
        sa.Column("code", sa.String(length=10), primary_key=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=True),
        sa.Column("base_si_unit", sa.String(length=10), nullable=True),
        sa.Column("conversion_to_si", postgresql.NUMERIC(18, 8), nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="tariff",
    )


def downgrade() -> None:
    op.drop_table("duty_units", schema="tariff")

