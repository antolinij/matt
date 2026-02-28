"""Pytest configuration and fixtures"""

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.db.models import User
from app.main import app

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# Override dependency
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Setup database tables for the entire test session"""
    app.dependency_overrides[get_db] = override_get_db

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


@pytest.fixture(scope="session", autouse=True)
def app_with_override_cleanup():
    """Ensure app is properly cleaned up after all tests"""
    from app.main import app

    yield

    # Clean up after all tests complete
    app.dependency_overrides.clear()


# Add more shared fixtures here as needed
# For example:
# - Database session fixtures
# - Mock repository fixtures
# - Test data factories


@pytest_asyncio.fixture(scope="function", autouse=True)
async def close_event_service_pool():
    """Ensure Redis pool from event service is closed between tests."""
    yield
    from app.services.event_service import event_service

    await event_service.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def close_cache_service():
    """Ensure Redis pool from cache service is closed between tests."""
    yield
    from app.core.cache import cache_service

    await cache_service.close()
    # Reset the Redis client to None so next test gets a fresh connection
    cache_service._redis = None


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Provide a database session for tests"""
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def test_user(setup_test_database):
    """Create a test user for authentication - shared across all tests"""
    async with TestingSessionLocal() as session:
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("testpass123"),
            full_name="Test User",
            is_active=True,
            is_superuser=False,
            role="user",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture(scope="session")
async def auth_headers(test_user, setup_test_database):
    """Get authentication headers with JWT token - shared across all tests"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Login to get token
        response = await client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "testpass123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            raise Exception(f"Login failed: {response.status_code} - {response.text}")

        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(auth_headers):
    """Provide an authenticated AsyncClient for tests"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Add auth headers to all requests
        client.headers.update(auth_headers)
        yield client
