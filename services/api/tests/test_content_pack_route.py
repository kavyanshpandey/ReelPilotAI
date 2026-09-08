import asyncio

from httpx import ASGITransport, AsyncClient

from reelpilot.main import app


def test_generates_edits_and_versions_content_pack() -> None:
    content = (
        b"username,comment,likes\n"
        b"neha,What was the total trip budget?,8\n"
        b"rohan,Kitna kharcha hua Ladakh mein?,4\n"
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
            cluster_id = analysis.json()["clusters"][0]["id"]
            first_pack = await client.post(
                f"/v1/clusters/{cluster_id}/content-packs",
                json={"language": "Hinglish", "tone": "Conversational"},
            )
            edited_pack = await client.patch(
                f"/v1/content-packs/{first_pack.json()['id']}",
                json={"cover_text": "Real Ladakh Budget"},
            )
            second_pack = await client.post(
                f"/v1/clusters/{cluster_id}/content-packs",
                json={"language": "English", "tone": "Educational"},
            )
            return first_pack, edited_pack, second_pack

    first_pack, edited_pack, second_pack = asyncio.run(run_flow())

    assert first_pack.status_code == 201
    assert first_pack.json()["provider"] == "local"
    assert len(first_pack.json()["hooks"]) == 3
    assert edited_pack.status_code == 200
    assert edited_pack.json()["cover_text"] == "Real Ladakh Budget"
    assert second_pack.status_code == 201
    assert second_pack.json()["version"] == 2
    assert second_pack.json()["language"] == "English"


def test_rejects_unknown_cluster() -> None:
    async def generate():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/v1/clusters/missing/content-packs",
                json={"language": "English", "tone": "Educational"},
            )

    response = asyncio.run(generate())

    assert response.status_code == 404
