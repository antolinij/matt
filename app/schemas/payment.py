"""Payment schemas (Pydantic models)"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from app.db.models import PaymentMethod


class PaymentBase(BaseModel):
    """Base payment schema"""
    invoice_id: int
    amount: Decimal = Field(..., gt=0)
    payment_date: date
    payment_method: PaymentMethod = PaymentMethod.OTHER
    reference: Optional[str] = None

    @field_validator("payment_method", mode="before")
    @classmethod
    def normalize_payment_method(cls, value):
        if isinstance(value, str):
            return value.lower()
        return value


class PaymentCreate(PaymentBase):
    """Schema for creating a payment"""
    pass


class PaymentUpdate(BaseModel):
    """Schema for updating a payment"""
    amount: Optional[Decimal] = Field(None, gt=0)
    payment_date: Optional[date] = None
    payment_method: Optional[PaymentMethod] = None
    reference: Optional[str] = None

    @field_validator("payment_method", mode="before")
    @classmethod
    def normalize_payment_method(cls, value):
        if isinstance(value, str):
            return value.lower()
        return value


class Payment(PaymentBase):
    """Schema for payment response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
