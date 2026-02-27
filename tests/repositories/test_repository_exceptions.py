"""
Tests for Repository Exception Handling

Tests that repositories correctly raise custom exceptions when database errors occur.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from decimal import Decimal
from datetime import date, datetime

from app.core.database import Base
from app.db.models import School, Student, User, Invoice, Payment, StudentStatus, InvoiceStatus, PaymentMethod, UserRole
from app.repositories.user_repository import UserRepository
from app.repositories.school_repository import SchoolRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.core.exceptions import (
    DuplicateRecordException,
    ForeignKeyViolationException,
    InvalidDataException,
    DatabaseConnectionException,
    DatabaseOperationException,
)

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_repository_exceptions.db"
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database():
    """Setup database before each test"""
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Get database session for testing"""
    async with TestingSessionLocal() as session:
        yield session


class TestUserRepositoryExceptions:
    """Tests for UserRepository exception handling"""

    @pytest.mark.asyncio
    async def test_create_duplicate_username_raises_exception(self, db_session):
        """Test that creating user with duplicate username raises DuplicateRecordException"""
        repo = UserRepository(db_session)

        # Create first user
        user1 = User(
            username="johndoe",
            email="john@example.com",
            hashed_password="hashed123",
            role=UserRole.USER
        )
        await repo.create(user1)

        # Try to create second user with same username
        user2 = User(
            username="johndoe",  # Duplicate username
            email="different@example.com",
            hashed_password="hashed456",
            role=UserRole.USER
        )

        with pytest.raises(DuplicateRecordException) as exc_info:
            await repo.create(user2)

        assert exc_info.value.resource == "User"
        assert exc_info.value.field == "username"
        assert exc_info.value.value == "johndoe"

    @pytest.mark.asyncio
    async def test_create_duplicate_email_raises_exception(self, db_session):
        """Test that creating user with duplicate email raises DuplicateRecordException"""
        repo = UserRepository(db_session)

        # Create first user
        user1 = User(
            username="user1",
            email="duplicate@example.com",
            hashed_password="hashed123",
            role=UserRole.USER
        )
        await repo.create(user1)

        # Try to create second user with same email
        user2 = User(
            username="user2",
            email="duplicate@example.com",  # Duplicate email
            hashed_password="hashed456",
            role=UserRole.USER
        )

        with pytest.raises(DuplicateRecordException) as exc_info:
            await repo.create(user2)

        assert exc_info.value.resource == "User"
        assert exc_info.value.field == "email"
        assert exc_info.value.value == "duplicate@example.com"

    @pytest.mark.asyncio
    async def test_update_duplicate_username_raises_exception(self, db_session):
        """Test that updating user to duplicate username raises DuplicateRecordException"""
        repo = UserRepository(db_session)

        # Create two users
        user1 = User(username="user1", email="user1@example.com", hashed_password="hash1", role=UserRole.USER)
        user2 = User(username="user2", email="user2@example.com", hashed_password="hash2", role=UserRole.USER)

        user1 = await repo.create(user1)
        user2 = await repo.create(user2)

        # Try to update user2 to have user1's username
        user2.username = "user1"

        with pytest.raises(DuplicateRecordException) as exc_info:
            await repo.update(user2)

        assert exc_info.value.field == "username"


class TestSchoolRepositoryExceptions:
    """Tests for SchoolRepository exception handling"""

    @pytest.mark.asyncio
    async def test_create_school_success(self, db_session):
        """Test successful school creation"""
        repo = SchoolRepository(db_session)
        school = await repo.create(
            name="Test School",
            email="school@example.com"
        )
        assert school.id is not None
        assert school.name == "Test School"


