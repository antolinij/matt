"""
Unit tests for SchoolRepository

Tests CRUD operations and account status methods for schools.
"""

from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.core.database import Base
from app.core.exceptions import DuplicateRecordException
from app.db.models import (Invoice, InvoiceStatus, Payment, PaymentMethod,
                           School, Student, StudentStatus)
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.school_repository import SchoolRepository
from app.repositories.student_repository import StudentRepository

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_school_repository.db"
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


class TestSchoolRepositoryCRUD:
    """Tests for School CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_school_with_all_fields(self, db_session):
        """Test creating a school with all fields"""
        repo = SchoolRepository(db_session)
        school = await repo.create(
            name="Complete School",
            address="123 Main St",
            phone="+1234567890",
            email="complete@school.com",
        )

        assert school.id is not None
        assert school.name == "Complete School"
        assert school.address == "123 Main St"
        assert school.phone == "+1234567890"
        assert school.email == "complete@school.com"

    @pytest.mark.asyncio
    async def test_create_school_with_minimal_fields(self, db_session):
        """Test creating a school with only required field (name)"""
        repo = SchoolRepository(db_session)
        school = await repo.create(name="Minimal School")

        assert school.id is not None
        assert school.name == "Minimal School"
        assert school.address is None
        assert school.phone is None
        assert school.email is None

    @pytest.mark.asyncio
    async def test_create_school_with_same_email_allowed(self, db_session):
        """Test that creating schools with same email is allowed (no unique constraint)"""
        repo = SchoolRepository(db_session)

        # Create first school
        school1 = await repo.create(name="School 1", email="same@school.com")

        # Create second school with same email - should succeed
        school2 = await repo.create(name="School 2", email="same@school.com")

        assert school1.id is not None
        assert school2.id is not None
        assert school1.email == school2.email

    @pytest.mark.asyncio
    async def test_get_existing_school(self, db_session):
        """Test getting an existing school by ID"""
        repo = SchoolRepository(db_session)
        created_school = await repo.create(name="Test School")

        retrieved_school = await repo.get(created_school.id)

        assert retrieved_school is not None
        assert retrieved_school.id == created_school.id
        assert retrieved_school.name == "Test School"

    @pytest.mark.asyncio
    async def test_get_nonexistent_school_returns_none(self, db_session):
        """Test getting a non-existent school returns None"""
        repo = SchoolRepository(db_session)
        school = await repo.get(999)
        assert school is None

    @pytest.mark.asyncio
    async def test_get_all_schools(self, db_session):
        """Test getting all schools"""
        repo = SchoolRepository(db_session)

        # Create multiple schools
        await repo.create(name="School 1")
        await repo.create(name="School 2")
        await repo.create(name="School 3")

        schools = await repo.get_all()

        assert len(schools) == 3
        names = [s.name for s in schools]
        assert "School 1" in names
        assert "School 2" in names
        assert "School 3" in names

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, db_session):
        """Test getting schools with pagination"""
        repo = SchoolRepository(db_session)

        # Create 5 schools
        for i in range(5):
            await repo.create(name=f"School {i}")

        # Get first 2 schools
        page1 = await repo.get_all(skip=0, limit=2)
        assert len(page1) == 2

        # Get next 2 schools
        page2 = await repo.get_all(skip=2, limit=2)
        assert len(page2) == 2

        # Get last school
        page3 = await repo.get_all(skip=4, limit=2)
        assert len(page3) == 1

    @pytest.mark.asyncio
    async def test_update_school_all_fields(self, db_session):
        """Test updating all fields of a school"""
        repo = SchoolRepository(db_session)
        school = await repo.create(name="Original Name")

        updated_school = await repo.update(
            school.id,
            name="Updated Name",
            address="New Address",
            phone="+9876543210",
            email="updated@school.com",
        )

        assert updated_school is not None
        assert updated_school.id == school.id
        assert updated_school.name == "Updated Name"
        assert updated_school.address == "New Address"
        assert updated_school.phone == "+9876543210"
        assert updated_school.email == "updated@school.com"

    @pytest.mark.asyncio
    async def test_update_school_partial_fields(self, db_session):
        """Test updating only some fields of a school"""
        repo = SchoolRepository(db_session)
        school = await repo.create(
            name="Original", address="Original Address", email="original@school.com"
        )

        updated_school = await repo.update(school.id, name="Updated")

        assert updated_school.name == "Updated"
        assert updated_school.address == "Original Address"
        assert updated_school.email == "original@school.com"

    @pytest.mark.asyncio
    async def test_update_nonexistent_school_returns_none(self, db_session):
        """Test updating a non-existent school returns None"""
        repo = SchoolRepository(db_session)
        updated_school = await repo.update(999, name="Updated")
        assert updated_school is None

    @pytest.mark.asyncio
    async def test_update_to_same_email_allowed(self, db_session):
        """Test that updating school to have same email as another is allowed (no unique constraint)"""
        repo = SchoolRepository(db_session)

        # Create two schools
        school1 = await repo.create(name="School 1", email="school1@test.com")
        school2 = await repo.create(name="School 2", email="school2@test.com")

        # Update school2 to have school1's email - should succeed
        updated_school = await repo.update(school2.id, email="school1@test.com")

        assert updated_school.email == "school1@test.com"

    @pytest.mark.asyncio
    async def test_delete_existing_school(self, db_session):
        """Test deleting an existing school"""
        repo = SchoolRepository(db_session)
        school = await repo.create(name="To Be Deleted")

        result = await repo.delete(school.id)
        assert result is True

        # Verify school is deleted
        deleted_school = await repo.get(school.id)
        assert deleted_school is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_school_returns_false(self, db_session):
        """Test deleting a non-existent school returns False"""
        repo = SchoolRepository(db_session)
        result = await repo.delete(999)
        assert result is False


class TestSchoolAccountStatus:
    """Tests for school account status calculations"""

    @pytest.mark.asyncio
    async def test_get_account_status_nonexistent_school(self, db_session):
        """Test getting account status for non-existent school returns None"""
        repo = SchoolRepository(db_session)
        status = await repo.get_account_status(999)
        assert status is None

    @pytest.mark.asyncio
    async def test_get_account_status_school_with_no_students(self, db_session):
        """Test account status for school with no students"""
        school_repo = SchoolRepository(db_session)
        school = await school_repo.create(name="Empty School")

        status = await school_repo.get_account_status(school.id)

        assert status is not None
        assert status["school_id"] == school.id
        assert status["school_name"] == "Empty School"
        assert status["total_students"] == 0
        assert status["active_students"] == 0
        assert status["total_invoiced"] == Decimal("0")
        assert status["total_paid"] == Decimal("0")
        assert status["total_pending"] == Decimal("0")
        assert len(status["invoices"]) == 0

    @pytest.mark.asyncio
    async def test_get_account_status_with_students_no_invoices(self, db_session):
        """Test account status for school with students but no invoices"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)

        school = await school_repo.create(name="Test School")
        await student_repo.create(
            school_id=school.id,
            first_name="John",
            last_name="Doe",
            status=StudentStatus.ACTIVE,
        )
        await student_repo.create(
            school_id=school.id,
            first_name="Jane",
            last_name="Smith",
            status=StudentStatus.INACTIVE,
        )

        status = await school_repo.get_account_status(school.id)

        assert status["total_students"] == 2
        assert status["active_students"] == 1
        assert status["total_invoiced"] == Decimal("0")
        assert status["total_paid"] == Decimal("0")
        assert status["total_pending"] == Decimal("0")
        assert len(status["invoices"]) == 0

    @pytest.mark.asyncio
    async def test_get_account_status_with_unpaid_invoices(self, db_session):
        """Test account status with unpaid invoices"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)

        # Create school and student
        school = await school_repo.create(name="Test School")
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

        status = await school_repo.get_account_status(school.id)

        assert status["total_invoiced"] == Decimal("300.00")
        assert status["total_paid"] == Decimal("0")
        assert status["total_pending"] == Decimal("300.00")
        assert len(status["invoices"]) == 2

        # Check invoice details
        invoice_ids = [inv["id"] for inv in status["invoices"]]
        assert invoice1.id in invoice_ids
        assert invoice2.id in invoice_ids

    @pytest.mark.asyncio
    async def test_get_account_status_with_partial_payments(self, db_session):
        """Test account status with partially paid invoices"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        # Create school, student, and invoice
        school = await school_repo.create(name="Test School")
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
            amount=Decimal("30.00"),
            payment_date=date(2024, 1, 15),
        )

        status = await school_repo.get_account_status(school.id)

        assert status["total_invoiced"] == Decimal("100.00")
        assert status["total_paid"] == Decimal("30.00")
        assert status["total_pending"] == Decimal("70.00")
        assert len(status["invoices"]) == 1
        assert status["invoices"][0]["paid_amount"] == Decimal("30.00")
        assert status["invoices"][0]["balance"] == Decimal("70.00")

    @pytest.mark.asyncio
    async def test_get_account_status_with_fully_paid_invoices(self, db_session):
        """Test account status with fully paid invoices"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        # Create school, student, and invoice
        school = await school_repo.create(name="Test School")
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

        status = await school_repo.get_account_status(school.id)

        assert status["total_invoiced"] == Decimal("100.00")
        assert status["total_paid"] == Decimal("100.00")
        assert status["total_pending"] == Decimal("0")
        assert status["invoices"][0]["paid_amount"] == Decimal("100.00")
        assert status["invoices"][0]["balance"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_account_status_with_multiple_students(self, db_session):
        """Test account status aggregates across multiple students"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        # Create school and students
        school = await school_repo.create(name="Test School")
        student1 = await student_repo.create(
            school_id=school.id, first_name="John", last_name="Doe"
        )
        student2 = await student_repo.create(
            school_id=school.id, first_name="Jane", last_name="Smith"
        )

        # Create invoices for both students
        invoice1 = await invoice_repo.create(
            student_id=student1.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
        )
        invoice2 = await invoice_repo.create(
            student_id=student2.id,
            amount=Decimal("200.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1),
        )

        # Create payment for student1
        await payment_repo.create(
            invoice_id=invoice1.id,
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 15),
        )

        status = await school_repo.get_account_status(school.id)

        assert status["total_students"] == 2
        assert status["total_invoiced"] == Decimal("300.00")
        assert status["total_paid"] == Decimal("50.00")
        assert status["total_pending"] == Decimal("250.00")
        assert len(status["invoices"]) == 2


