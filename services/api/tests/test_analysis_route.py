import asyncio

from httpx import ASGITransport, AsyncClient

from reelpilot.main import app


def test_import_then_analyse_comments() -> None:
    content = (
        b"username,comment,created_at,likes\n"
        b"neha,What was the total trip budget?,2026-08-20,8\n"
        b"rohan,Kitna kharcha hua Ladakh mein?,2026-08-21,4\n"
        b"sam,Which camera did you use?,2026-08-22,7\n"
        b"riya,Camera settings share karoge?,2026-08-23,3\n"
    )

    async def run_flow():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            imported = await client.post(
                "/v1/imports/comments-csv",
                files={"file": ("comments.csv", content)},
            )
            analysis = await client.post(
                "/v1/analysis-runs",
                json={"import_id": imported.json()["import_id"]},
            )
            return imported, analysis

    imported, analysis = asyncio.run(run_flow())

    assert imported.status_code == 200
    assert analysis.status_code == 201
    payload = analysis.json()
    assert payload["status"] == "completed"
    assert payload["provider"] == "local"
    assert payload["comment_count"] == 4
    assert len(payload["clusters"]) == 2
    assert {cluster["label"] for cluster in payload["clusters"]} == {
        "Trip budget & costs",
        "Camera & editing setup",
    }
    assert all(cluster["mention_count"] == 2 for cluster in payload["clusters"])


def test_unknown_import_returns_not_found() -> None:
    async def create_analysis():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/v1/analysis-runs", json={"import_id": "missing"})

    response = asyncio.run(create_analysis())

    assert response.status_code == 404
