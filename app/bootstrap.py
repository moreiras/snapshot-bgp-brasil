"""Helpers to bootstrap the database with the provided schema."""
from __future__ import annotations

from pathlib import Path
from sqlalchemy import text

from app.config import get_settings
from app.db import db_session, execute_sql_file


def initialize_database() -> None:
    """Create schema objects if they do not exist."""
    settings = get_settings()
    schema_path = Path(settings.schema_file)
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    execute_sql_file(str(schema_path))


def ensure_snapshot(logical_date: str, description: str | None = None) -> int:
    """Ensure a snapshot row exists for the provided logical date."""
    with db_session() as conn:
        result = conn.execute(
            text(
                """
                SELECT snapshot_id
                FROM snapshot
                WHERE logical_date = :logical_date
                ORDER BY snapshot_id DESC
                LIMIT 1
                """
            ),
            {"logical_date": logical_date},
        ).scalar()
        if result is not None:
            return int(result)

        new_id = conn.execute(
            text(
                """
                INSERT INTO snapshot (collected_at, logical_date, description)
                VALUES (NOW(), :logical_date, :description)
                RETURNING snapshot_id
                """
            ),
            {"logical_date": logical_date, "description": description or "Automatic snapshot"},
        ).scalar_one()
        return int(new_id)