class TestSchoolStudentAccountStatus:
    """Tests for getting account status of specific student in a school"""

    @pytest.mark.asyncio
    async def test_get_student_account_status_nonexistent_school(self, db_session):
        """Test getting student account status for non-existent school returns None"""
        repo = SchoolRepository(db_session)
        status = await repo.get_student_account_status(999, 1)
        assert status is None

    @pytest.mark.asyncio
    async def test_get_student_account_status_nonexistent_student(self, db_session):
        """Test getting account status for non-existent student returns None"""
        school_repo = SchoolRepository(db_session)
        school = await school_repo.create(name="Test School")

        status = await school_repo.get_student_account_status(school.id, 999)
        assert status is None

    @pytest.mark.asyncio
    async def test_get_student_account_status_wrong_school(self, db_session):
        """Test getting student from wrong school returns None"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)

        # Create two schools
        school1 = await school_repo.create(name="School 1")
        school2 = await school_repo.create(name="School 2")

        # Create student in school1
        student = await student_repo.create(
            school_id=school1.id, first_name="John", last_name="Doe"
        )

        # Try to get student from school2
        status = await school_repo.get_student_account_status(school2.id, student.id)
        assert status is None

    @pytest.mark.asyncio
    async def test_get_student_account_status_no_invoices(self, db_session):
        """Test student account status with no invoices"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)

        school = await school_repo.create(name="Test School")
        student = await student_repo.create(
            school_id=school.id, first_name="John", last_name="Doe"
        )

        status = await school_repo.get_student_account_status(school.id, student.id)

        assert status is not None
        assert status["student_id"] == student.id
        assert status["student_name"] == "John Doe"
        assert status["total_invoiced"] == Decimal("0")
        assert status["total_paid"] == Decimal("0")
        assert status["total_pending"] == Decimal("0")
        assert len(status["invoices"]) == 0

    @pytest.mark.asyncio
    async def test_get_student_account_status_with_invoices(self, db_session):
        """Test student account status with invoices"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        # Create school and student
        school = await school_repo.create(name="Test School")
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

        # Create partial payment on invoice1
        await payment_repo.create(
            invoice_id=invoice1.id,
            amount=Decimal("30.00"),
            payment_date=date(2024, 1, 15),
        )

        status = await school_repo.get_student_account_status(school.id, student.id)

        assert status["student_id"] == student.id
        assert status["student_name"] == "John Doe"
        assert status["total_invoiced"] == Decimal("300.00")
        assert status["total_paid"] == Decimal("30.00")
        assert status["total_pending"] == Decimal("270.00")
        assert len(status["invoices"]) == 2

        # Find invoice1 in results
        inv1_data = next(
            (inv for inv in status["invoices"] if inv["id"] == invoice1.id), None
        )
        assert inv1_data is not None
        assert inv1_data["paid_amount"] == Decimal("30.00")
        assert inv1_data["balance"] == Decimal("70.00")

        # Find invoice2 in results
        inv2_data = next(
            (inv for inv in status["invoices"] if inv["id"] == invoice2.id), None
        )
        assert inv2_data is not None
        assert inv2_data["paid_amount"] == Decimal("0")
        assert inv2_data["balance"] == Decimal("200.00")

    @pytest.mark.asyncio
    async def test_get_student_account_status_multiple_payments_on_invoice(
        self, db_session
    ):
        """Test student account status with multiple payments on one invoice"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        # Create school, student, and invoice
        school = await school_repo.create(name="Test School")
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
            amount=Decimal("40.00"),
            payment_date=date(2024, 1, 20),
        )

        status = await school_repo.get_student_account_status(school.id, student.id)

        assert status["total_invoiced"] == Decimal("100.00")
        assert status["total_paid"] == Decimal("70.00")
        assert status["total_pending"] == Decimal("30.00")
        assert status["invoices"][0]["paid_amount"] == Decimal("70.00")
        assert status["invoices"][0]["balance"] == Decimal("30.00")
