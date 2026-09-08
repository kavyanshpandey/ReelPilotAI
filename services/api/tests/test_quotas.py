import asyncio

from httpx import ASGITransport, AsyncClient

from reelpilot.config import Settings, get_settings
from reelpilot.database import SessionLocal
from reelpilot.limits import _check_memory
from reelpilot.main import app
from reelpilot.models import UsageCounter
from reelpilot.security import get_current_user


def test_comment_quota_returns_429_and_usage_reports_consumption() -> None:
    original = app.dependency_overrides.get(get_settings)
    user = app.dependency_overrides[get_current_user]()
    database = SessionLocal()
    database.query(UsageCounter).filter(UsageCounter.workspace_id == user.workspace_id).delete()
    database.commit()
    database.close()
    app.dependency_overrides[get_settings] = lambda: Settings(
        max_comments_per_month=1,
        max_analyses_per_month=1,
        max_generations_per_month=1,
    )

    async def flow():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post(
                "/v1/imports/comments-csv",
                files={"file": ("one.csv", b"text\nFirst question?\n")},
            )
            second = await client.post(
                "/v1/imports/comments-csv",
                files={"file": ("two.csv", b"text\nSecond question?\n")},
            )
            usage = await client.get("/v1/usage")
            return first, second, usage

    try:
        first, second, usage = asyncio.run(flow())
    finally:
        if original is None:
            app.dependency_overrides.pop(get_settings, None)
        else:
            app.dependency_overrides[get_settings] = original

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "Monthly comments limit of 1 reached"
    assert usage.status_code == 200
    assert usage.json()["comments"] == {"used": 1, "limit": 1, "remaining": 0}


def test_memory_rate_limiter_rejects_after_limit() -> None:
    key = ("rate-test", "imports")
    first, _ = _check_memory(key, window=60, limit=1)
    second, retry_after = _check_memory(key, window=60, limit=1)

    assert first is True
    assert second is False
    assert retry_after >= 1
