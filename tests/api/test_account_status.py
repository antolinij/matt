from datetime import date
from decimal import Decimal

import pytest


@pytest.mark.asyncio
async def test_student_account_status(authenticated_client):
    """Test student account status calculation"""
    # Create school
    school_response = await authenticated_client.post(
        "/api/schools/", json={"name": "Test School"}
    )
    school_id = school_response.json()["id"]

    # Create student
    student_response = await authenticated_client.post(
        "/api/students/",
        json={
            "school_id": school_id,
            "first_name": "Test",
            "last_name": "Student",
            "status": "active",
        },
    )
    student_id = student_response.json()["id"]

    # Create invoices
    invoice1 = await authenticated_client.post(
        "/api/invoices/",
        json={
            "student_id": student_id,
            "amount": 5000.00,
            "issue_date": str(date.today()),
            "due_date": str(date.today()),
            "description": "Invoice 1",
        },
    )
    invoice1_id = invoice1.json()["id"]

    invoice2 = await authenticated_client.post(
        "/api/invoices/",
        json={
            "student_id": student_id,
            "amount": 3000.00,
            "issue_date": str(date.today()),
            "due_date": str(date.today()),
            "description": "Invoice 2",
        },
    )

    # Create payment
    await authenticated_client.post(
        "/api/payments/",
        json={
            "invoice_id": invoice1_id,
            "amount": 2500.00,
            "payment_date": str(date.today()),
            "payment_method": "cash",
        },
    )

    # Get account status
    response = await authenticated_client.get(
        f"/api/students/{student_id}/account-status"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["student_id"] == student_id
    assert float(data["total_invoiced"]) == 8000.00
    assert float(data["total_paid"]) == 2500.00
    assert float(data["total_pending"]) == 5500.00
    assert len(data["invoices"]) == 2


@pytest.mark.asyncio
async def test_school_account_status(authenticated_client):
    """Test school account status calculation"""
    # Create school
    school_response = await authenticated_client.post(
        "/api/schools/", json={"name": "Status Test School"}
    )
    school_id = school_response.json()["id"]

    # Create students
    student1 = await authenticated_client.post(
        "/api/students/",
        json={
            "school_id": school_id,
            "first_name": "Student",
            "last_name": "One",
            "status": "active",
        },
    )
    student1_id = student1.json()["id"]

    student2 = await authenticated_client.post(
        "/api/students/",
        json={
            "school_id": school_id,
            "first_name": "Student",
            "last_name": "Two",
            "status": "active",
        },
    )
    student2_id = student2.json()["id"]

    # Create invoices for both students
    invoice1 = await authenticated_client.post(
        "/api/invoices/",
        json={
            "student_id": student1_id,
            "amount": 4000.00,
            "issue_date": str(date.today()),
            "due_date": str(date.today()),
            "description": "Student 1 Invoice",
        },
    )

    invoice2 = await authenticated_client.post(
        "/api/invoices/",
        json={
            "student_id": student2_id,
            "amount": 6000.00,
            "issue_date": str(date.today()),
            "due_date": str(date.today()),
            "description": "Student 2 Invoice",
        },
    )
    invoice2_id = invoice2.json()["id"]

    # Create payment for student 2
    await authenticated_client.post(
        "/api/payments/",
        json={
            "invoice_id": invoice2_id,
            "amount": 6000.00,
            "payment_date": str(date.today()),
            "payment_method": "transfer",
        },
    )

    # Get school account status
    response = await authenticated_client.get(
        f"/api/schools/{school_id}/account-status"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["school_id"] == school_id
    assert data["total_students"] == 2
    assert data["active_students"] == 2
    assert float(data["total_invoiced"]) == 10000.00
    assert float(data["total_paid"]) == 6000.00
    assert float(data["total_pending"]) == 4000.00


@pytest.mark.asyncio
async def test_payment_validation(authenticated_client):
    """Test that payments can't exceed invoice balance"""
    # Create school
    school_response = await authenticated_client.post(
        "/api/schools/", json={"name": "Payment Test School"}
    )
    school_id = school_response.json()["id"]

    # Create student
    student_response = await authenticated_client.post(
        "/api/students/",
        json={
            "school_id": school_id,
            "first_name": "Payment",
            "last_name": "Test",
            "status": "active",
        },
    )
    student_id = student_response.json()["id"]

    # Create invoice
    invoice_response = await authenticated_client.post(
        "/api/invoices/",
        json={
            "student_id": student_id,
            "amount": 1000.00,
            "issue_date": str(date.today()),
            "due_date": str(date.today()),
            "description": "Test Invoice",
        },
    )
    invoice_id = invoice_response.json()["id"]

    # Try to pay more than invoice amount
    payment_response = await authenticated_client.post(
        "/api/payments/",
        json={
            "invoice_id": invoice_id,
            "amount": 1500.00,
            "payment_date": str(date.today()),
            "payment_method": "cash",
        },
    )
    assert payment_response.status_code == 422
