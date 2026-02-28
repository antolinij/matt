"""
Tests for Global Exception Handlers

Tests that FastAPI global exception handlers return correct HTTP responses.
"""

import time

import pytest


class TestDuplicateRecordExceptionHandler:
    """Tests for DuplicateRecordException handler (409 Conflict)"""

    @pytest.mark.asyncio
    async def test_duplicate_username_returns_409(self, authenticated_client):
        """Test that duplicate username returns 409 with proper error message"""
        unique_id = str(int(time.time() * 1000000))[
            -10:
        ]  # Use timestamp for uniqueness

        # Create first user
        response1 = await authenticated_client.post(
            "/api/auth/register",
            json={
                "username": f"duplicate{unique_id}",
                "email": f"user1{unique_id}@example.com",
                "password": "password123",
            },
        )
        assert response1.status_code == 201

        # Try to create second user with same username
        response2 = await authenticated_client.post(
            "/api/auth/register",
            json={
                "username": f"duplicate{unique_id}",  # Same username
                "email": f"user2{unique_id}@example.com",
                "password": "password123",
            },
        )

        assert response2.status_code == 409
        data = response2.json()
        assert data["error"] == "Duplicate Record"
        assert "duplicate" in data["message"].lower()
        assert data["resource"] == "User"
        assert data["field"] == "username"

    @pytest.mark.asyncio
    async def test_duplicate_email_returns_409(self, authenticated_client):
        """Test that duplicate email returns 409 with proper error message"""
        unique_id = str(int(time.time() * 1000000))[
            -10:
        ]  # Use timestamp for uniqueness

        # Create first user
        response1 = await authenticated_client.post(
            "/api/auth/register",
            json={
                "username": f"user1{unique_id}",
                "email": f"duplicate{unique_id}@example.com",
                "password": "password123",
            },
        )
        assert response1.status_code == 201

        # Try to create second user with same email
        response2 = await authenticated_client.post(
            "/api/auth/register",
            json={
                "username": f"user2{unique_id}",
                "email": f"duplicate{unique_id}@example.com",  # Same email
                "password": "password123",
            },
        )

        assert response2.status_code == 409
        data = response2.json()
        assert data["error"] == "Duplicate Record"
        assert f"duplicate{unique_id}@example.com" in data["message"]
        assert data["field"] == "email"


