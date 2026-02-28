"""
Unit tests for PaymentRepository

Tests CRUD operations and payment validation for payments.
"""

from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.core.database import Base
from app.core.exceptions import InvalidDataException
from app.db.models import (Invoice, InvoiceStatus, Payment, PaymentMethod,
                           School, Student)
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.school_repository import SchoolRepository
from app.repositories.student_repository import StudentRepository

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_payment_repository.db"
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database():
    """Setup database before each test"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Get database session for testing"""
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def school(db_session):
    """Create a test school"""
    repo = SchoolRepository(db_session)
    return await repo.create(name="Test School")


@pytest_asyncio.fixture
async def student(db_session, school):
    """Create a test student"""
    repo = StudentRepository(db_session)
    return await repo.create(school_id=school.id, first_name="John", last_name="Doe")


@pytest_asyncio.fixture
async def invoice(db_session, student):
    """Create a test invoice"""
    repo = InvoiceRepository(db_session)
    return await repo.create(
        student_id=student.id,
        amount=Decimal("100.00"),
        due_date=date(2024, 12, 31),
        issue_date=date(2024, 1, 1),
    )


class TestPaymentRepositoryCRUD:
    """Tests for Payment CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_payment_with_all_fields(self, db_session, invoice):
        """Test creating a payment with all fields"""
        repo = PaymentRepository(db_session)
        payment = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 15),
            payment_method=PaymentMethod.CASH,
            reference="REF-12345",
        )

        assert payment is not None
        assert payment.id is not None
        assert payment.invoice_id == invoice.id
        assert payment.amount == Decimal("50.00")
        assert payment.payment_date == date(2024, 1, 15)
        assert payment.payment_method == PaymentMethod.CASH
        assert payment.reference == "REF-12345"

    @pytest.mark.asyncio
    async def test_create_payment_with_minimal_fields(self, db_session, invoice):
        """Test creating a payment with only required fields"""
        repo = PaymentRepository(db_session)
        payment = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 15),
        )

        assert payment is not None
        assert payment.id is not None
        assert payment.invoice_id == invoice.id
        assert payment.amount == Decimal("50.00")
        assert payment.payment_method == PaymentMethod.OTHER  # Default
        assert payment.reference is None

    @pytest.mark.asyncio
    async def test_create_payment_updates_invoice_status_to_paid(
        self, db_session, invoice
    ):
        """Test that creating full payment updates invoice status to PAID"""
        repo = PaymentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)

        # Verify invoice starts as PENDING
        assert invoice.status == InvoiceStatus.PENDING

        # Create full payment
        payment = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("100.00"),
            payment_date=date(2024, 1, 15),
        )

        # Refresh invoice and check status
        await db_session.refresh(invoice)
        assert invoice.status == InvoiceStatus.PAID

    @pytest.mark.asyncio
    async def test_create_partial_payment_keeps_invoice_pending(
        self, db_session, invoice
    ):
        """Test that creating partial payment keeps invoice as PENDING"""
        repo = PaymentRepository(db_session)

        # Create partial payment
        payment = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("30.00"),
            payment_date=date(2024, 1, 15),
        )

        # Refresh invoice and check status
        await db_session.refresh(invoice)
        assert invoice.status == InvoiceStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_payment_with_different_payment_methods(
        self, db_session, student
    ):
        """Test creating payments with different payment methods"""
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        # Create multiple invoices for different payment methods
        invoice1 = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
        )
        invoice2 = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
        )
        invoice3 = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
        )

        # Create payments with different methods
        payment1 = await payment_repo.create(
            invoice_id=invoice1.id,
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 15),
            payment_method=PaymentMethod.CASH,
        )
        payment2 = await payment_repo.create(
            invoice_id=invoice2.id,
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 15),
            payment_method=PaymentMethod.CARD,
        )
        payment3 = await payment_repo.create(
            invoice_id=invoice3.id,
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 15),
            payment_method=PaymentMethod.TRANSFER,
        )

        assert payment1.payment_method == PaymentMethod.CASH
        assert payment2.payment_method == PaymentMethod.CARD
        assert payment3.payment_method == PaymentMethod.TRANSFER

    @pytest.mark.asyncio
    async def test_get_existing_payment(self, db_session, invoice):
        """Test getting an existing payment by ID"""
        repo = PaymentRepository(db_session)
        created_payment = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 15),
        )

        retrieved_payment = await repo.get(created_payment.id)

        assert retrieved_payment is not None
        assert retrieved_payment.id == created_payment.id
        assert retrieved_payment.amount == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_get_nonexistent_payment_returns_none(self, db_session):
        """Test getting a non-existent payment returns None"""
        repo = PaymentRepository(db_session)
        payment = await repo.get(999)
        assert payment is None

    @pytest.mark.asyncio
    async def test_get_all_payments(self, db_session, invoice):
        """Test getting all payments"""
        repo = PaymentRepository(db_session)

        # Create multiple payments
        await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("30.00"),
            payment_date=date(2024, 1, 15),
        )
        await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("40.00"),
            payment_date=date(2024, 1, 20),
        )
        await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("30.00"),
            payment_date=date(2024, 1, 25),
        )

        payments = await repo.get_all()

        assert len(payments) == 3
        amounts = [p.amount for p in payments]
        assert Decimal("30.00") in amounts
        assert Decimal("40.00") in amounts

    @pytest.mark.asyncio
    async def test_get_all_with_invoice_filter(self, db_session, student):
        """Test getting payments filtered by invoice"""
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        # Create two invoices
        invoice1 = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
        )
        invoice2 = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("200.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
        )

        # Create payments for both invoices
        await payment_repo.create(
            invoice_id=invoice1.id,
            amount=Decimal("30.00"),
            payment_date=date(2024, 1, 15),
        )
        await payment_repo.create(
            invoice_id=invoice1.id,
            amount=Decimal("40.00"),
            payment_date=date(2024, 1, 20),
        )
        await payment_repo.create(
            invoice_id=invoice2.id,
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 25),
        )

        # Get payments for invoice1 only
        invoice1_payments = await payment_repo.get_all(invoice_id=invoice1.id)

        assert len(invoice1_payments) == 2
        for payment in invoice1_payments:
            assert payment.invoice_id == invoice1.id

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, db_session, invoice):
        """Test getting payments with pagination"""
        repo = PaymentRepository(db_session)

        # Create 5 payments
        for i in range(5):
            await repo.create(
                invoice_id=invoice.id,
                amount=Decimal("10.00"),
                payment_date=date(2024, 1, 15 + i),
            )

        # Get first 2 payments
        page1 = await repo.get_all(skip=0, limit=2)
        assert len(page1) == 2

        # Get next 2 payments
        page2 = await repo.get_all(skip=2, limit=2)
        assert len(page2) == 2

        # Get last payment
        page3 = await repo.get_all(skip=4, limit=2)
        assert len(page3) == 1

    @pytest.mark.asyncio
    async def test_update_payment_all_fields(self, db_session, invoice):
        """Test updating all fields of a payment"""
        repo = PaymentRepository(db_session)
        payment = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 15),
            payment_method=PaymentMethod.CASH,
        )

        updated_payment = await repo.update(
            payment.id,
            amount=Decimal("60.00"),
            payment_date=date(2024, 1, 20),
            payment_method=PaymentMethod.CARD,
            reference="NEW-REF",
        )

        assert updated_payment is not None
        assert updated_payment.id == payment.id
        assert updated_payment.amount == Decimal("60.00")
        assert updated_payment.payment_date == date(2024, 1, 20)
        assert updated_payment.payment_method == PaymentMethod.CARD
        assert updated_payment.reference == "NEW-REF"

    @pytest.mark.asyncio
    async def test_update_payment_partial_fields(self, db_session, invoice):
        """Test updating only some fields of a payment"""
        repo = PaymentRepository(db_session)
        payment = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 15),
            payment_method=PaymentMethod.CASH,
        )

        updated_payment = await repo.update(payment.id, reference="REF-123")

        assert updated_payment.reference == "REF-123"
        assert updated_payment.amount == Decimal("50.00")
        assert updated_payment.payment_method == PaymentMethod.CASH

    @pytest.mark.asyncio
    async def test_update_nonexistent_payment_returns_none(self, db_session):
        """Test updating a non-existent payment returns None"""
        repo = PaymentRepository(db_session)
        updated_payment = await repo.update(999, amount=Decimal("100.00"))
        assert updated_payment is None

    @pytest.mark.asyncio
    async def test_delete_existing_payment(self, db_session, invoice):
        """Test deleting an existing payment"""
        repo = PaymentRepository(db_session)
        payment = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 15),
        )

        result = await repo.delete(payment.id)
        assert result is True

        # Verify payment is deleted
        deleted_payment = await repo.get(payment.id)
        assert deleted_payment is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_payment_returns_false(self, db_session):
        """Test deleting a non-existent payment returns False"""
        repo = PaymentRepository(db_session)
        result = await repo.delete(999)
        assert result is False


class TestPaymentValidation:
    """Tests for payment validation logic"""

    @pytest.mark.asyncio
    async def test_create_payment_for_nonexistent_invoice_returns_none(
        self, db_session
    ):
        """Test that creating payment for non-existent invoice returns None"""
        repo = PaymentRepository(db_session)
        payment = await repo.create(
            invoice_id=999, amount=Decimal("50.00"), payment_date=date(2024, 1, 15)
        )
        assert payment is None

    @pytest.mark.asyncio
    async def test_create_payment_within_balance_succeeds(self, db_session, invoice):
        """Test creating payment within invoice balance succeeds"""
        repo = PaymentRepository(db_session)
        payment = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 15),
        )
        assert payment is not None
        assert payment.amount == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_create_payment_equal_to_balance_succeeds(self, db_session, invoice):
        """Test creating payment equal to invoice balance succeeds"""
        repo = PaymentRepository(db_session)
        payment = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("100.00"),
            payment_date=date(2024, 1, 15),
        )
        assert payment is not None
        assert payment.amount == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_create_payment_within_remaining_balance_succeeds(
        self, db_session, invoice
    ):
        """Test creating payment within remaining balance after previous payments succeeds"""
        repo = PaymentRepository(db_session)

        # First payment
        await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("30.00"),
            payment_date=date(2024, 1, 15),
        )

        # Second payment within remaining balance (70)
        payment = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 20),
        )
        assert payment is not None
        assert payment.amount == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_create_payment_equal_to_remaining_balance_succeeds(
        self, db_session, invoice
    ):
        """Test creating payment equal to remaining balance succeeds"""
        repo = PaymentRepository(db_session)

        # First payment
        await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("40.00"),
            payment_date=date(2024, 1, 15),
        )

        # Second payment equal to remaining balance (60)
        payment = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("60.00"),
            payment_date=date(2024, 1, 20),
        )
        assert payment is not None

        # Invoice should now be paid
        await db_session.refresh(invoice)
        assert invoice.status == InvoiceStatus.PAID

    @pytest.mark.asyncio
    async def test_create_multiple_partial_payments_completing_invoice(
        self, db_session, invoice
    ):
        """Test creating multiple partial payments that complete the invoice"""
        repo = PaymentRepository(db_session)

        # First payment
        payment1 = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("25.00"),
            payment_date=date(2024, 1, 15),
        )
        assert payment1 is not None

        # Second payment
        payment2 = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("25.00"),
            payment_date=date(2024, 1, 20),
        )
        assert payment2 is not None

        # Third payment
        payment3 = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("25.00"),
            payment_date=date(2024, 1, 25),
        )
        assert payment3 is not None

        # Fourth payment completing the invoice
        payment4 = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("25.00"),
            payment_date=date(2024, 1, 30),
        )
        assert payment4 is not None

        # Invoice should now be paid
        await db_session.refresh(invoice)
        assert invoice.status == InvoiceStatus.PAID

    @pytest.mark.asyncio
    async def test_create_payment_with_decimal_precision(self, db_session, student):
        """Test creating payments with decimal precision"""
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("123.45"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
        )

        # First payment with decimal
        payment1 = await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("50.25"),
            payment_date=date(2024, 1, 15),
        )
        assert payment1.amount == Decimal("50.25")

        # Second payment completing the invoice with decimal
        payment2 = await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("73.20"),
            payment_date=date(2024, 1, 20),
        )
        assert payment2.amount == Decimal("73.20")

        # Invoice should now be paid
        await db_session.refresh(invoice)
        assert invoice.status == InvoiceStatus.PAID


class TestPaymentRollback:
    """Tests that payment transactions are rolled back on validation failures"""

    @pytest.mark.asyncio
    async def test_exceeding_payment_does_not_create_payment(self, db_session, invoice):
        """Test that payment exceeding balance is not created"""
        repo = PaymentRepository(db_session)

        try:
            await repo.create(
                invoice_id=invoice.id,
                amount=Decimal("150.00"),
                payment_date=date(2024, 1, 15),
            )
        except InvalidDataException:
            pass

        # Verify no payments exist
        all_payments = await repo.get_all()
        assert len(all_payments) == 0

    @pytest.mark.asyncio
    async def test_exceeding_payment_does_not_update_invoice_status(
        self, db_session, invoice
    ):
        """Test that failed payment doesn't update invoice status"""
        repo = PaymentRepository(db_session)

        try:
            await repo.create(
                invoice_id=invoice.id,
                amount=Decimal("150.00"),
                payment_date=date(2024, 1, 15),
            )
        except InvalidDataException:
            pass

        # Verify invoice status unchanged
        await db_session.refresh(invoice)
        assert invoice.status == InvoiceStatus.PENDING

    @pytest.mark.asyncio
    async def test_partial_then_exceeding_payment_does_not_persist(
        self, db_session, invoice
    ):
        """Test that exceeding payment after partial payment doesn't persist"""
        repo = PaymentRepository(db_session)

        # First valid partial payment
        payment1 = await repo.create(
            invoice_id=invoice.id,
            amount=Decimal("60.00"),
            payment_date=date(2024, 1, 15),
        )
        assert payment1 is not None

        # Try to create exceeding payment
        try:
            await repo.create(
                invoice_id=invoice.id,
                amount=Decimal("50.00"),  # Would total 110, exceeds 100
                payment_date=date(2024, 1, 20),
            )
        except InvalidDataException:
            pass

        # Verify only first payment exists
        all_payments = await repo.get_all()
        assert len(all_payments) == 1
        assert all_payments[0].amount == Decimal("60.00")

        # Verify invoice still pending
        await db_session.refresh(invoice)
        assert invoice.status == InvoiceStatus.PENDING
