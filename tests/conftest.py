import os
from pathlib import Path
import sys

import pytest_asyncio


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////private/tmp/fraud_detection_test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

TEST_DB = Path("/private/tmp/fraud_detection_test.db")
if TEST_DB.exists():
    TEST_DB.unlink()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_database():
    from backend.utils.database import close_db, init_db

    await init_db()
    yield
    await close_db()
