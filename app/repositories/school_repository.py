"""School repository for database operations"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, OperationalError, DataError
from typing import List, Optional
from decimal import Decimal

from app.db.models import School, Student, Invoice, Payment, StudentStatus, InvoiceStatus
from app.core.exceptions import (
    DuplicateRecordException,
    DatabaseConnectionException,
    DatabaseOperationException,
    InvalidDataException
)


class SchoolRepository:
    """Repository for School database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, name: str, address: Optional[str] = None,
                    phone: Optional[str] = None, email: Optional[str] = None) -> School:
        """
        Create a new school.

        Args:
            name: School name
            address: School address (optional)
            phone: School phone (optional)
            email: School email (optional)

        Returns:
            Created School instance

        Raises:
            DuplicateRecordException: If school with same email or unique constraint violated
            DatabaseConnectionException: If database connection fails
            InvalidDataException: If data validation fails
            DatabaseOperationException: If operation fails for other reasons
        """
        try:
            school = School(name=name, address=address, phone=phone, email=email)
            self.db.add(school)
            await self.db.commit()
            await self.db.refresh(school)
            return school
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = str(e.orig).lower()

            # Check which constraint was violated
            if 'email' in error_msg:
                raise DuplicateRecordException("School", "email", email)
            else:
                raise DatabaseOperationException("create", "School", str(e.orig))
        except DataError as e:
            await self.db.rollback()
            raise InvalidDataException("School", str(e.orig))
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("create", "School", str(e))

    async def get(self, school_id: int) -> Optional[School]:
        """
        Get a school by ID.

        Args:
            school_id: ID of the school

        Returns:
            School instance or None if not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            result = await self.db.execute(
                select(School).filter(School.id == school_id)
            )
            return result.scalar_one_or_none()
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get", "School", str(e))

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[School]:
        """
        Get all schools with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of School instances

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            result = await self.db.execute(
                select(School).offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get_all", "School", str(e))

    async def update(self, school_id: int, **kwargs) -> Optional[School]:
        """
        Update a school.

        Args:
            school_id: ID of the school to update
            **kwargs: Fields to update

        Returns:
            Updated School instance or None if not found

        Raises:
            DuplicateRecordException: If email already exists
            DatabaseConnectionException: If database connection fails
            InvalidDataException: If data validation fails
            DatabaseOperationException: If operation fails for other reasons
        """
        try:
            school = await self.get(school_id)
            if not school:
                return None

            for field, value in kwargs.items():
                if value is not None and hasattr(school, field):
                    setattr(school, field, value)

            await self.db.commit()
            await self.db.refresh(school)
            return school
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = str(e.orig).lower()

            # Check which constraint was violated
            if 'email' in error_msg:
                raise DuplicateRecordException("School", "email", kwargs.get('email', 'unknown'))
            else:
                raise DatabaseOperationException("update", "School", str(e.orig))
        except DataError as e:
            await self.db.rollback()
            raise InvalidDataException("School", str(e.orig))
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("update", "School", str(e))

    async def delete(self, school_id: int) -> bool:
        """
        Delete a school.

        Args:
            school_id: ID of the school to delete

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            school = await self.get(school_id)
            if not school:
                return False

            await self.db.delete(school)
            await self.db.commit()
            return True
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("delete", "School", str(e))

    async def get_account_status(self, school_id: int) -> Optional[dict]:
        """
        Get account status for a school - OPTIMIZED to avoid N+1 queries.

        Args:
            school_id: ID of the school

        Returns:
            Dictionary with account status or None if school not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            # Get school
            school = await self.get(school_id)
            if not school:
                return None

            # Get student counts in a single query
            result = await self.db.execute(
                select(
                    func.count(Student.id).label('total_students'),
                    func.count(Student.id).filter(Student.status == StudentStatus.ACTIVE).label('active_students')
                )
                .filter(Student.school_id == school_id)
            )
            student_counts = result.one()
            total_students = student_counts.total_students
            active_students = student_counts.active_students

            # Single optimized query: Join students -> invoices -> payments with aggregation
            # This replaces potentially hundreds of queries with just ONE query
            query = (
                select(
                    Invoice.id,
                    Invoice.invoice_number,
                    Invoice.amount,
                    Invoice.due_date,
                    Invoice.status,
                    func.coalesce(func.sum(Payment.amount), 0).label('paid_amount')
                )
                .join(Student, Invoice.student_id == Student.id)
                .outerjoin(Payment, Invoice.id == Payment.invoice_id)
                .filter(Student.school_id == school_id)
                .group_by(
                    Invoice.id,
                    Invoice.invoice_number,
                    Invoice.amount,
                    Invoice.due_date,
                    Invoice.status
                )
            )

            result = await self.db.execute(query)
            invoice_rows = result.all()

            total_invoiced = Decimal('0')
            total_paid = Decimal('0')
            invoice_details = []

            for row in invoice_rows:
                invoice_amount = Decimal(str(row.amount))
                paid_amount = Decimal(str(row.paid_amount))
                balance = invoice_amount - paid_amount

                total_invoiced += invoice_amount
                total_paid += paid_amount

                invoice_details.append({
                    'id': row.id,
                    'invoice_number': row.invoice_number,
                    'amount': row.amount,
                    'paid_amount': paid_amount,
                    'balance': balance,
                    'due_date': row.due_date,
                    'status': row.status
                })

            return {
                'school_id': school.id,
                'school_name': school.name,
                'total_students': total_students,
                'active_students': active_students,
                'total_invoiced': total_invoiced,
                'total_paid': total_paid,
                'total_pending': total_invoiced - total_paid,
                'invoices': invoice_details
            }
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get_account_status", "School", str(e))

    async def get_student_account_status(self, school_id: int, student_id: int) -> Optional[dict]:
        """
        Get account status for a specific student in a specific school.

        Args:
            school_id: ID of the school
            student_id: ID of the student

        Returns:
            Dictionary with student account status or None if school/student not found
            or student doesn't belong to the school

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            # Verify school exists
            school = await self.get(school_id)
            if not school:
                return None

            # Verify student exists AND belongs to this school
            result = await self.db.execute(
                select(Student).filter(
                    Student.id == student_id,
                    Student.school_id == school_id
                )
            )
            student = result.scalar_one_or_none()
            if not student:
                return None

            # Get all invoices for this student with payment totals
            query = (
                select(
                    Invoice.id,
                    Invoice.invoice_number,
                    Invoice.amount,
                    Invoice.due_date,
                    Invoice.status,
                    func.coalesce(func.sum(Payment.amount), 0).label('paid_amount')
                )
                .outerjoin(Payment, Invoice.id == Payment.invoice_id)
                .filter(Invoice.student_id == student_id)
                .group_by(
                    Invoice.id,
                    Invoice.invoice_number,
                    Invoice.amount,
                    Invoice.due_date,
                    Invoice.status
                )
            )

            result = await self.db.execute(query)
            invoice_rows = result.all()

            total_invoiced = Decimal('0')
            total_paid = Decimal('0')
            invoice_details = []

            for row in invoice_rows:
                invoice_amount = Decimal(str(row.amount))
                paid_amount = Decimal(str(row.paid_amount))
                balance = invoice_amount - paid_amount

                total_invoiced += invoice_amount
                total_paid += paid_amount

                invoice_details.append({
                    'id': row.id,
                    'invoice_number': row.invoice_number,
                    'amount': row.amount,
                    'paid_amount': paid_amount,
                    'balance': balance,
                    'due_date': row.due_date,
                    'status': row.status
                })

            return {
                'student_id': student.id,
                'student_name': f"{student.first_name} {student.last_name}",
                'total_invoiced': total_invoiced,
                'total_paid': total_paid,
                'total_pending': total_invoiced - total_paid,
                'invoices': invoice_details
            }
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get_student_account_status", "School", str(e))
