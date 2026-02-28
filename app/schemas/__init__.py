"""Pydantic schemas (DTOs)"""

from .account_status import (InvoiceDetail, SchoolAccountStatus,
                             SchoolStudentAccountStatus, StudentAccountStatus)
from .invoice import Invoice, InvoiceCreate, InvoiceUpdate
from .payment import Payment, PaymentCreate, PaymentUpdate
from .school import School, SchoolCreate, SchoolUpdate
from .student import Student, StudentCreate, StudentUpdate
from .token import RefreshTokenRequest, Token, TokenData
from .user import User, UserCreate, UserInDB, UserLogin, UserUpdate

__all__ = [
    # School
    "School",
    "SchoolCreate",
    "SchoolUpdate",
    # Student
    "Student",
    "StudentCreate",
    "StudentUpdate",
    # Invoice
    "Invoice",
    "InvoiceCreate",
    "InvoiceUpdate",
    # Payment
    "Payment",
    "PaymentCreate",
    "PaymentUpdate",
    # Account Status
    "InvoiceDetail",
    "StudentAccountStatus",
    "SchoolAccountStatus",
    "SchoolStudentAccountStatus",
    # User & Auth
    "User",
    "UserCreate",
    "UserLogin",
    "UserUpdate",
    "UserInDB",
    # Token
    "Token",
    "TokenData",
    "RefreshTokenRequest",
]
