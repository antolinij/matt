"""
Dependency injection for API routes.

This module provides dependency functions that create and inject service instances
with their required repositories into API route handlers.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.school_repository import SchoolRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.invoice_service import InvoiceService
from app.services.payment_service import PaymentService
from app.services.school_service import SchoolService
from app.services.student_service import StudentService


# School Service Dependency
def get_school_service(db: AsyncSession = Depends(get_db)) -> SchoolService:
    """
    Create and return a SchoolService instance with its repository.

    Args:
        db: Database session injected by FastAPI

    Returns:
        SchoolService instance ready to use
    """
    repository = SchoolRepository(db)
    return SchoolService(repository)


# Student Service Dependency
def get_student_service(db: AsyncSession = Depends(get_db)) -> StudentService:
    """
    Create and return a StudentService instance with its repositories.

    Args:
        db: Database session injected by FastAPI

    Returns:
        StudentService instance ready to use
    """
    student_repository = StudentRepository(db)
    school_repository = SchoolRepository(db)
    return StudentService(student_repository, school_repository)


# Invoice Service Dependency
def get_invoice_service(db: AsyncSession = Depends(get_db)) -> InvoiceService:
    """
    Create and return an InvoiceService instance with its repositories.

    Args:
        db: Database session injected by FastAPI

    Returns:
        InvoiceService instance ready to use
    """
    invoice_repository = InvoiceRepository(db)
    student_repository = StudentRepository(db)
    return InvoiceService(invoice_repository, student_repository)


# Payment Service Dependency
def get_payment_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    """
    Create and return a PaymentService instance with its repositories.

    Args:
        db: Database session injected by FastAPI

    Returns:
        PaymentService instance ready to use
    """
    payment_repository = PaymentRepository(db)
    invoice_repository = InvoiceRepository(db)
    student_repository = StudentRepository(db)
    return PaymentService(payment_repository, invoice_repository, student_repository)


# Auth Service Dependency
def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """
    Create and return an AuthService instance with its repository.

    Args:
        db: Database session injected by FastAPI

    Returns:
        AuthService instance ready to use
    """
    user_repository = UserRepository(db)
    return AuthService(user_repository)
