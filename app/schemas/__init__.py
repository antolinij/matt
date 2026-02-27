"""Pydantic schemas (DTOs)"""
from .school import School, SchoolCreate, SchoolUpdate
from .student import Student, StudentCreate, StudentUpdate
from .invoice import Invoice, InvoiceCreate, InvoiceUpdate
from .payment import Payment, PaymentCreate, PaymentUpdate
from .account_status import InvoiceDetail, StudentAccountStatus, SchoolAccountStatus, SchoolStudentAccountStatus
from .user import User, UserCreate, UserLogin, UserUpdate, UserInDB
from .token import Token, TokenData, RefreshTokenRequest

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
