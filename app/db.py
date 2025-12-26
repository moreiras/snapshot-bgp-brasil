"""Database helpers using SQLAlchemy Core."""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings


_settings = get_settings()
_engine: Engine | None = None


def get_engine() -> Engine:
    """Create (or reuse) the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(_settings.database_url, future=True)
    return _engine


@contextmanager
def db_session():
    """Context manager yielding a database connection."""
    engine = get_engine()
    connection = engine.connect()
    transaction = connection.begin()
    try:
        yield connection
        transaction.commit()
    except SQLAlchemyError:
        transaction.rollback()
        raise
    finally:
        connection.close()


def execute_sql_file(path: str) -> None:
    """Execute a raw SQL file against the database."""
    with open(path, "r", encoding="utf-8") as handle:
        sql = handle.read()
    with db_session() as conn:
        for statement in filter(None, sql.split(";")):
            conn.execute(text(statement))
