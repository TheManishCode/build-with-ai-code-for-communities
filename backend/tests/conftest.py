import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal  # noqa: E402


@pytest.fixture(scope="session")
def db():
    session = SessionLocal()
    yield session
    session.close()
