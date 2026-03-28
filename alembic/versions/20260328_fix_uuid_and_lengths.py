from alembic import op
import sqlalchemy as sa


revision = "20260328_fix_uuid_and_lengths"
down_revision = "20260328_duty_units"
branch_labels = None
depends_on = None


def _column_info(conn, *, schema: str, table: str, column: str) -> tuple[str | None, int | None]:
    row = conn.execute(
        sa.text(
            """
            SELECT data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = :schema
              AND table_name = :table
              AND column_name = :column
            """
        ),
        {"schema": schema, "table": table, "column": column},
    ).fetchone()
    if not row:
        return None, None
    return row[0], row[1]


def _ensure_uuid_pk(conn, *, schema: str, table: str) -> None:
    data_type, _ = _column_info(conn, schema=schema, table=table, column="id")
    if data_type and data_type != "uuid":
        op.execute(sa.text(f"ALTER TABLE {schema}.{table} ALTER COLUMN id TYPE uuid USING id::uuid"))


def _ensure_varchar_len(conn, *, schema: str, table: str, column: str, length: int) -> None:
    data_type, max_len = _column_info(conn, schema=schema, table=table, column=column)
    if data_type == "character varying" and max_len is not None and int(max_len) < int(length):
        op.execute(sa.text(f"ALTER TABLE {schema}.{table} ALTER COLUMN {column} TYPE varchar({int(length)})"))


def upgrade() -> None:
    conn = op.get_bind()
    _ensure_uuid_pk(conn, schema="ingestion", table="ingestion_runs")
    _ensure_uuid_pk(conn, schema="tariff", table="tariff_measures")
    _ensure_varchar_len(conn, schema="tariff", table="tariff_measures", column="source_measure_id", length=100)


def downgrade() -> None:
    conn = op.get_bind()

    data_type, _ = _column_info(conn, schema="ingestion", table="ingestion_runs", column="id")
    if data_type == "uuid":
        op.execute(
            sa.text(
                "ALTER TABLE ingestion.ingestion_runs ALTER COLUMN id TYPE varchar(32) USING replace(id::text, '-', '')"
            )
        )

    data_type, _ = _column_info(conn, schema="tariff", table="tariff_measures", column="id")
    if data_type == "uuid":
        op.execute(
            sa.text(
                "ALTER TABLE tariff.tariff_measures ALTER COLUMN id TYPE varchar(32) USING replace(id::text, '-', '')"
            )
        )

    data_type, max_len = _column_info(conn, schema="tariff", table="tariff_measures", column="source_measure_id")
    if data_type == "character varying" and max_len is not None and int(max_len) > 32:
        op.execute(sa.text("ALTER TABLE tariff.tariff_measures ALTER COLUMN source_measure_id TYPE varchar(32) USING left(source_measure_id, 32)"))
