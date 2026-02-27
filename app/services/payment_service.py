"""Payment service for business logic"""
from typing import List, Optional
from decimal import Decimal
from app.repositories.payment_repository import PaymentRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.student_repository import StudentRepository
from app.schemas import Payment, PaymentCreate, PaymentUpdate
from app.services.event_service import event_service


class PaymentService:
    """Service for Payment business logic"""

    def __init__(
        self,
        repository: PaymentRepository,
        invoice_repository: InvoiceRepository,
        student_repository: StudentRepository
    ):
        self.repository = repository
        self.invoice_repository = invoice_repository
        self.student_repository = student_repository

    async def create_payment(self, schema: PaymentCreate) -> Optional[Payment]:
        """
        Create a new payment

        Args:
            schema: PaymentCreate schema with payment data

        Returns:
            Payment schema with created payment data, None if invoice doesn't exist

        Business Rules:
            - Invoice must exist before creating a payment
            - Payment amount cannot exceed remaining invoice balance
            - Invoice status is automatically updated to PAID when fully paid

        Raises:
            ValueError: If payment amount exceeds remaining balance
        """
        # Verify invoice exists
        invoice = await self.invoice_repository.get(schema.invoice_id)
        if not invoice:
            return None

        try:
            # Repository handles validation and invoice status update
            db_payment = await self.repository.create(
                invoice_id=schema.invoice_id,
                amount=schema.amount,
                payment_date=schema.payment_date,
                payment_method=schema.payment_method,
                reference=schema.reference
            )
            if not db_payment:
                return None

            # Publish payment_created event for async processing
            # Get student info to include school_id in event
            student = await self.student_repository.get(invoice.student_id)
            if student:
                await event_service.publish_payment_created(
                    payment_id=db_payment.id,
                    invoice_id=invoice.id,
                    student_id=student.id,
                    school_id=student.school_id,
                    amount=float(schema.amount),
                    user_id=None  # TODO: Add when auth is integrated
                )

            return Payment.model_validate(db_payment)
        except ValueError:
            # Payment amount exceeds remaining balance
            raise

    async def get_payment(self, payment_id: int) -> Optional[Payment]:
        """
        Get a payment by ID

        Args:
            payment_id: ID of the payment to retrieve

        Returns:
            Payment schema if found, None otherwise
        """
        db_payment = await self.repository.get(payment_id)
        if not db_payment:
            return None
        return Payment.model_validate(db_payment)

    async def get_all_payments(
        self,
        skip: int = 0,
        limit: int = 100,
        invoice_id: Optional[int] = None
    ) -> List[Payment]:
        """
        Get all payments with pagination and optional invoice filter

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            invoice_id: Optional invoice ID to filter by

        Returns:
            List of Payment schemas
        """
        db_payments = await self.repository.get_all(
            skip=skip,
            limit=limit,
            invoice_id=invoice_id
        )
        return [Payment.model_validate(payment) for payment in db_payments]

    async def update_payment(self, payment_id: int, schema: PaymentUpdate) -> Optional[Payment]:
        """
        Update a payment

        Args:
            payment_id: ID of the payment to update
            schema: PaymentUpdate schema with updated data

        Returns:
            Updated Payment schema if found, None otherwise

        Note:
            - Cannot update invoice_id (payments are tied to a specific invoice)
            - Updating payment amount may require recalculating invoice status
        """
        # Check if payment exists
        existing_payment = await self.repository.get(payment_id)
        if not existing_payment:
            return None

        # Prepare update data (only include fields that are set)
        update_data = schema.model_dump(exclude_unset=True)

        db_payment = await self.repository.update(payment_id, **update_data)
        if not db_payment:
            return None

        # If amount was updated, recalculate invoice status
        if 'amount' in update_data:
            await self.invoice_repository.update_status_based_on_payments(
                existing_payment.invoice_id
            )

        return Payment.model_validate(db_payment)

    async def delete_payment(self, payment_id: int) -> bool:
        """
        Delete a payment

        Args:
            payment_id: ID of the payment to delete

        Returns:
            True if deleted successfully, False otherwise

        Note:
            After deleting a payment, invoice status should be recalculated
        """
        # Check if payment exists and get invoice_id
        existing_payment = await self.repository.get(payment_id)
        if not existing_payment:
            return False

        invoice_id = existing_payment.invoice_id
        result = await self.repository.delete(payment_id)

        # Recalculate invoice status after deletion
        if result:
            await self.invoice_repository.update_status_based_on_payments(invoice_id)

        return result

    async def get_invoice_remaining_balance(self, invoice_id: int) -> Optional[Decimal]:
        """
        Calculate remaining balance for an invoice

        Args:
            invoice_id: ID of the invoice

        Returns:
            Remaining balance as Decimal, None if invoice doesn't exist
        """
        # Verify invoice exists
        invoice = await self.invoice_repository.get(invoice_id)
        if not invoice:
            return None

        paid_amount = await self.invoice_repository.get_paid_amount(invoice_id)
        invoice_amount = Decimal(str(invoice.amount))

        return invoice_amount - paid_amount
