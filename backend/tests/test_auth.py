from collections.abc import AsyncGenerator
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
import pytest_asyncio
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base, get_db
from app.main import app
from app.core.config import settings


@pytest_asyncio.fixture
async def client(tmp_path: Path) -> AsyncGenerator[AsyncClient, None]:
    original_upload_dir = settings.upload_dir
    settings.upload_dir = str(tmp_path / "uploads")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
    settings.upload_dir = original_upload_dir
    await engine.dispose()


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_auth_flow(client: AsyncClient) -> None:
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "test_user",
            "email": "test@example.com",
            "password": "strong-pass-123",
            "full_name": "Тестовый Пользователь",
            "position": "Backend Developer",
        },
    )
    assert registration.status_code == 201
    assert registration.json()["username"] == "test_user"
    assert registration.json()["full_name"] == "Тестовый Пользователь"
    assert registration.json()["position"] == "Backend Developer"
    assert "hashed_password" not in registration.json()

    duplicate = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "test_user",
            "email": "another@example.com",
            "password": "strong-pass-123",
        },
    )
    assert duplicate.status_code == 409

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "test_user", "password": "strong-pass-123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert set(tokens) == {"access_token", "refresh_token", "token_type"}

    profile = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["email"] == "test@example.com"

    refreshed = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "secure_user",
            "email": "secure@example.com",
            "password": "strong-pass-123",
        },
    )

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "secure_user", "password": "wrong-password"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_notifications_flow(client: AsyncClient) -> None:
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "notification_user",
            "email": "notification@example.com",
            "password": "strong-pass-123",
        },
    )
    user_id = registration.json()["id"]
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "notification_user", "password": "strong-pass-123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post(
        "/api/v1/notifications/",
        headers=headers,
        json={
            "user_id": user_id,
            "title": "Document ready",
            "message": "Your document was processed.",
            "type": "success",
        },
    )
    assert created.status_code == 201
    notification_id = created.json()["id"]

    listed = await client.get("/api/v1/notifications/", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["unread_count"] == 1
    assert len(listed.json()["items"]) == 1

    marked = await client.put(
        f"/api/v1/notifications/{notification_id}/read",
        headers=headers,
    )
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True

    count = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert count.json() == {"unread_count": 0}


PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0dIDAT\x08\xd7c\xf8\xcf\xc0"
    b"\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
)
PDF_MINIMAL = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def office_fixture(kind: str) -> bytes:
    marker = {
        "docx": "wordprocessingml",
        "xlsx": "spreadsheetml",
        "pptx": "presentationml",
    }[kind]
    stream = BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", f"<Types><Default ContentType=\"{marker}\"/></Types>")
    return stream.getvalue()


async def create_test_user(client: AsyncClient, username: str = "document_user") -> tuple[str, str]:
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "strong-pass-123",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "strong-pass-123"},
    )
    return registration.json()["id"], login.json()["access_token"]


@pytest.mark.asyncio
async def test_document_upload_list_and_download(client: AsyncClient) -> None:
    user_id, token = await create_test_user(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files=[
            ("files", ("photo.png", PNG_1X1, "image/png")),
            ("files", ("report.pdf", PDF_MINIMAL, "application/pdf")),
        ],
    )

    assert response.status_code == 200
    results = response.json()
    print(results)
    assert [result["success"] for result in results] == [True, True]
    document_id = results[0]["document"]["id"]

    listed = await client.get("/api/v1/documents/", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 2
    assert listed.json()[0]["user_id"] == user_id

    downloaded = await client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == PNG_1X1
    assert "photo.png" in downloaded.headers["content-disposition"]

    deleted = await client.delete(f"/api/v1/documents/{document_id}", headers=headers)
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/documents/{document_id}", headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_document_upload_rejects_unsupported_and_fake_mime(client: AsyncClient) -> None:
    _, token = await create_test_user(client, "validation_user")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files=[
            ("files", ("virus.exe", b"MZ\x90\x00", "application/octet-stream")),
            ("files", ("renamed.txt", PNG_1X1, "text/plain")),
        ],
    )

    assert response.status_code == 200
    results = response.json()
    assert results[0]["success"] is False
    assert "не поддерживается" in results[0]["error"]
    assert results[1]["success"] is False
    assert "MIME" in results[1]["error"]


@pytest.mark.asyncio
async def test_document_upload_rejects_oversized_file(client: AsyncClient) -> None:
    _, token = await create_test_user(client, "large_file_user")
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files=[("files", ("large.txt", b"a" * (52_428_800 + 1), "text/plain"))],
    )

    assert response.status_code == 200
    assert response.json()[0]["success"] is False
    assert "слишком большой" in response.json()[0]["error"]


@pytest.mark.asyncio
async def test_docx_zip_container_is_detected_by_internal_type(client: AsyncClient) -> None:
    _, token = await create_test_user(client, "office_user")
    response = await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=[("files", ("contract.docx", office_fixture("docx"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
    )

    assert response.status_code == 200
    assert response.json()[0]["success"] is True
    assert response.json()[0]["document"]["mime_type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
