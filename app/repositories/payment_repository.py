"""Payment repository for database operations"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError, DataError
from typing import List, Optional
from decimal import Decimal
from datetime import date

from app.db.models import Payment, Invoice, PaymentMethod, InvoiceStatus
from app.core.exceptions import (
    ForeignKeyViolationException,
    DatabaseConnectionException,
    DatabaseOperationException,
    InvalidDataException
)


class PaymentRepository:
    """Repository for Payment database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, invoice_id: int, amount: Decimal, payment_date: date,
                    payment_method: PaymentMethod = PaymentMethod.OTHER,
                    reference: Optional[str] = None) -> Optional[Payment]:
        """
        Create payment and update invoice status.

        Args:
            invoice_id: ID of the invoice
            amount: Payment amount
            payment_date: Date of payment
            payment_method: Payment method (default: OTHER)
            reference: Payment reference (optional)

        Returns:
            Created Payment instance or None if invoice not found

        Raises:
            ForeignKeyViolationException: If invoice_id doesn't exist
            InvalidDataException: If payment amount exceeds remaining balance or data validation fails
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails for other reasons
        """
        try:
            from app.repositories.invoice_repository import InvoiceRepository

            invoice_repo = InvoiceRepository(self.db)
            invoice = await invoice_repo.get(invoice_id)
            if not invoice:
                return None

            # Calculate current paid amount
            paid_amount = await invoice_repo.get_paid_amount(invoice_id)
            remaining = Decimal(str(invoice.amount)) - paid_amount

            # Validate payment amount doesn't exceed remaining balance
            if amount > remaining:
                raise InvalidDataException(
                    "Payment",
                    f"Payment amount ({amount}) exceeds remaining balance ({remaining})"
                )

            # Create payment
            payment = Payment(
                invoice_id=invoice_id,
                amount=amount,
                payment_date=payment_date,
                payment_method=payment_method,
                reference=reference
            )
            self.db.add(payment)

            # Update invoice status
            new_paid_amount = paid_amount + amount
            if new_paid_amount >= Decimal(str(invoice.amount)):
                invoice.status = InvoiceStatus.PAID

            await self.db.commit()
            await self.db.refresh(payment)
            return payment
        except InvalidDataException:
            # Re-raise our custom exception
            await self.db.rollback()
            raise
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = str(e.orig).lower()

            # Check which constraint was violated
            if 'foreign key' in error_msg and 'invoice' in error_msg:
                raise ForeignKeyViolationException("Payment", "invoice_id", invoice_id)
            else:
                raise DatabaseOperationException("create", "Payment", str(e.orig))
        except DataError as e:
            await self.db.rollback()
            raise InvalidDataException("Payment", str(e.orig))
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("create", "Payment", str(e))

    async def get(self, payment_id: int) -> Optional[Payment]:
        """
        Get a payment by ID.

        Args:
            payment_id: ID of the payment

        Returns:
            Payment instance or None if not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            result = await self.db.execute(
                select(Payment).filter(Payment.id == payment_id)
            )
            return result.scalar_one_or_none()
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get", "Payment", str(e))

    async def get_all(self, skip: int = 0, limit: int = 100,
                     invoice_id: Optional[int] = None) -> List[Payment]:
        """
        Get all payments with pagination and optional invoice filter.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            invoice_id: Optional invoice ID filter

        Returns:
            List of Payment instances

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            query = select(Payment)
            if invoice_id:
                query = query.filter(Payment.invoice_id == invoice_id)
            query = query.offset(skip).limit(limit)

            result = await self.db.execute(query)
            return list(result.scalars().all())
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get_all", "Payment", str(e))

    async def update(self, payment_id: int, **kwargs) -> Optional[Payment]:
        """
        Update a payment.

        Args:
            payment_id: ID of the payment to update
            **kwargs: Fields to update

        Returns:
            Updated Payment instance or None if not found

        Raises:
            ForeignKeyViolationException: If invoice_id doesn't exist
            DatabaseConnectionException: If database connection fails
            InvalidDataException: If data validation fails
            DatabaseOperationException: If operation fails for other reasons
        """
        try:
            payment = await self.get(payment_id)
            if not payment:
                return None

            for field, value in kwargs.items():
                if value is not None and hasattr(payment, field):
                    setattr(payment, field, value)

            await self.db.commit()
            await self.db.refresh(payment)
            return payment
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = str(e.orig).lower()

            # Check which constraint was violated
            if 'foreign key' in error_msg and 'invoice' in error_msg:
                raise ForeignKeyViolationException("Payment", "invoice_id", kwargs.get('invoice_id', 'unknown'))
            else:
                raise DatabaseOperationException("update", "Payment", str(e.orig))
        except DataError as e:
            await self.db.rollback()
            raise InvalidDataException("Payment", str(e.orig))
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("update", "Payment", str(e))

    async def delete(self, payment_id: int) -> bool:
        """
        Delete a payment.

        Args:
            payment_id: ID of the payment to delete

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            payment = await self.get(payment_id)
            if not payment:
                return False

            await self.db.delete(payment)
            await self.db.commit()
            return True
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("delete", "Payment", str(e))