class TestStudentRepositoryExceptions:
    """Tests for StudentRepository exception handling"""

    @pytest.mark.asyncio
    async def test_create_student_with_invalid_school_id_raises_exception(self, db_session):
        """Test that creating student with non-existent school_id raises ForeignKeyViolationException"""
        repo = StudentRepository(db_session)

        with pytest.raises(ForeignKeyViolationException) as exc_info:
            await repo.create(
                school_id=999,  # Non-existent school
                first_name="John",
                last_name="Doe"
            )

        assert exc_info.value.resource == "Student"
        assert exc_info.value.foreign_key == "school_id"
        assert exc_info.value.value == 999

    @pytest.mark.asyncio
    async def test_create_student_with_valid_school_id_success(self, db_session):
        """Test successful student creation with valid school_id"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)

        # Create school first
        school = await school_repo.create(name="Test School")

        # Create student with valid school_id
        student = await student_repo.create(
            school_id=school.id,
            first_name="John",
            last_name="Doe"
        )

        assert student.id is not None
        assert student.school_id == school.id

    @pytest.mark.asyncio
    async def test_update_student_to_invalid_school_id_raises_exception(self, db_session):
        """Test that updating student to non-existent school_id raises ForeignKeyViolationException"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)

        # Create school and student
        school = await school_repo.create(name="Test School")
        student = await student_repo.create(
            school_id=school.id,
            first_name="John",
            last_name="Doe"
        )

        # Try to update to invalid school_id
        with pytest.raises(ForeignKeyViolationException) as exc_info:
            await student_repo.update(student.id, school_id=999)

        assert exc_info.value.foreign_key == "school_id"


class TestInvoiceRepositoryExceptions:
    """Tests for InvoiceRepository exception handling"""

    @pytest.mark.asyncio
    async def test_create_invoice_with_invalid_student_id_raises_exception(self, db_session):
        """Test that creating invoice with non-existent student_id raises ForeignKeyViolationException"""
        repo = InvoiceRepository(db_session)

        with pytest.raises(ForeignKeyViolationException) as exc_info:
            await repo.create(
                student_id=999,  # Non-existent student
                amount=Decimal("100.00"),
                due_date=date(2024, 12, 31),
                issue_date=date(2024, 1, 1)
            )

        assert exc_info.value.resource == "Invoice"
        assert exc_info.value.foreign_key == "student_id"
        assert exc_info.value.value == 999

    @pytest.mark.asyncio
    async def test_create_invoice_with_valid_student_id_success(self, db_session):
        """Test successful invoice creation with valid student_id"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)

        # Create school and student
        school = await school_repo.create(name="Test School")
        student = await student_repo.create(
            school_id=school.id,
            first_name="John",
            last_name="Doe"
        )

        # Create invoice with valid student_id
        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )

        assert invoice.id is not None
        assert invoice.student_id == student.id
        assert invoice.amount == Decimal("100.00")


class TestPaymentRepositoryExceptions:
    """Tests for PaymentRepository exception handling"""

    @pytest.mark.asyncio
    async def test_create_payment_with_invalid_invoice_id_returns_none(self, db_session):
        """Test that creating payment with non-existent invoice_id returns None"""
        repo = PaymentRepository(db_session)

        # Payment repository returns None for invalid invoice_id (not an exception)
        payment = await repo.create(
            invoice_id=999,  # Non-existent invoice
            amount=Decimal("50.00"),
            payment_date=date(2024, 1, 15)
        )

        assert payment is None

    @pytest.mark.asyncio
    async def test_create_payment_exceeding_balance_raises_exception(self, db_session):
        """Test that creating payment exceeding invoice balance raises InvalidDataException"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        # Create school, student, and invoice
        school = await school_repo.create(name="Test School")
        student = await student_repo.create(
            school_id=school.id,
            first_name="John",
            last_name="Doe"
        )
        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )

        # Try to create payment exceeding invoice amount
        with pytest.raises(InvalidDataException) as exc_info:
            await payment_repo.create(
                invoice_id=invoice.id,
                amount=Decimal("150.00"),  # Exceeds 100.00
                payment_date=date(2024, 1, 15)
            )

        assert exc_info.value.resource == "Payment"
        assert "exceeds remaining balance" in exc_info.value.details

    @pytest.mark.asyncio
    async def test_create_payment_exactly_matching_balance_success(self, db_session):
        """Test successful payment creation matching exact invoice balance"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        # Create school, student, and invoice
        school = await school_repo.create(name="Test School")
        student = await student_repo.create(
            school_id=school.id,
            first_name="John",
            last_name="Doe"
        )
        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )

        # Create payment matching exact balance
        payment = await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("100.00"),
            payment_date=date(2024, 1, 15)
        )

        assert payment is not None
        assert payment.amount == Decimal("100.00")

        # Verify invoice status updated to PAID
        await db_session.refresh(invoice)
        assert invoice.status == InvoiceStatus.PAID

    @pytest.mark.asyncio
    async def test_create_partial_payment_then_exceeding_payment_raises_exception(self, db_session):
        """Test that partial payment followed by exceeding payment raises exception"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        # Create school, student, and invoice
        school = await school_repo.create(name="Test School")
        student = await student_repo.create(
            school_id=school.id,
            first_name="John",
            last_name="Doe"
        )
        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )

        # Create first partial payment
        await payment_repo.create(
            invoice_id=invoice.id,
            amount=Decimal("60.00"),
            payment_date=date(2024, 1, 15)
        )

        # Try to create second payment exceeding remaining balance
        with pytest.raises(InvalidDataException) as exc_info:
            await payment_repo.create(
                invoice_id=invoice.id,
                amount=Decimal("50.00"),  # Would total 110.00, exceeds 100.00
                payment_date=date(2024, 1, 20)
            )

        assert "exceeds remaining balance" in exc_info.value.details
        assert "40.00" in exc_info.value.details  # Remaining balance should be 40.00


