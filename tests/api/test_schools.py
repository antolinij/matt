import pytest


@pytest.mark.asyncio
async def test_create_school(authenticated_client):
    """Test creating a school"""
    response = await authenticated_client.post(
        "/api/schools/",
        json={
            "name": "Test School",
            "address": "123 Test St",
            "phone": "+1234567890",
            "email": "test@school.com"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test School"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_schools(authenticated_client):
    """Test listing schools"""
    response = await authenticated_client.get("/api/schools/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_school_by_id(authenticated_client):
    """Test getting a specific school"""
    # First create a school
    create_response = await authenticated_client.post(
        "/api/schools/",
        json={"name": "Another School"}
    )
    school_id = create_response.json()["id"]

    # Then retrieve it
    response = await authenticated_client.get(f"/api/schools/{school_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Another School"


@pytest.mark.asyncio
async def test_update_school(authenticated_client):
    """Test updating a school"""
    # Create a school
    create_response = await authenticated_client.post(
        "/api/schools/",
        json={"name": "Original Name"}
    )
    school_id = create_response.json()["id"]

    # Update it
    response = await authenticated_client.put(
        f"/api/schools/{school_id}",
        json={"name": "Updated Name"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_delete_school(authenticated_client):
    """Test deleting a school"""
    # Create a school
    create_response = await authenticated_client.post(
        "/api/schools/",
        json={"name": "To Be Deleted"}
    )
    school_id = create_response.json()["id"]

    # Delete it
    response = await authenticated_client.delete(f"/api/schools/{school_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_response = await authenticated_client.get(f"/api/schools/{school_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_school_not_found(authenticated_client):
    """Test getting non-existent school"""
    response = await authenticated_client.get("/api/schools/999999")
    assert response.status_code == 404
