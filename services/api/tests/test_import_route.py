import asyncio

from httpx import ASGITransport, AsyncClient

from reelpilot.main import app


def test_uploads_comments_csv() -> None:
    async def upload():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/v1/imports/comments-csv",
                files={"file": ("comments.csv", b"username,text\nneha,Camera kaunsa hai?\n")},
            )

    response = asyncio.run(upload())

    assert response.status_code == 200
    assert response.json()["imported_count"] == 1
    assert response.json()["comments"][0]["text"] == "Camera kaunsa hai?"


def test_rejects_non_csv_upload() -> None:
    async def upload():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/v1/imports/comments-csv",
                files={"file": ("comments.txt", b"text\nQuestion?\n")},
            )

    response = asyncio.run(upload())

    assert response.status_code == 415
    assert response.json()["detail"] == "Upload a .csv file"
