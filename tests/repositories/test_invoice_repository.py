"""
Unit tests for InvoiceRepository

Tests CRUD operations, invoice number generation, and status updates for invoices.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from decimal import Decimal
from datetime import date

from app.core.database import Base
from app.db.models import School, Student, Invoice, Payment, InvoiceStatus, PaymentMethod
from app.repositories.school_repository import SchoolRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.core.exceptions import ForeignKeyViolationException

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_invoice_repository.db"
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


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
    return await repo.create(
        school_id=school.id,
        first_name="John",
        last_name="Doe"
    )


class TestInvoiceNumberGeneration:
    """Tests for invoice number generation"""

    @pytest.mark.asyncio
    async def test_generate_first_invoice_number(self, db_session):
        """Test generating the first invoice number"""
        repo = InvoiceRepository(db_session)
        invoice_number = await repo.generate_invoice_number()
        assert invoice_number == "INV-000001"

    @pytest.mark.asyncio
    async def test_generate_sequential_invoice_numbers(self, db_session, student):
        """Test that invoice numbers are sequential"""
        repo = InvoiceRepository(db_session)

        # Create first invoice
        invoice1 = await repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )
        assert invoice1.invoice_number == "INV-000001"

        # Create second invoice
        invoice2 = await repo.create(
            student_id=student.id,
            amount=Decimal("200.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )
        assert invoice2.invoice_number == "INV-000002"

        # Create third invoice
        invoice3 = await repo.create(
            student_id=student.id,
            amount=Decimal("300.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )
        assert invoice3.invoice_number == "INV-000003"

    @pytest.mark.asyncio
    async def test_invoice_number_format(self, db_session, student):
        """Test invoice number format with leading zeros"""
        repo = InvoiceRepository(db_session)

        # Create 10 invoices to test leading zeros
        for i in range(10):
            invoice = await repo.create(
                student_id=student.id,
                amount=Decimal("100.00"),
                due_date=date(2024, 12, 31),
                issue_date=date(2024, 1, 1)
            )

        # Last invoice should be INV-000010
        assert invoice.invoice_number == "INV-000010"


class TestInvoiceRepositoryCRUD:
    """Tests for Invoice CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_invoice_with_all_fields(self, db_session, student):
        """Test creating an invoice with all fields"""
        repo = InvoiceRepository(db_session)
        invoice = await repo.create(
            student_id=student.id,
            amount=Decimal("100.50"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
            description="Test invoice",
            status=InvoiceStatus.PENDING
        )

        assert invoice.id is not None
        assert invoice.student_id == student.id
        assert invoice.amount == Decimal("100.50")
        assert invoice.due_date == date(2024, 12, 31)
        assert invoice.issue_date == date(2024, 1, 1)
        assert invoice.description == "Test invoice"
        assert invoice.status == InvoiceStatus.PENDING
        assert invoice.invoice_number.startswith("INV-")

    @pytest.mark.asyncio
    async def test_create_invoice_with_minimal_fields(self, db_session, student):
        """Test creating an invoice with only required fields"""
        repo = InvoiceRepository(db_session)
        invoice = await repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )

        assert invoice.id is not None
        assert invoice.student_id == student.id
        assert invoice.amount == Decimal("100.00")
        assert invoice.description is None
        assert invoice.status == InvoiceStatus.PENDING  # Default status

    @pytest.mark.asyncio
    async def test_get_existing_invoice(self, db_session, student):
        """Test getting an existing invoice by ID"""
        repo = InvoiceRepository(db_session)
        created_invoice = await repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )

        retrieved_invoice = await repo.get(created_invoice.id)

        assert retrieved_invoice is not None
        assert retrieved_invoice.id == created_invoice.id
        assert retrieved_invoice.amount == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_get_nonexistent_invoice_returns_none(self, db_session):
        """Test getting a non-existent invoice returns None"""
        repo = InvoiceRepository(db_session)
        invoice = await repo.get(999)
        assert invoice is None

    @pytest.mark.asyncio
    async def test_get_all_invoices(self, db_session, student):
        """Test getting all invoices"""
        repo = InvoiceRepository(db_session)

        # Create multiple invoices
        await repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )
        await repo.create(
            student_id=student.id,
            amount=Decimal("200.00"),
            due_date=date(2024, 11, 30),
            issue_date=date(2024, 1, 1)
        )
        await repo.create(
            student_id=student.id,
            amount=Decimal("300.00"),
            due_date=date(2024, 10, 31),
            issue_date=date(2024, 1, 1)
        )

        invoices = await repo.get_all()

        assert len(invoices) == 3
        amounts = [inv.amount for inv in invoices]
        assert Decimal("100.00") in amounts
        assert Decimal("200.00") in amounts
        assert Decimal("300.00") in amounts

    @pytest.mark.asyncio
    async def test_get_all_with_student_filter(self, db_session, school):
        """Test getting invoices filtered by student"""
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)

        # Create two students
        student1 = await student_repo.create(
            school_id=school.id,
            first_name="John",
            last_name="Doe"
        )
        student2 = await student_repo.create(
            school_id=school.id,
            first_name="Jane",
            last_name="Smith"
        )

        # Create invoices for both students
        await invoice_repo.create(
            student_id=student1.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )
        await invoice_repo.create(
            student_id=student1.id,
            amount=Decimal("200.00"),
            due_date=date(2024, 11, 30),
            issue_date=date(2024, 1, 1)
        )
        await invoice_repo.create(
            student_id=student2.id,
            amount=Decimal("300.00"),
            due_date=date(2024, 10, 31),
            issue_date=date(2024, 1, 1)
        )

        # Get invoices for student1 only
        student1_invoices = await invoice_repo.get_all(student_id=student1.id)

        assert len(student1_invoices) == 2
        for invoice in student1_invoices:
            assert invoice.student_id == student1.id

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, db_session, student):
        """Test getting invoices with pagination"""
        repo = InvoiceRepository(db_session)

        # Create 5 invoices
        for i in range(5):
            await repo.create(
                student_id=student.id,
                amount=Decimal(f"{(i+1) * 100}.00"),
                due_date=date(2024, 12, 31),
                issue_date=date(2024, 1, 1)
            )

        # Get first 2 invoices
        page1 = await repo.get_all(skip=0, limit=2)
        assert len(page1) == 2

        # Get next 2 invoices
        page2 = await repo.get_all(skip=2, limit=2)
        assert len(page2) == 2

        # Get last invoice
        page3 = await repo.get_all(skip=4, limit=2)
        assert len(page3) == 1

    @pytest.mark.asyncio
    async def test_update_invoice_all_fields(self, db_session, student):
        """Test updating all fields of an invoice"""
        repo = InvoiceRepository(db_session)
        invoice = await repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )

        updated_invoice = await repo.update(
            invoice.id,
            amount=Decimal("200.00"),
            due_date=date(2024, 11, 30),
            description="Updated invoice",
            status=InvoiceStatus.PAID
        )

        assert updated_invoice is not None
        assert updated_invoice.id == invoice.id
        assert updated_invoice.amount == Decimal("200.00")
        assert updated_invoice.due_date == date(2024, 11, 30)
        assert updated_invoice.description == "Updated invoice"
        assert updated_invoice.status == InvoiceStatus.PAID

    @pytest.mark.asyncio
    async def test_update_invoice_partial_fields(self, db_session, student):
        """Test updating only some fields of an invoice"""
        repo = InvoiceRepository(db_session)
        invoice = await repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
            description="Original"
        )

        updated_invoice = await repo.update(invoice.id, description="Updated")

        assert updated_invoice.description == "Updated"
        assert updated_invoice.amount == Decimal("100.00")
        assert updated_invoice.due_date == date(2024, 12, 31)

    @pytest.mark.asyncio
    async def test_update_nonexistent_invoice_returns_none(self, db_session):
        """Test updating a non-existent invoice returns None"""
        repo = InvoiceRepository(db_session)
        updated_invoice = await repo.update(999, amount=Decimal("200.00"))
        assert updated_invoice is None

    @pytest.mark.asyncio
    async def test_delete_existing_invoice(self, db_session, student):
        """Test deleting an existing invoice"""
        repo = InvoiceRepository(db_session)
        invoice = await repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )

        result = await repo.delete(invoice.id)
        assert result is True

        # Verify invoice is deleted
        deleted_invoice = await repo.get(invoice.id)
        assert deleted_invoice is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_invoice_returns_false(self, db_session):
        """Test deleting a non-existent invoice returns False"""
        repo = InvoiceRepository(db_session)
        result = await repo.delete(999)
        assert result is False


