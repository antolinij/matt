"""
Invoice API Routes

This module defines all HTTP endpoints for invoice management operations.
All routes use dependency injection for services and follow RESTful conventions.
"""

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_invoice_service
from app.core.security import get_current_active_user
from app.schemas import Invoice, InvoiceCreate, InvoiceUpdate, User
from app.services.invoice_service import InvoiceService

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("", response_model=Invoice, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice: InvoiceCreate,
    service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new invoice. 🔒 Requires authentication.

    Args:
        invoice: InvoiceCreate schema with invoice data
        service: Injected InvoiceService instance

    Returns:
        Created invoice with auto-generated invoice number, ID, and timestamps

    Raises:
        HTTPException 404: If the specified student does not exist

    Business Rules:
        - Invoice number is automatically generated in format INV-XXXXXX
        - Student must exist before creating an invoice
        - Amount must be greater than 0
    """
    created_invoice = await service.create_invoice(invoice)
    if not created_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )
    return created_invoice


@router.get("", response_model=List[Invoice])
async def list_invoices(
    skip: int = 0,
    limit: int = 100,
    student_id: Optional[int] = Query(None, description="Filter by student ID"),
    service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all invoices with pagination and optional filtering. 🔒 Requires authentication.

    Args:
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100)
        student_id: Optional student ID to filter invoices by
        service: Injected InvoiceService instance

    Returns:
        List of Invoice schemas
    """
    return await service.get_all_invoices(skip=skip, limit=limit, student_id=student_id)


@router.get("/{invoice_id}", response_model=Invoice)
async def get_invoice(
    invoice_id: int,
    service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific invoice by ID. 🔒 Requires authentication.

    Args:
        invoice_id: ID of the invoice to retrieve
        service: Injected InvoiceService instance

    Returns:
        Invoice schema with all details

    Raises:
        HTTPException 404: If invoice not found
    """
    invoice = await service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )
    return invoice


@router.put("/{invoice_id}", response_model=Invoice)
async def update_invoice(
    invoice_id: int,
    invoice: InvoiceUpdate,
    service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update an invoice's information. 🔒 Requires authentication.

    Args:
        invoice_id: ID of the invoice to update
        invoice: InvoiceUpdate schema with updated data
        service: Injected InvoiceService instance

    Returns:
        Updated Invoice schema

    Raises:
        HTTPException 404: If invoice not found or new student_id does not exist

    Note:
        - Invoice number cannot be updated (it's auto-generated)
        - If changing student_id, the new student must exist
    """
    updated_invoice = await service.update_invoice(invoice_id, invoice)
    if not updated_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found or invalid student_id",
        )
    return updated_invoice


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete an invoice. 🔒 Requires authentication.

    Args:
        invoice_id: ID of the invoice to delete
        service: Injected InvoiceService instance

    Returns:
        None (204 No Content on success)

    Raises:
        HTTPException 404: If invoice not found

    Note:
        This will cascade delete all related payments
    """
    success = await service.delete_invoice(invoice_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )
    return None


@router.get("/{invoice_id}/paid-amount", response_model=dict)
async def get_invoice_paid_amount(
    invoice_id: int,
    service: InvoiceService = Depends(get_invoice_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the total paid amount for an invoice. 🔒 Requires authentication.

    Args:
        invoice_id: ID of the invoice
        service: Injected InvoiceService instance

    Returns:
        Dictionary with invoice_id and paid_amount

    Raises:
        HTTPException 404: If invoice not found
    """
    paid_amount = await service.get_paid_amount(invoice_id)
    if paid_amount is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )
    return {"invoice_id": invoice_id, "paid_amount": paid_amount}
