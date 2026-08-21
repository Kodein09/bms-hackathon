from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base, get_db
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
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
        },
    )
    assert registration.status_code == 201
    assert registration.json()["username"] == "test_user"
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