class TestForeignKeyViolationExceptionHandler:
    """Tests for ForeignKeyViolationException handler (400 Bad Request)"""

    @pytest.mark.asyncio
    async def test_student_with_invalid_school_id_returns_400(
        self, authenticated_client
    ):
        """Test that creating student with invalid school_id returns 400"""
        response = await authenticated_client.post(
            "/api/students",
            json={
                "school_id": 999,  # Non-existent school
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Invalid Reference"
        assert "school_id" in data["message"]
        assert data["resource"] == "Student"
        assert data["foreign_key"] == "school_id"

    @pytest.mark.asyncio
    async def test_invoice_with_invalid_student_id_returns_400(
        self, authenticated_client
    ):
        """Test that creating invoice with invalid student_id returns 400"""
        response = await authenticated_client.post(
            "/api/invoices",
            json={
                "student_id": 999,  # Non-existent student
                "amount": "100.00",
                "due_date": "2024-12-31",
                "issue_date": "2024-01-01",
                "description": "Test invoice",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Invalid Reference"
        assert "student_id" in data["message"]
        assert data["resource"] == "Invoice"


class TestInvalidDataExceptionHandler:
    """Tests for InvalidDataException handler (422 Unprocessable Entity)"""

    @pytest.mark.asyncio
    async def test_payment_exceeding_balance_returns_422(self, authenticated_client):
        """Test that payment exceeding invoice balance returns 422"""
        # Create school
        school_response = await authenticated_client.post(
            "/api/schools", json={"name": "Test School", "email": "school@example.com"}
        )
        school_id = school_response.json()["id"]

        # Create student
        student_response = await authenticated_client.post(
            "/api/students",
            json={"school_id": school_id, "first_name": "John", "last_name": "Doe"},
        )
        student_id = student_response.json()["id"]

        # Create invoice
        invoice_response = await authenticated_client.post(
            "/api/invoices",
            json={
                "student_id": student_id,
                "amount": "100.00",
                "due_date": "2024-12-31",
                "issue_date": "2024-01-01",
            },
        )
        invoice_id = invoice_response.json()["id"]

        # Try to create payment exceeding balance
        payment_response = await authenticated_client.post(
            "/api/payments",
            json={
                "invoice_id": invoice_id,
                "amount": "150.00",  # Exceeds 100.00
                "payment_date": "2024-01-15",
                "payment_method": "CASH",
            },
        )

        assert payment_response.status_code == 422
        data = payment_response.json()
        assert data["error"] == "Invalid Data"
        assert "exceeds remaining balance" in data["message"]
        assert data["resource"] == "Payment"


class TestNotFoundExceptionHandler:
    """Tests for 404 Not Found responses"""

    @pytest.mark.asyncio
    async def test_get_nonexistent_school_returns_404(self, authenticated_client):
        """Test that getting non-existent school returns 404"""
        response = await authenticated_client.get("/api/schools/999")

        # Note: This might return 404 from FastAPI itself, not our custom handler
        # depending on how the routes are implemented
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_student_returns_404(self, authenticated_client):
        """Test that getting non-existent student returns 404"""
        response = await authenticated_client.get("/api/students/999")
        assert response.status_code == 404


class TestSuccessfulOperations:
    """Tests for successful operations that should NOT trigger exception handlers"""

    @pytest.mark.asyncio
    async def test_create_school_success_returns_201(self, authenticated_client):
        """Test that successful school creation returns 201"""
        response = await authenticated_client.post(
            "/api/schools",
            json={"name": "Success School", "email": "success@example.com"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Success School"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_student_with_valid_school_success(self, authenticated_client):
        """Test that creating student with valid school_id succeeds"""
        # Create school
        school_response = await authenticated_client.post(
            "/api/schools", json={"name": "Test School"}
        )
        school_id = school_response.json()["id"]

        # Create student
        student_response = await authenticated_client.post(
            "/api/students",
            json={"school_id": school_id, "first_name": "John", "last_name": "Doe"},
        )

        assert student_response.status_code == 201
        data = student_response.json()
        assert data["first_name"] == "John"
        assert data["school_id"] == school_id

    @pytest.mark.asyncio
    async def test_create_payment_within_balance_success(self, authenticated_client):
        """Test that creating payment within invoice balance succeeds"""
        # Create school
        school_response = await authenticated_client.post(
            "/api/schools", json={"name": "Test School"}
        )
        school_id = school_response.json()["id"]

        # Create student
        student_response = await authenticated_client.post(
            "/api/students",
            json={"school_id": school_id, "first_name": "John", "last_name": "Doe"},
        )
        student_id = student_response.json()["id"]

        # Create invoice
        invoice_response = await authenticated_client.post(
            "/api/invoices",
            json={
                "student_id": student_id,
                "amount": "100.00",
                "due_date": "2024-12-31",
                "issue_date": "2024-01-01",
            },
        )
        invoice_id = invoice_response.json()["id"]

        # Create payment within balance
        payment_response = await authenticated_client.post(
            "/api/payments",
            json={
                "invoice_id": invoice_id,
                "amount": "50.00",  # Within 100.00 balance
                "payment_date": "2024-01-15",
                "payment_method": "CASH",
            },
        )

        assert payment_response.status_code == 201
        data = payment_response.json()
        assert data["amount"] == "50.00"


class TestPartialPaymentScenarios:
    """Tests for partial payment scenarios"""

    @pytest.mark.asyncio
    async def test_multiple_partial_payments_success(self, authenticated_client):
        """Test that multiple partial payments within balance succeed"""
        # Create school, student, invoice
        school = await authenticated_client.post(
            "/api/schools", json={"name": "School"}
        )
        school_id = school.json()["id"]

        student = await authenticated_client.post(
            "/api/students",
            json={"school_id": school_id, "first_name": "John", "last_name": "Doe"},
        )
        student_id = student.json()["id"]

        invoice = await authenticated_client.post(
            "/api/invoices",
            json={
                "student_id": student_id,
                "amount": "100.00",
                "due_date": "2024-12-31",
                "issue_date": "2024-01-01",
            },
        )
        invoice_id = invoice.json()["id"]

        # First payment
        payment1 = await authenticated_client.post(
            "/api/payments",
            json={
                "invoice_id": invoice_id,
                "amount": "30.00",
                "payment_date": "2024-01-10",
            },
        )
        assert payment1.status_code == 201

        # Second payment
        payment2 = await authenticated_client.post(
            "/api/payments",
            json={
                "invoice_id": invoice_id,
                "amount": "40.00",
                "payment_date": "2024-01-15",
            },
        )
        assert payment2.status_code == 201

        # Third payment completing the invoice
        payment3 = await authenticated_client.post(
            "/api/payments",
            json={
                "invoice_id": invoice_id,
                "amount": "30.00",
                "payment_date": "2024-01-20",
            },
        )
        assert payment3.status_code == 201

    @pytest.mark.asyncio
    async def test_partial_payment_then_exceeding_returns_422(
        self, authenticated_client
    ):
        """Test that partial payment followed by exceeding payment returns 422"""
        # Create school, student, invoice
        school = await authenticated_client.post(
            "/api/schools", json={"name": "School"}
        )
        school_id = school.json()["id"]

        student = await authenticated_client.post(
            "/api/students",
            json={"school_id": school_id, "first_name": "John", "last_name": "Doe"},
        )
        student_id = student.json()["id"]

        invoice = await authenticated_client.post(
            "/api/invoices",
            json={
                "student_id": student_id,
                "amount": "100.00",
                "due_date": "2024-12-31",
                "issue_date": "2024-01-01",
            },
        )
        invoice_id = invoice.json()["id"]

        # First partial payment
        payment1 = await authenticated_client.post(
            "/api/payments",
            json={
                "invoice_id": invoice_id,
                "amount": "60.00",
                "payment_date": "2024-01-10",
            },
        )
        assert payment1.status_code == 201

        # Second payment exceeding remaining balance
        payment2 = await authenticated_client.post(
            "/api/payments",
            json={
                "invoice_id": invoice_id,
                "amount": "50.00",  # Would total 110.00, exceeds 100.00
                "payment_date": "2024-01-15",
            },
        )

        assert payment2.status_code == 422
        data = payment2.json()
        assert data["error"] == "Invalid Data"
        assert "exceeds remaining balance" in data["message"]


class TestExceptionResponseFormat:
    """Tests for exception response format consistency"""

    @pytest.mark.asyncio
    async def test_all_exceptions_return_json(self, authenticated_client):
        """Test that all exceptions return JSON responses"""
        unique_id = str(int(time.time() * 1000000))[
            -10:
        ]  # Use timestamp for uniqueness

        # Test duplicate (409)
        await authenticated_client.post(
            "/api/auth/register",
            json={
                "username": f"test{unique_id}",
                "email": f"test{unique_id}@example.com",
                "password": "pass123",
            },
        )
        response1 = await authenticated_client.post(
            "/api/auth/register",
            json={
                "username": f"test{unique_id}",
                "email": f"test2{unique_id}@example.com",
                "password": "pass123",
            },
        )
        assert response1.status_code == 409
        assert response1.headers["content-type"] == "application/json"

        # Test foreign key violation (400)
        response2 = await authenticated_client.post(
            "/api/students",
            json={"school_id": 999, "first_name": "John", "last_name": "Doe"},
        )
        assert response2.status_code == 400
        assert response2.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_exception_responses_have_required_fields(self, authenticated_client):
        """Test that exception responses have required fields"""
        unique_id = str(int(time.time() * 1000000))[
            -10:
        ]  # Use timestamp for uniqueness

        # Create duplicate user
        await authenticated_client.post(
            "/api/auth/register",
            json={
                "username": f"test{unique_id}",
                "email": f"test{unique_id}@example.com",
                "password": "pass123",
            },
        )
        response = await authenticated_client.post(
            "/api/auth/register",
            json={
                "username": f"test{unique_id}",
                "email": f"test2{unique_id}@example.com",
                "password": "pass123",
            },
        )

        data = response.json()
        assert "error" in data
        assert "message" in data
        assert isinstance(data["error"], str)
        assert isinstance(data["message"], str)
