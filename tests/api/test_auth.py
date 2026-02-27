"""
Authentication Tests

Tests for user registration, login, token refresh, and protected endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_register_user():
    """Test user registration"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "testpassword123",
                "full_name": "New User"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "id" in data
        assert "hashed_password" not in data  # Password should not be in response


@pytest.mark.asyncio
async def test_register_duplicate_username():
    """Test registering with duplicate username"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register first user
        await client.post(
            "/api/auth/register",
            json={
                "username": "duplicate",
                "email": "unique@example.com",
                "password": "password123"
            }
        )

        # Try to register with same username
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "duplicate",
                "email": "different@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "Duplicate Record"
        assert data["field"] == "username"


@pytest.mark.asyncio
async def test_register_duplicate_email():
    """Test registering with duplicate email"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register first user
        await client.post(
            "/api/auth/register",
            json={
                "username": "user1",
                "email": "duplicate@example.com",
                "password": "password123"
            }
        )

        # Try to register with same email
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "user2",
                "email": "duplicate@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "Duplicate Record"
        assert data["field"] == "email"


@pytest.mark.asyncio
async def test_login_success():
    """Test successful login"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register user
        await client.post(
            "/api/auth/register",
            json={
                "username": "loginuser",
                "email": "login@example.com",
                "password": "loginpassword123"
            }
        )

        # Login
        response = await client.post(
            "/api/auth/login",
            data={  # Note: OAuth2PasswordRequestForm uses form data, not JSON
                "username": "loginuser",
                "password": "loginpassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_with_email():
    """Test login with email instead of username"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register user
        await client.post(
            "/api/auth/register",
            json={
                "username": "emailuser",
                "email": "emaillogin@example.com",
                "password": "emailpassword123"
            }
        )

        # Login with email
        response = await client.post(
            "/api/auth/login",
            data={
                "username": "emaillogin@example.com",  # Can use email as username
                "password": "emailpassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password():
    """Test login with incorrect password"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register user
        await client.post(
            "/api/auth/register",
            json={
                "username": "wrongpassuser",
                "email": "wrongpass@example.com",
                "password": "correctpassword"
            }
        )

        # Login with wrong password
        response = await client.post(
            "/api/auth/login",
            data={
                "username": "wrongpassuser",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user():
    """Test login with nonexistent user"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent",
                "password": "password123"
            }
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_access_protected_route():
    """Test accessing protected route with valid token"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register and login
        await client.post(
            "/api/auth/register",
            json={
                "username": "protecteduser",
                "email": "protected@example.com",
                "password": "password123"
            }
        )

        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": "protecteduser",
                "password": "password123"
            }
        )
        access_token = login_response.json()["access_token"]

        # Access protected route
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "protecteduser"
        assert data["email"] == "protected@example.com"


@pytest.mark.asyncio
async def test_access_protected_route_without_token():
    """Test accessing protected route without token"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/auth/me")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_access_protected_route_invalid_token():
    """Test accessing protected route with invalid token"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token():
    """Test refreshing access token"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register and login
        await client.post(
            "/api/auth/register",
            json={
                "username": "refreshuser",
                "email": "refresh@example.com",
                "password": "password123"
            }
        )

        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": "refreshuser",
                "password": "password123"
            }
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails():
    """Test that access token cannot be used for refresh"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register and login
        await client.post(
            "/api/auth/register",
            json={
                "username": "wrongtokenuser",
                "email": "wrongtoken@example.com",
                "password": "password123"
            }
        )

        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": "wrongtokenuser",
                "password": "password123"
            }
        )
        access_token = login_response.json()["access_token"]

        # Try to refresh with access token (should fail)
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": access_token}
        )
        assert response.status_code == 401
        assert "Invalid token type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_logout():
    """Test logout endpoint"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register and login
        await client.post(
            "/api/auth/register",
            json={
                "username": "logoutuser",
                "email": "logout@example.com",
                "password": "password123"
            }
        )

        login_response = await client.post(
            "/api/auth/login",
            data={
                "username": "logoutuser",
                "password": "password123"
            }
        )
        access_token = login_response.json()["access_token"]

        # Logout
        response = await client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]