class TestRepositoryRollback:
    """Tests that database transactions are rolled back on exceptions"""

    @pytest.mark.asyncio
    async def test_duplicate_user_does_not_persist(self, db_session):
        """Test that failed user creation due to duplicate doesn't persist"""
        repo = UserRepository(db_session)

        # Create first user
        user1 = User(username="test", email="test@example.com", hashed_password="hash", role=UserRole.USER)
        await repo.create(user1)

        # Try to create duplicate
        user2 = User(username="test", email="different@example.com", hashed_password="hash", role=UserRole.USER)

        try:
            await repo.create(user2)
        except DuplicateRecordException:
            pass

        # Verify only one user exists
        all_users = await repo.get_all()
        assert len(all_users) == 1

    @pytest.mark.asyncio
    async def test_invalid_student_does_not_persist(self, db_session):
        """Test that failed student creation due to invalid foreign key doesn't persist"""
        student_repo = StudentRepository(db_session)

        # Try to create student with invalid school_id
        try:
            await student_repo.create(
                school_id=999,
                first_name="John",
                last_name="Doe"
            )
        except ForeignKeyViolationException:
            pass

        # Verify no students exist
        all_students = await student_repo.get_all()
        assert len(all_students) == 0

    @pytest.mark.asyncio
    async def test_exceeding_payment_does_not_persist(self, db_session):
        """Test that failed payment creation doesn't persist or update invoice"""
        school_repo = SchoolRepository(db_session)
        student_repo = StudentRepository(db_session)
        invoice_repo = InvoiceRepository(db_session)
        payment_repo = PaymentRepository(db_session)

        # Create school, student, and invoice
        school = await school_repo.create(name="Test School")
        student = await student_repo.create(school_id=school.id, first_name="John", last_name="Doe")
        invoice = await invoice_repo.create(
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=date(2024, 12, 31),
            issue_date=date(2024, 1, 1)
        )

        # Try to create exceeding payment
        try:
            await payment_repo.create(
                invoice_id=invoice.id,
                amount=Decimal("150.00"),
                payment_date=date(2024, 1, 15)
            )
        except InvalidDataException:
            pass

        # Verify no payments exist
        all_payments = await payment_repo.get_all()
        assert len(all_payments) == 0

        # Verify invoice status unchanged
        await db_session.refresh(invoice)
        assert invoice.status == InvoiceStatus.PENDING
