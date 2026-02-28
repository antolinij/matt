"""
Unit tests for StudentRepository

Tests CRUD operations and account status methods for students.
"""

from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.core.database import Base
from app.core.exceptions import (DuplicateRecordException,
                                 ForeignKeyViolationException)
from app.db.models import (Invoice, InvoiceStatus, Payment, School, Student,
                           StudentStatus)
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.school_repository import SchoolRepository
from app.repositories.student_repository import StudentRepository

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_student_repository.db"
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


class TestStudentRepositoryCRUD:
    """Tests for Student CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_student_with_all_fields(self, db_session, school):
        """Test creating a student with all fields"""
        repo = StudentRepository(db_session)
        student = await repo.create(
            school_id=school.id,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            enrollment_date=date(2024, 1, 1),
            status=StudentStatus.ACTIVE,
        )

        assert student.id is not None
        assert student.school_id == school.id
        assert student.first_name == "John"
        assert student.last_name == "Doe"
        assert student.email == "john.doe@example.com"
        assert student.enrollment_date == date(2024, 1, 1)
        assert student.status == StudentStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_create_student_with_minimal_fields(self, db_session, school):
        """Test creating a student with only required fields"""
        repo = StudentRepository(db_session)
        student = await repo.create(
            school_id=school.id, first_name="Jane", last_name="Smith"
        )

        assert student.id is not None
        assert student.school_id == school.id
        assert student.first_name == "Jane"
        assert student.last_name == "Smith"
        assert student.email is None
        assert student.status == StudentStatus.ACTIVE  # Default status

    @pytest.mark.asyncio
    async def test_create_student_with_same_email_allowed(self, db_session, school):
        """Test that creating students with same email is allowed (no unique constraint)"""
        repo = StudentRepository(db_session)

        # Create first student
        student1 = await repo.create(
            school_id=school.id,
            first_name="John",
            last_name="Doe",
            email="same@example.com",
        )

        # Create second student with same email - should succeed
        student2 = await repo.create(
            school_id=school.id,
            first_name="Jane",
            last_name="Smith",
            email="same@example.com",
        )

        assert student1.id is not None
        assert student2.id is not None
        assert student1.email == student2.email

    @pytest.mark.asyncio
    async def test_get_existing_student(self, db_session, school):
        """Test getting an existing student by ID"""
        repo = StudentRepository(db_session)
        created_student = await repo.create(
            school_id=school.id, first_name="John", last_name="Doe"
        )

        retrieved_student = await repo.get(created_student.id)

        assert retrieved_student is not None
        assert retrieved_student.id == created_student.id
        assert retrieved_student.first_name == "John"
        assert retrieved_student.last_name == "Doe"

    @pytest.mark.asyncio
    async def test_get_nonexistent_student_returns_none(self, db_session):
        """Test getting a non-existent student returns None"""
        repo = StudentRepository(db_session)
        student = await repo.get(999)
        assert student is None

    @pytest.mark.asyncio
    async def test_get_all_students(self, db_session, school):
        """Test getting all students"""
        repo = StudentRepository(db_session)

        # Create multiple students
        await repo.create(school_id=school.id, first_name="John", last_name="Doe")
        await repo.create(school_id=school.id, first_name="Jane", last_name="Smith")
        await repo.create(school_id=school.id, first_name="Bob", last_name="Johnson")

        students = await repo.get_all()

        assert len(students) == 3
        names = [(s.first_name, s.last_name) for s in students]
        assert ("John", "Doe") in names
        assert ("Jane", "Smith") in names
        assert ("Bob", "Johnson") in names

    @pytest.mark.asyncio
    async def test_get_all_with_school_filter(self, db_session):
        """Test getting students filtered by school"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)

        # Create two schools
        school1 = await school_repo.create(name="School 1")
        school2 = await school_repo.create(name="School 2")

        # Create students in different schools
        await student_repo.create(
            school_id=school1.id, first_name="John", last_name="Doe"
        )
        await student_repo.create(
            school_id=school1.id, first_name="Jane", last_name="Smith"
        )
        await student_repo.create(
            school_id=school2.id, first_name="Bob", last_name="Johnson"
        )

        # Get students from school1 only
        school1_students = await student_repo.get_all(school_id=school1.id)

        assert len(school1_students) == 2
        for student in school1_students:
            assert student.school_id == school1.id

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, db_session, school):
        """Test getting students with pagination"""
        repo = StudentRepository(db_session)

        # Create 5 students
        for i in range(5):
            await repo.create(
                school_id=school.id, first_name=f"Student{i}", last_name="Test"
            )

        # Get first 2 students
        page1 = await repo.get_all(skip=0, limit=2)
        assert len(page1) == 2

        # Get next 2 students
        page2 = await repo.get_all(skip=2, limit=2)
        assert len(page2) == 2

        # Get last student
        page3 = await repo.get_all(skip=4, limit=2)
        assert len(page3) == 1

    @pytest.mark.asyncio
    async def test_update_student_all_fields(self, db_session, school):
        """Test updating all fields of a student"""
        repo = StudentRepository(db_session)
        student = await repo.create(
            school_id=school.id, first_name="John", last_name="Doe"
        )

        updated_student = await repo.update(
            student.id,
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            status=StudentStatus.INACTIVE,
        )

        assert updated_student is not None
        assert updated_student.id == student.id
        assert updated_student.first_name == "Jane"
        assert updated_student.last_name == "Smith"
        assert updated_student.email == "jane.smith@example.com"
        assert updated_student.status == StudentStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_update_student_partial_fields(self, db_session, school):
        """Test updating only some fields of a student"""
        repo = StudentRepository(db_session)
        student = await repo.create(
            school_id=school.id,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )

        updated_student = await repo.update(student.id, first_name="Jane")

        assert updated_student.first_name == "Jane"
        assert updated_student.last_name == "Doe"
        assert updated_student.email == "john@example.com"

    @pytest.mark.asyncio
    async def test_update_student_to_different_school(self, db_session):
        """Test updating student to different school"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)

        # Create two schools
        school1 = await school_repo.create(name="School 1")
        school2 = await school_repo.create(name="School 2")

        # Create student in school1
        student = await student_repo.create(
            school_id=school1.id, first_name="John", last_name="Doe"
        )

        # Update to school2
        updated_student = await student_repo.update(student.id, school_id=school2.id)

        assert updated_student.school_id == school2.id

    @pytest.mark.asyncio
    async def test_update_nonexistent_student_returns_none(self, db_session):
        """Test updating a non-existent student returns None"""
        repo = StudentRepository(db_session)
        updated_student = await repo.update(999, first_name="Updated")
        assert updated_student is None

    @pytest.mark.asyncio
    async def test_update_to_same_email_allowed(self, db_session, school):
        """Test that updating student to have same email as another is allowed (no unique constraint)"""
        repo = StudentRepository(db_session)

        # Create two students
        student1 = await repo.create(
            school_id=school.id,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )
        student2 = await repo.create(
            school_id=school.id,
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
        )

        # Update student2 to have student1's email - should succeed
        updated_student = await repo.update(student2.id, email="john@example.com")

        assert updated_student.email == "john@example.com"

    @pytest.mark.asyncio
    async def test_delete_existing_student(self, db_session, school):
        """Test deleting an existing student"""
        repo = StudentRepository(db_session)
        student = await repo.create(
            school_id=school.id, first_name="John", last_name="Doe"
        )

        result = await repo.delete(student.id)
        assert result is True

        # Verify student is deleted
        deleted_student = await repo.get(student.id)
        assert deleted_student is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_student_returns_false(self, db_session):
        """Test deleting a non-existent student returns False"""
        repo = StudentRepository(db_session)
        result = await repo.delete(999)
        assert result is False


class TestStudentAccountStatus:
    """Tests for student account status calculations"""

    @pytest.mark.asyncio
    async def test_get_account_status_nonexistent_student(self, db_session):
        """Test getting account status for non-existent student returns None"""
        repo = StudentRepository(db_session)
        status = await repo.get_account_status(999)
        assert status is None

    @pytest.mark.asyncio
    async def test_get_account_status_no_invoices(self, db_session, school):
        """Test account status for student with no invoices"""
        student_repo = StudentRepository(db_session)
        student = await student_repo.create(
            school_id=school.id, first_name="John", last_name="Doe"
        )

        status = await student_repo.get_account_status(student.id)

        assert status is not None
        assert status["student_id"] == student.id
        assert status["student_name"] == "John Doe"
        assert status["total_invoiced"] == Decimal("0")
        assert status["total_paid"] == Decimal("0")
        assert status["total_pending"] == Decimal("0")
        assert len(status["invoices"]) == 0

    @pytest.mark.asyncio
    async def test_get_account_status_with_unpaid_invoices(self, db_session, school):
        """Test account status with unpaid invoices"""
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)

        student = await student_repo.create(
            school_id=school.id, first_name="John", last_name="Doe"
        )

        # Create invoices
        invoice1 = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
        )
        invoice2 = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("200.00"),
            due_date=date(2024, 11, 30),
            issue_date=date(2024, 1, 1),
        )

        status = await student_repo.get_account_status(student.id)

        assert status["total_invoiced"] == Decimal("300.00")
        assert status["total_paid"] == Decimal("0")
        assert status["total_pending"] == Decimal("300.00")
        assert len(status["invoices"]) == 2

        # Verify invoice details
        invoice_ids = [inv["id"] for inv in status["invoices"]]
        assert invoice1.id in invoice_ids
        assert invoice2.id in invoice_ids

    @pytest.mark.asyncio
    async def test_get_account_status_with_partial_payment(self, db_session, school):
        """Test account status with partially paid invoice"""
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        student = await student_repo.create(
            school_id=school.id, first_name="John", last_name="Doe"
        )
        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
        )

        # Create partial payment
        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("40.00"),
            payment_date=date(2024, 1, 15),
        )

        status = await student_repo.get_account_status(student.id)

        assert status["total_invoiced"] == Decimal("100.00")
        assert status["total_paid"] == Decimal("40.00")
        assert status["total_pending"] == Decimal("60.00")
        assert status["invoices"][0]["paid_amount"] == Decimal("40.00")
        assert status["invoices"][0]["balance"] == Decimal("60.00")

    @pytest.mark.asyncio
    async def test_get_account_status_with_fully_paid_invoice(self, db_session, school):
        """Test account status with fully paid invoice"""
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        student = await student_repo.create(
            school_id=school.id, first_name="John", last_name="Doe"
        )
        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
        )

        # Create full payment
        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("100.00"),
            payment_date=date(2024, 1, 15),
        )

        status = await student_repo.get_account_status(student.id)

        assert status["total_invoiced"] == Decimal("100.00")
        assert status["total_paid"] == Decimal("100.00")
        assert status["total_pending"] == Decimal("0")
        assert status["invoices"][0]["paid_amount"] == Decimal("100.00")
        assert status["invoices"][0]["balance"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_account_status_with_multiple_payments_on_invoice(
        self, db_session, school
    ):
        """Test account status with multiple payments on same invoice"""
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        student = await student_repo.create(
            school_id=school.id, first_name="John", last_name="Doe"
        )
        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
        )

        # Create multiple payments
        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("30.00"),
            payment_date=date(2024, 1, 15),
        )
        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("20.00"),
            payment_date=date(2024, 1, 20),
        )
        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("25.00"),
            payment_date=date(2024, 1, 25),
        )

        status = await student_repo.get_account_status(student.id)

        assert status["total_invoiced"] == Decimal("100.00")
        assert status["total_paid"] == Decimal("75.00")
        assert status["total_pending"] == Decimal("25.00")
        assert status["invoices"][0]["paid_amount"] == Decimal("75.00")
        assert status["invoices"][0]["balance"] == Decimal("25.00")

    @pytest.mark.asyncio
    async def test_get_account_status_with_mixed_invoices(self, db_session, school):
        """Test account status with mix of paid, partially paid, and unpaid invoices"""
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        student = await student_repo.create(
            school_id=school.id, first_name="John", last_name="Doe"
        )

        # Create invoices
        invoice1 = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
        )
        invoice2 = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("200.00"),
            due_date=date(2024, 11, 30),
            issue_date=date(2024, 1, 1),
        )
        invoice3 = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("150.00"),
            due_date=date(2024, 10, 31),
            issue_date=date(2024, 1, 1),
        )

        # Fully pay invoice1
        await payment_repo.create(
            invoice_id=invoice1.id,
            amount=Decimal("100.00"),
            payment_date=date(2024, 1, 15),
        )

        # Partially pay invoice2
        await payment_repo.create(
            invoice_id=invoice2.id,
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 20),
        )

        # Leave invoice3 unpaid

        status = await student_repo.get_account_status(student.id)

        assert status["total_invoiced"] == Decimal("450.00")
        assert status["total_paid"] == Decimal("150.00")
        assert status["total_pending"] == Decimal("300.00")

        # Find each invoice in results
        inv1 = next(
            (inv for inv in status["invoices"] if inv["id"] == invoice1.id), None
        )
        assert inv1["paid_amount"] == Decimal("100.00")
        assert inv1["balance"] == Decimal("0")

        inv2 = next(
            (inv for inv in status["invoices"] if inv["id"] == invoice2.id), None
        )
        assert inv2["paid_amount"] == Decimal("50.00")
        assert inv2["balance"] == Decimal("150.00")

        inv3 = next(
            (inv for inv in status["invoices"] if inv["id"] == invoice3.id), None
        )
        assert inv3["paid_amount"] == Decimal("0")
        assert inv3["balance"] == Decimal("150.00")

    @pytest.mark.asyncio
    async def test_get_account_status_preserves_invoice_details(
        self, db_session, school
    ):
        """Test that account status preserves all invoice details"""
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)

        student = await student_repo.create(
            school_id=school.id, first_name="John", last_name="Doe"
        )
        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
        )

        status = await student_repo.get_account_status(student.id)

        invoice_data = status["invoices"][0]
        assert invoice_data["id"] == invoice.id
        assert invoice_data["invoice_number"] == invoice.invoice_number
        assert invoice_data["amount"] == invoice.amount
        assert invoice_data["due_date"] == invoice.due_date
        assert invoice_data["status"] == invoice.status
