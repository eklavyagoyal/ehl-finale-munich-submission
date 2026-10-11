"""Test setup: a separate Postgres database (parallax_test), mock LLM mode, synthetic fixtures only."""

import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

os.environ.update({
    "PARALLAX_DATABASE_URL": os.environ.get("PARALLAX_TEST_DATABASE_URL",
                                            "postgresql+psycopg://parallax@localhost:5433/parallax_test"),
    "PARALLAX_LLM_MODE": "mock",
    "PARALLAX_PERSONA_ENGINE": "direct",
    "PARALLAX_RESEARCH_ROOT": str(FIXTURES / "research"),
    # Synthetic fixtures are pending/accepted mixes; nothing leaves the machine in mock mode.
    "PARALLAX_ALLOW_UNREVIEWED_EVIDENCE_FOR_LLM": "true",
})


def _database_available() -> bool:
    from sqlalchemy import text

    from parallax.db import get_engine

    try:
        with get_engine().connect() as connection:
            connection.execute(text("select 1"))
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def database():
    if not _database_available():
        pytest.skip("Postgres test database not reachable (run scripts/db.sh init)")
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from parallax.config import BACKEND_ROOT
    from parallax.db import get_engine

    with get_engine().begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
    yield


@pytest.fixture(scope="session")
def client(database):
    from fastapi.testclient import TestClient

    from parallax.api.app import app

    return TestClient(app, headers={"X-Actor": "pm:test"})
