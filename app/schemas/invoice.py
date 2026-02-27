"""Invoice schemas (Pydantic models)"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from app.db.models import InvoiceStatus


class InvoiceBase(BaseModel):
    """Base invoice schema"""
    student_id: int
    amount: Decimal = Field(..., gt=0)
    due_date: date
    issue_date: date
    description: Optional[str] = None
    status: InvoiceStatus = InvoiceStatus.PENDING


class InvoiceCreate(InvoiceBase):
    """Schema for creating an invoice"""
    pass


class InvoiceUpdate(BaseModel):
    """Schema for updating an invoice"""
    student_id: Optional[int] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    due_date: Optional[date] = None
    issue_date: Optional[date] = None
    description: Optional[str] = None
    status: Optional[InvoiceStatus] = None


class Invoice(InvoiceBase):
    """Schema for invoice response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str
    created_at: datetime
    updated_at: datetime
