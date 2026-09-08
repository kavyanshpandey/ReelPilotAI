import asyncio
import uuid

from httpx import ASGITransport, AsyncClient

from reelpilot.main import app
from reelpilot.security import get_current_user


def test_signup_login_me_and_protected_route() -> None:
    email = f"{uuid.uuid4()}@example.com"
    original = app.dependency_overrides.pop(get_current_user, None)

    async def flow():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            signup = await client.post(
                "/v1/auth/signup",
                json={
                    "email": email,
                    "password": "secure-password",
                    "display_name": "New Creator",
                    "workspace_name": "New Creator Studio",
                },
            )
            login = await client.post(
                "/v1/auth/login", json={"email": email, "password": "secure-password"}
            )
            token = login.json()["access_token"]
            me = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            protected = await client.post(
                "/v1/analysis-runs",
                json={"import_id": "missing"},
                headers={"Authorization": f"Bearer {token}"},
            )
            return signup, login, me, protected

    try:
        signup, login, me, protected = asyncio.run(flow())
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original

    assert signup.status_code == 201
    assert login.status_code == 200
    assert me.status_code == 200
    assert me.json()["workspace_name"] == "New Creator Studio"
    assert protected.status_code == 404


def test_protected_endpoint_requires_authentication() -> None:
    original = app.dependency_overrides.pop(get_current_user, None)

    async def request():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/v1/usage")

    try:
        response = asyncio.run(request())
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original

    assert response.status_code == 401
