"""Alembic migrations must build exactly the schema the models describe."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.config import settings
from app.database import Base

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_migrations_match_models(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(config, "head")

    engine = create_engine(url)
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert diff == []

    command.downgrade(config, "base")
