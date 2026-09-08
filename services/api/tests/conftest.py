import os

# Tests must never create or drop tables in the developer's application database.
os.environ["APP_DATABASE_URL"] = "sqlite:///./test_reelpilot.db"

import pytest

from reelpilot.config import Settings, get_settings
from reelpilot.database import Base, SessionLocal, create_tables, engine
from reelpilot.main import app
from reelpilot.models import User, Workspace
from reelpilot.security import get_current_user, hash_password


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    create_tables()
    database = SessionLocal()
    workspace = Workspace(name="Test workspace")
    user = User(
        email="test@example.com",
        password_hash=hash_password("password123"),
        display_name="Test User",
        workspace=workspace,
    )
    database.add(user)
    database.commit()
    database.refresh(user)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_settings] = lambda: Settings(
        embedding_provider="local", generation_provider="local"
    )
    yield
    app.dependency_overrides.clear()
    database.close()
    Base.metadata.drop_all(bind=engine)
