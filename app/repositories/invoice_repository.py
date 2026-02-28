"""Invoice repository for database operations"""

from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import DataError, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (DatabaseConnectionException,
                                 DatabaseOperationException,
                                 ForeignKeyViolationException,
                                 InvalidDataException)
from app.db.models import Invoice, InvoiceStatus, Payment, Student


class InvoiceRepository:
    """Repository for Invoice database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_invoice_number(self) -> str:
        """
        Generate unique invoice number.

        Returns:
            Generated invoice number string

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            result = await self.db.execute(
                select(Invoice).order_by(Invoice.id.desc()).limit(1)
            )
            last_invoice = result.scalar_one_or_none()
            next_number = 1 if not last_invoice else last_invoice.id + 1
            return f"INV-{next_number:06d}"
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException(
                "generate_invoice_number", "Invoice", str(e)
            )

    async def create(
        self,
        student_id: int,
        amount: Decimal,
        due_date: date,
        issue_date: date,
        description: Optional[str] = None,
        status: InvoiceStatus = InvoiceStatus.PENDING,
    ) -> Invoice:
        """
        Create a new invoice.

        Args:
            student_id: ID of the student
            amount: Invoice amount
            due_date: Payment due date
            issue_date: Invoice issue date
            description: Invoice description (optional)
            status: Invoice status (default: PENDING)

        Returns:
            Created Invoice instance

        Raises:
            ForeignKeyViolationException: If student_id doesn't exist
            DatabaseConnectionException: If database connection fails
            InvalidDataException: If data validation fails
            DatabaseOperationException: If operation fails for other reasons
        """
        try:
            student_exists = await self.db.scalar(
                select(Student.id).filter(Student.id == student_id)
            )
            if student_exists is None:
                raise ForeignKeyViolationException("Invoice", "student_id", student_id)

            invoice_number = await self.generate_invoice_number()
            invoice = Invoice(
                student_id=student_id,
                invoice_number=invoice_number,
                amount=amount,
                due_date=due_date,
                issue_date=issue_date,
                description=description,
                status=status,
            )
            self.db.add(invoice)
            await self.db.commit()
            await self.db.refresh(invoice)
            return invoice
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = str(e.orig).lower()

            # Check which constraint was violated
            if "foreign key" in error_msg and "student" in error_msg:
                raise ForeignKeyViolationException("Invoice", "student_id", student_id)
            else:
                raise DatabaseOperationException("create", "Invoice", str(e.orig))
        except DataError as e:
            await self.db.rollback()
            raise InvalidDataException("Invoice", str(e.orig))
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except ForeignKeyViolationException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("create", "Invoice", str(e))

    async def get(self, invoice_id: int) -> Optional[Invoice]:
        """
        Get an invoice by ID.

        Args:
            invoice_id: ID of the invoice

        Returns:
            Invoice instance or None if not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            result = await self.db.execute(
                select(Invoice).filter(Invoice.id == invoice_id)
            )
            return result.scalar_one_or_none()
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get", "Invoice", str(e))

    async def get_all(
        self, skip: int = 0, limit: int = 100, student_id: Optional[int] = None
    ) -> List[Invoice]:
        """
        Get all invoices with pagination and optional student filter.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            student_id: Optional student ID filter

        Returns:
            List of Invoice instances

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            query = select(Invoice)
            if student_id:
                query = query.filter(Invoice.student_id == student_id)
            query = query.offset(skip).limit(limit)

            result = await self.db.execute(query)
            return list(result.scalars().all())
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get_all", "Invoice", str(e))

    async def update(self, invoice_id: int, **kwargs) -> Optional[Invoice]:
        """
        Update an invoice.

        Args:
            invoice_id: ID of the invoice to update
            **kwargs: Fields to update

        Returns:
            Updated Invoice instance or None if not found

        Raises:
            ForeignKeyViolationException: If student_id doesn't exist
            DatabaseConnectionException: If database connection fails
            InvalidDataException: If data validation fails
            DatabaseOperationException: If operation fails for other reasons
        """
        try:
            invoice = await self.get(invoice_id)
            if not invoice:
                return None

            if "student_id" in kwargs and kwargs["student_id"] is not None:
                student_exists = await self.db.scalar(
                    select(Student.id).filter(Student.id == kwargs["student_id"])
                )
                if student_exists is None:
                    raise ForeignKeyViolationException(
                        "Invoice", "student_id", kwargs["student_id"]
                    )

            for field, value in kwargs.items():
                if value is not None and hasattr(invoice, field):
                    setattr(invoice, field, value)

            await self.db.commit()
            await self.db.refresh(invoice)
            return invoice
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = str(e.orig).lower()

            # Check which constraint was violated
            if "foreign key" in error_msg and "student" in error_msg:
                raise ForeignKeyViolationException(
                    "Invoice", "student_id", kwargs.get("student_id", "unknown")
                )
            else:
                raise DatabaseOperationException("update", "Invoice", str(e.orig))
        except DataError as e:
            await self.db.rollback()
            raise InvalidDataException("Invoice", str(e.orig))
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except ForeignKeyViolationException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("update", "Invoice", str(e))

    async def delete(self, invoice_id: int) -> bool:
        """
        Delete an invoice.

        Args:
            invoice_id: ID of the invoice to delete

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            invoice = await self.get(invoice_id)
            if not invoice:
                return False

            await self.db.delete(invoice)
            await self.db.commit()
            return True
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("delete", "Invoice", str(e))

    async def get_paid_amount(self, invoice_id: int) -> Decimal:
        """
        Calculate total paid amount for an invoice.

        Args:
            invoice_id: ID of the invoice

        Returns:
            Total paid amount as Decimal

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            result = await self.db.execute(
                select(func.coalesce(func.sum(Payment.amount), 0)).filter(
                    Payment.invoice_id == invoice_id
                )
            )
            amount = result.scalar()
            return Decimal(str(amount))
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get_paid_amount", "Invoice", str(e))

    async def update_status_based_on_payments(
        self, invoice_id: int
    ) -> Optional[Invoice]:
        """
        Update invoice status based on payment amount.

        Args:
            invoice_id: ID of the invoice

        Returns:
            Updated Invoice instance or None if not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            invoice = await self.get(invoice_id)
            if not invoice:
                return None

            paid_amount = await self.get_paid_amount(invoice_id)
            invoice_amount = Decimal(str(invoice.amount))

            if paid_amount >= invoice_amount:
                invoice.status = InvoiceStatus.PAID
                await self.db.commit()
                await self.db.refresh(invoice)

            return invoice
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException(
                "update_status_based_on_payments", "Invoice", str(e)
            )
