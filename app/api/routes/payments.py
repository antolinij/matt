"""
Payment API Routes

This module defines all HTTP endpoints for payment management operations.
All routes use dependency injection for services and follow RESTful conventions.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from decimal import Decimal

from app.schemas import Payment, PaymentCreate, PaymentUpdate, User
from app.services.payment_service import PaymentService
from app.core.security import get_current_active_user
from app.api.dependencies import get_payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=Payment, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment: PaymentCreate,
    service: PaymentService = Depends(get_payment_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new payment for an invoice. 🔒 Requires authentication.

    Args:
        payment: PaymentCreate schema with payment data
        service: Injected PaymentService instance

    Returns:
        Created payment with generated ID and timestamp

    Raises:
        HTTPException 404: If the specified invoice does not exist
        HTTPException 400: If payment amount exceeds remaining invoice balance

    Business Rules:
        - Invoice must exist before creating a payment
        - Payment amount cannot exceed the remaining balance on the invoice
        - Invoice status is automatically updated to PAID when fully paid
    """
    try:
        created_payment = await service.create_payment(payment)
        if not created_payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        return created_payment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[Payment])
async def list_payments(
    skip: int = 0,
    limit: int = 100,
    invoice_id: Optional[int] = Query(None, description="Filter by invoice ID"),
    service: PaymentService = Depends(get_payment_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all payments with pagination and optional filtering. 🔒 Requires authentication.

    Args:
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100)
        invoice_id: Optional invoice ID to filter payments by
        service: Injected PaymentService instance

    Returns:
        List of Payment schemas
    """
    return await service.get_all_payments(skip=skip, limit=limit, invoice_id=invoice_id)


@router.get("/{payment_id}", response_model=Payment)
async def get_payment(
    payment_id: int,
    service: PaymentService = Depends(get_payment_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific payment by ID. 🔒 Requires authentication.

    Args:
        payment_id: ID of the payment to retrieve
        service: Injected PaymentService instance

    Returns:
        Payment schema with all details

    Raises:
        HTTPException 404: If payment not found
    """
    payment = await service.get_payment(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    return payment


@router.put("/{payment_id}", response_model=Payment)
async def update_payment(
    payment_id: int,
    payment: PaymentUpdate,
    service: PaymentService = Depends(get_payment_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a payment's information. 🔒 Requires authentication.

    Args:
        payment_id: ID of the payment to update
        payment: PaymentUpdate schema with updated data
        service: Injected PaymentService instance

    Returns:
        Updated Payment schema

    Raises:
        HTTPException 404: If payment not found

    Note:
        - Invoice ID cannot be updated (payments are tied to a specific invoice)
        - Updating payment amount will trigger recalculation of invoice status
    """
    updated_payment = await service.update_payment(payment_id, payment)
    if not updated_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    return updated_payment


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: int,
    service: PaymentService = Depends(get_payment_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a payment. 🔒 Requires authentication.

    Args:
        payment_id: ID of the payment to delete
        service: Injected PaymentService instance

    Returns:
        None (204 No Content on success)

    Raises:
        HTTPException 404: If payment not found

    Note:
        Deleting a payment will trigger recalculation of the associated invoice status
    """
    success = await service.delete_payment(payment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    return None


@router.get("/invoices/{invoice_id}/remaining-balance", response_model=dict)
async def get_invoice_remaining_balance(
    invoice_id: int,
    service: PaymentService = Depends(get_payment_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Calculate the remaining balance for an invoice.

    Args:
        invoice_id: ID of the invoice
        service: Injected PaymentService instance

    Returns:
        Dictionary with invoice_id and remaining_balance

    Raises:
        HTTPException 404: If invoice not found
    """
    remaining_balance = await service.get_invoice_remaining_balance(invoice_id)
    if remaining_balance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return {
        "invoice_id": invoice_id,
        "remaining_balance": remaining_balance
    }
