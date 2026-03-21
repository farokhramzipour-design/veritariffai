"""Add calculations.calculation_profiles table

Revision ID: 20260321_calculation_profiles
Revises: 20260224_initial_schema
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260321_calculation_profiles"
down_revision = "20260224_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calculation_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("shipment_data", postgresql.JSONB(), nullable=False),
        sa.Column("lines_data", postgresql.JSONB(), nullable=False),
        sa.Column("last_result", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="calculations",
    )

    op.create_index(
        "idx_calc_profiles_user_id",
        "calculation_profiles",
        ["user_id"],
        schema="calculations",
    )
    op.create_index(
        "idx_calc_profiles_updated_at",
        "calculation_profiles",
        ["updated_at"],
        schema="calculations",
    )


def downgrade() -> None:
    op.drop_index("idx_calc_profiles_updated_at", table_name="calculation_profiles", schema="calculations")
    op.drop_index("idx_calc_profiles_user_id", table_name="calculation_profiles", schema="calculations")
    op.drop_table("calculation_profiles", schema="calculations")
