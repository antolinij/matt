"""Student repository for database operations"""

from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import DataError, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (DatabaseConnectionException,
                                 DatabaseOperationException,
                                 DuplicateRecordException,
                                 ForeignKeyViolationException,
                                 InvalidDataException)
from app.db.models import Invoice, Payment, School, Student, StudentStatus


class StudentRepository:
    """Repository for Student database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        school_id: int,
        first_name: str,
        last_name: str,
        email: Optional[str] = None,
        enrollment_date: Optional[date] = None,
        status: StudentStatus = StudentStatus.ACTIVE,
    ) -> Student:
        """
        Create a new student.

        Args:
            school_id: ID of the school
            first_name: Student's first name
            last_name: Student's last name
            email: Student's email (optional)
            enrollment_date: Enrollment date (optional)
            status: Student status (default: ACTIVE)

        Returns:
            Created Student instance

        Raises:
            ForeignKeyViolationException: If school_id doesn't exist
            DuplicateRecordException: If email already exists
            DatabaseConnectionException: If database connection fails
            InvalidDataException: If data validation fails
            DatabaseOperationException: If operation fails for other reasons
        """
        try:
            school_exists = await self.db.scalar(
                select(School.id).filter(School.id == school_id)
            )
            if school_exists is None:
                raise ForeignKeyViolationException("Student", "school_id", school_id)

            student = Student(
                school_id=school_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                enrollment_date=enrollment_date,
                status=status,
            )
            self.db.add(student)
            await self.db.commit()
            await self.db.refresh(student)
            return student
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = str(e.orig).lower()

            # Check which constraint was violated
            if "foreign key" in error_msg and "school" in error_msg:
                raise ForeignKeyViolationException("Student", "school_id", school_id)
            elif "email" in error_msg:
                raise DuplicateRecordException("Student", "email", email)
            else:
                raise DatabaseOperationException("create", "Student", str(e.orig))
        except DataError as e:
            await self.db.rollback()
            raise InvalidDataException("Student", str(e.orig))
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except ForeignKeyViolationException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("create", "Student", str(e))

    async def get(self, student_id: int) -> Optional[Student]:
        """
        Get a student by ID.

        Args:
            student_id: ID of the student

        Returns:
            Student instance or None if not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            result = await self.db.execute(
                select(Student).filter(Student.id == student_id)
            )
            return result.scalar_one_or_none()
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get", "Student", str(e))

    async def get_all(
        self, skip: int = 0, limit: int = 100, school_id: Optional[int] = None
    ) -> List[Student]:
        """
        Get all students with pagination and optional school filter.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            school_id: Optional school ID filter

        Returns:
            List of Student instances

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            query = select(Student)
            if school_id:
                query = query.filter(Student.school_id == school_id)
            query = query.offset(skip).limit(limit)

            result = await self.db.execute(query)
            return list(result.scalars().all())
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get_all", "Student", str(e))

    async def update(self, student_id: int, **kwargs) -> Optional[Student]:
        """
        Update a student.

        Args:
            student_id: ID of the student to update
            **kwargs: Fields to update

        Returns:
            Updated Student instance or None if not found

        Raises:
            ForeignKeyViolationException: If school_id doesn't exist
            DuplicateRecordException: If email already exists
            DatabaseConnectionException: If database connection fails
            InvalidDataException: If data validation fails
            DatabaseOperationException: If operation fails for other reasons
        """
        try:
            student = await self.get(student_id)
            if not student:
                return None

            if "school_id" in kwargs and kwargs["school_id"] is not None:
                school_exists = await self.db.scalar(
                    select(School.id).filter(School.id == kwargs["school_id"])
                )
                if school_exists is None:
                    raise ForeignKeyViolationException(
                        "Student", "school_id", kwargs["school_id"]
                    )

            for field, value in kwargs.items():
                if value is not None and hasattr(student, field):
                    setattr(student, field, value)

            await self.db.commit()
            await self.db.refresh(student)
            return student
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = str(e.orig).lower()

            # Check which constraint was violated
            if "foreign key" in error_msg and "school" in error_msg:
                raise ForeignKeyViolationException(
                    "Student", "school_id", kwargs.get("school_id", "unknown")
                )
            elif "email" in error_msg:
                raise DuplicateRecordException(
                    "Student", "email", kwargs.get("email", "unknown")
                )
            else:
                raise DatabaseOperationException("update", "Student", str(e.orig))
        except DataError as e:
            await self.db.rollback()
            raise InvalidDataException("Student", str(e.orig))
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except ForeignKeyViolationException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("update", "Student", str(e))

    async def delete(self, student_id: int) -> bool:
        """
        Delete a student.

        Args:
            student_id: ID of the student to delete

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            student = await self.get(student_id)
            if not student:
                return False

            await self.db.delete(student)
            await self.db.commit()
            return True
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("delete", "Student", str(e))

    async def get_account_status(self, student_id: int) -> Optional[dict]:
        """
        Get account status for a student - OPTIMIZED to avoid N+1 queries.

        Args:
            student_id: ID of the student

        Returns:
            Dictionary with account status or None if student not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            # Get student
            student = await self.get(student_id)
            if not student:
                return None

            # Single query to get all invoices with their payment totals using LEFT JOIN and aggregation
            # This replaces N queries (one per invoice) with a single query
            query = (
                select(
                    Invoice.id,
                    Invoice.invoice_number,
                    Invoice.amount,
                    Invoice.due_date,
                    Invoice.status,
                    func.coalesce(func.sum(Payment.amount), 0).label("paid_amount"),
                )
                .outerjoin(Payment, Invoice.id == Payment.invoice_id)
                .filter(Invoice.student_id == student_id)
                .group_by(
                    Invoice.id,
                    Invoice.invoice_number,
                    Invoice.amount,
                    Invoice.due_date,
                    Invoice.status,
                )
            )

            result = await self.db.execute(query)
            invoice_rows = result.all()

            total_invoiced = Decimal("0")
            total_paid = Decimal("0")
            invoice_details = []

            for row in invoice_rows:
                invoice_amount = Decimal(str(row.amount))
                paid_amount = Decimal(str(row.paid_amount))
                balance = invoice_amount - paid_amount

                total_invoiced += invoice_amount
                total_paid += paid_amount

                invoice_details.append(
                    {
                        "id": row.id,
                        "invoice_number": row.invoice_number,
                        "amount": row.amount,
                        "paid_amount": paid_amount,
                        "balance": balance,
                        "due_date": row.due_date,
                        "status": row.status,
                    }
                )

            return {
                "student_id": student.id,
                "student_name": f"{student.first_name} {student.last_name}",
                "total_invoiced": total_invoiced,
                "total_paid": total_paid,
                "total_pending": total_invoiced - total_paid,
                "invoices": invoice_details,
            }
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get_account_status", "Student", str(e))
