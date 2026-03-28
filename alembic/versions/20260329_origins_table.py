from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260329_origins_table"
down_revision = "20260328_fix_uuid_and_lengths"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "origins",
        sa.Column("origin_code", sa.String(length=10), primary_key=True),
        sa.Column("origin_name", sa.Text(), nullable=False),
        sa.Column("origin_code_type", sa.String(length=20), nullable=False),
        sa.Column("iso2", sa.String(length=2), nullable=True),
        sa.Column("iso3", sa.String(length=3), nullable=True),
        sa.Column("is_eu_member", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_erga_omnes", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_group", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("member_iso2_codes", postgresql.ARRAY(sa.String(length=2)), nullable=True),
        sa.Column("group_category", sa.String(length=30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="tariff",
    )
    op.create_index("idx_origins_iso2", "origins", ["iso2"], schema="tariff")
    op.create_index("idx_origins_code_type", "origins", ["origin_code_type"], schema="tariff")
    op.create_index("idx_origins_group_cat", "origins", ["group_category"], schema="tariff")

    op.alter_column(
        "tariff_measures",
        "country_of_origin",
        existing_type=sa.String(length=5),
        type_=sa.String(length=10),
        schema="tariff",
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "tariff_measures",
        "country_of_origin",
        existing_type=sa.String(length=10),
        type_=sa.String(length=5),
        schema="tariff",
        existing_nullable=True,
    )

    op.drop_index("idx_origins_group_cat", table_name="origins", schema="tariff")
    op.drop_index("idx_origins_code_type", table_name="origins", schema="tariff")
    op.drop_index("idx_origins_iso2", table_name="origins", schema="tariff")
    op.drop_table("origins", schema="tariff")

