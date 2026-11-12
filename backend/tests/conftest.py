import time

import pytest

from config import Settings

ORIGIN = "http://localhost:5173"
EMAIL = "owner@example.com"
# Test-only credentials: they exist only inside a temporary database created for each test.
PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def settings(tmp_path):
    return Settings(
        secret_key="t" * 48,
        database_path=str(tmp_path / "test.db"),
        allowed_origins=(ORIGIN,),
    )
