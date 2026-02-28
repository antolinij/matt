"""Invoice service for business logic"""

from decimal import Decimal
from typing import List, Optional

from app.core.exceptions import ForeignKeyViolationException
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.student_repository import StudentRepository
from app.schemas import Invoice, InvoiceCreate, InvoiceUpdate
from app.services.event_service import event_service


class InvoiceService:
    """Service for Invoice business logic"""

    def __init__(
        self, repository: InvoiceRepository, student_repository: StudentRepository
    ):
        self.repository = repository
        self.student_repository = student_repository

    async def create_invoice(self, schema: InvoiceCreate) -> Optional[Invoice]:
        """
        Create a new invoice

        Args:
            schema: InvoiceCreate schema with invoice data

        Returns:
            Invoice schema with created invoice data, None if student doesn't exist

        Business Rules:
            - Student must exist before creating an invoice
            - Invoice number is auto-generated
            - Amount must be greater than 0
        """
        # Verify student exists
        student = await self.student_repository.get(schema.student_id)
        if not student:
            raise ForeignKeyViolationException(
                "Invoice", "student_id", schema.student_id
            )

        db_invoice = await self.repository.create(
            student_id=schema.student_id,
            amount=schema.amount,
            due_date=schema.due_date,
            issue_date=schema.issue_date,
            description=schema.description,
            status=schema.status,
        )

        # Publish invoice_created event for async processing
        await event_service.publish_invoice_created(
            invoice_id=db_invoice.id,
            student_id=student.id,
            school_id=student.school_id,
            amount=float(schema.amount),
            user_id=None,  # TODO: Add when auth is integrated
        )

        return Invoice.model_validate(db_invoice)

    async def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """
        Get an invoice by ID

        Args:
            invoice_id: ID of the invoice to retrieve

        Returns:
            Invoice schema if found, None otherwise
        """
        db_invoice = await self.repository.get(invoice_id)
        if not db_invoice:
            return None
        return Invoice.model_validate(db_invoice)

    async def get_all_invoices(
        self, skip: int = 0, limit: int = 100, student_id: Optional[int] = None
    ) -> List[Invoice]:
        """
        Get all invoices with pagination and optional student filter

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            student_id: Optional student ID to filter by

        Returns:
            List of Invoice schemas
        """
        db_invoices = await self.repository.get_all(
            skip=skip, limit=limit, student_id=student_id
        )
        return [Invoice.model_validate(invoice) for invoice in db_invoices]

    async def update_invoice(
        self, invoice_id: int, schema: InvoiceUpdate
    ) -> Optional[Invoice]:
        """
        Update an invoice

        Args:
            invoice_id: ID of the invoice to update
            schema: InvoiceUpdate schema with updated data

        Returns:
            Updated Invoice schema if found, None otherwise

        Business Rules:
            - If changing student_id, new student must exist
            - Cannot update invoice_number (it's auto-generated)
        """
        # Check if invoice exists
        existing_invoice = await self.repository.get(invoice_id)
        if not existing_invoice:
            return None

        # If updating student_id, verify new student exists
        update_data = schema.model_dump(exclude_unset=True)
        if "student_id" in update_data:
            new_student = await self.student_repository.get(update_data["student_id"])
            if not new_student:
                raise ForeignKeyViolationException(
                    "Invoice", "student_id", update_data["student_id"]
                )

        # Track old amount for event publishing
        old_amount = float(existing_invoice.amount)
        amount_changed = "amount" in update_data

        db_invoice = await self.repository.update(invoice_id, **update_data)
        if not db_invoice:
            return None

        # Publish invoice_updated event if amount changed
        if amount_changed:
            # Get student info for event
            student = await self.student_repository.get(db_invoice.student_id)
            if student:
                await event_service.publish_invoice_updated(
                    invoice_id=db_invoice.id,
                    student_id=student.id,
                    school_id=student.school_id,
                    old_amount=old_amount,
                    new_amount=float(db_invoice.amount),
                    user_id=None,  # TODO: Add when auth is integrated
                )

        return Invoice.model_validate(db_invoice)

    async def delete_invoice(self, invoice_id: int) -> bool:
        """
        Delete an invoice

        Args:
            invoice_id: ID of the invoice to delete

        Returns:
            True if deleted successfully, False otherwise

        Note:
            This will cascade delete all related payments
        """
        # Check if invoice exists
        existing_invoice = await self.repository.get(invoice_id)
        if not existing_invoice:
            return False

        return await self.repository.delete(invoice_id)

    async def get_paid_amount(self, invoice_id: int) -> Optional[Decimal]:
        """
        Get total paid amount for an invoice

        Args:
            invoice_id: ID of the invoice

        Returns:
            Total paid amount as Decimal, None if invoice doesn't exist
        """
        # Check if invoice exists
        existing_invoice = await self.repository.get(invoice_id)
        if not existing_invoice:
            return None

        return await self.repository.get_paid_amount(invoice_id)

    async def update_status_based_on_payments(
        self, invoice_id: int
    ) -> Optional[Invoice]:
        """
        Update invoice status based on payment amount

        Args:
            invoice_id: ID of the invoice

        Returns:
            Updated Invoice schema if found, None otherwise

        Business Rules:
            - If total paid amount >= invoice amount, status becomes PAID
        """
        db_invoice = await self.repository.update_status_based_on_payments(invoice_id)
        if not db_invoice:
            return None
        return Invoice.model_validate(db_invoice)