class TestInvoicePaidAmount:
    """Tests for calculating paid amount on invoices"""

    @pytest.mark.asyncio
    async def test_get_paid_amount_no_payments(self, db_session, student):
        """Test getting paid amount for invoice with no payments"""
        invoice_repo = InvoiceRepository(db_session)
        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )

        paid_amount = await invoice_repo.get_paid_amount(invoice.id)
        assert paid_amount == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_paid_amount_single_payment(self, db_session, student):
        """Test getting paid amount for invoice with single payment"""
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )

        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("30.00"),
            payment_date=date(2024, 1, 15)
        )

        paid_amount = await invoice_repo.get_paid_amount(invoice.id)
        assert paid_amount == Decimal("30.00")

    @pytest.mark.asyncio
    async def test_get_paid_amount_multiple_payments(self, db_session, student):
        """Test getting paid amount for invoice with multiple payments"""
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )

        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("30.00"),
            payment_date=date(2024, 1, 15)
        )
        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("20.00"),
            payment_date=date(2024, 1, 20)
        )
        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("25.00"),
            payment_date=date(2024, 1, 25)
        )

        paid_amount = await invoice_repo.get_paid_amount(invoice.id)
        assert paid_amount == Decimal("75.00")

    @pytest.mark.asyncio
    async def test_get_paid_amount_full_payment(self, db_session, student):
        """Test getting paid amount when invoice is fully paid"""
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )

        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("100.00"),
            payment_date=date(2024, 1, 15)
        )

        paid_amount = await invoice_repo.get_paid_amount(invoice.id)
        assert paid_amount == Decimal("100.00")


class TestInvoiceStatusUpdate:
    """Tests for updating invoice status based on payments"""

    @pytest.mark.asyncio
    async def test_update_status_no_payments_stays_pending(self, db_session, student):
        """Test that invoice with no payments stays PENDING"""
        repo = InvoiceRepository(db_session)
        invoice = await repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
            status=InvoiceStatus.PENDING
        )

        updated_invoice = await repo.update_status_based_on_payments(invoice.id)

        assert updated_invoice.status == InvoiceStatus.PENDING

    @pytest.mark.asyncio
    async def test_update_status_partial_payment_stays_pending(self, db_session, student):
        """Test that invoice with partial payment stays PENDING"""
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
            status=InvoiceStatus.PENDING
        )

        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("30.00"),
            payment_date=date(2024, 1, 15)
        )

        updated_invoice = await invoice_repo.update_status_based_on_payments(invoice.id)

        assert updated_invoice.status == InvoiceStatus.PENDING

    @pytest.mark.asyncio
    async def test_update_status_full_payment_becomes_paid(self, db_session, student):
        """Test that invoice with full payment becomes PAID"""
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
            status=InvoiceStatus.PENDING
        )

        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("100.00"),
            payment_date=date(2024, 1, 15)
        )

        updated_invoice = await invoice_repo.update_status_based_on_payments(invoice.id)

        assert updated_invoice.status == InvoiceStatus.PAID

    @pytest.mark.asyncio
    async def test_update_status_multiple_payments_reaching_total(self, db_session, student):
        """Test that invoice becomes PAID when multiple payments reach total"""
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
            status=InvoiceStatus.PENDING
        )

        # First payment - should stay PENDING
        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("30.00"),
            payment_date=date(2024, 1, 15)
        )
        updated_invoice = await invoice_repo.update_status_based_on_payments(invoice.id)
        assert updated_invoice.status == InvoiceStatus.PENDING

        # Second payment - should stay PENDING
        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("40.00"),
            payment_date=date(2024, 1, 20)
        )
        updated_invoice = await invoice_repo.update_status_based_on_payments(invoice.id)
        assert updated_invoice.status == InvoiceStatus.PENDING

        # Third payment completing the total - should become PAID
        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("30.00"),
            payment_date=date(2024, 1, 25)
        )
        updated_invoice = await invoice_repo.update_status_based_on_payments(invoice.id)
        assert updated_invoice.status == InvoiceStatus.PAID

    @pytest.mark.asyncio
    async def test_update_status_nonexistent_invoice_returns_none(self, db_session):
        """Test that updating status of non-existent invoice returns None"""
        repo = InvoiceRepository(db_session)
        updated_invoice = await repo.update_status_based_on_payments(999)
        assert updated_invoice is None

    @pytest.mark.asyncio
    async def test_update_status_exact_amount_becomes_paid(self, db_session, student):
        """Test that invoice with exact payment amount becomes PAID"""
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("123.45"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
            status=InvoiceStatus.PENDING
        )

        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("123.45"),
            payment_date=date(2024, 1, 15)
        )

        updated_invoice = await invoice_repo.update_status_based_on_payments(invoice.id)

        assert updated_invoice.status == InvoiceStatus.PAID
