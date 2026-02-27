"""
Tests for Event-Driven Accounting System

Tests cover:
- Event publishing by services
- Worker processing of events
- Movement creation
- Denormalized field updates
- Historical queries
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.db.models import (
    School, Student, Invoice, Payment,
    StudentStatus, InvoiceStatus, PaymentMethod,
    AccountMovement, AccountSnapshot,
    MovementType, MovementEntityType, SnapshotType, SnapshotEntityType
)
from app.repositories.school_repository import SchoolRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.account_repository import AccountRepository
from app.services.invoice_service import InvoiceService
from app.services.payment_service import PaymentService
from app.services.event_service import EventService
from app.schemas import InvoiceCreate, PaymentCreate
from app.workers.account_worker import (
    handle_payment_created,
    handle_invoice_created,
    handle_invoice_updated
)


# Test Database Setup
@pytest.fixture
async def test_db():
    """Create test database"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def test_school(test_db: AsyncSession):
    """Create test school"""
    school = School(
        name="Test School",
        address="123 Test St",
        phone="555-0100",
        email="test@school.com",
        total_students=0,
        active_students=0,
        total_invoiced=Decimal('0.00'),
        total_paid=Decimal('0.00'),
        total_pending=Decimal('0.00')
    )
    test_db.add(school)
    await test_db.commit()
    await test_db.refresh(school)
    return school


@pytest.fixture
async def test_student(test_db: AsyncSession, test_school: School):
    """Create test student"""
    student = Student(
        school_id=test_school.id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        enrollment_date=date.today(),
        status=StudentStatus.ACTIVE,
        total_invoiced=Decimal('0.00'),
        total_paid=Decimal('0.00'),
        total_pending=Decimal('0.00')
    )
    test_db.add(student)
    await test_db.commit()
    await test_db.refresh(student)
    return student


@pytest.fixture
async def test_invoice(test_db: AsyncSession, test_student: Student):
    """Create test invoice"""
    invoice = Invoice(
        student_id=test_student.id,
        invoice_number="INV-TEST-001",
        amount=Decimal('1000.00'),
        due_date=date.today() + timedelta(days=30),
        issue_date=date.today(),
        status=InvoiceStatus.PENDING,
        description="Test Invoice"
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)
    return invoice


# ==================== Event Publishing Tests ====================

@pytest.mark.asyncio
async def test_invoice_service_publishes_event_on_create(test_db: AsyncSession, test_student: Student):
    """Test that InvoiceService publishes invoice_created event"""
    invoice_repo = InvoiceRepository(test_db)
    student_repo = StudentRepository(test_db)
    invoice_service = InvoiceService(invoice_repo, student_repo)

    # Mock event service
    with patch('app.services.invoice_service.event_service.publish_invoice_created') as mock_publish:
        mock_publish.return_value = AsyncMock()

        # Create invoice
        schema = InvoiceCreate(
            student_id=test_student.id,
            amount=Decimal('500.00'),
            due_date=date.today() + timedelta(days=30),
            issue_date=date.today(),
            status=InvoiceStatus.PENDING,
            description="Test"
        )

        invoice = await invoice_service.create_invoice(schema)

        # Verify event was published
        assert mock_publish.called
        call_args = mock_publish.call_args[1]
        assert call_args['invoice_id'] == invoice.id
        assert call_args['student_id'] == test_student.id
        assert call_args['school_id'] == test_student.school_id
        assert call_args['amount'] == 500.00


@pytest.mark.asyncio
async def test_invoice_service_publishes_event_on_update(test_db: AsyncSession, test_invoice: Invoice, test_student: Student):
    """Test that InvoiceService publishes invoice_updated event when amount changes"""
    from app.schemas import InvoiceUpdate

    invoice_repo = InvoiceRepository(test_db)
    student_repo = StudentRepository(test_db)
    invoice_service = InvoiceService(invoice_repo, student_repo)

    # Mock event service
    with patch('app.services.invoice_service.event_service.publish_invoice_updated') as mock_publish:
        mock_publish.return_value = AsyncMock()

        # Update invoice amount
        schema = InvoiceUpdate(amount=Decimal('1500.00'))

        updated_invoice = await invoice_service.update_invoice(test_invoice.id, schema)

        # Verify event was published
        assert mock_publish.called
        call_args = mock_publish.call_args[1]
        assert call_args['invoice_id'] == test_invoice.id
        assert call_args['old_amount'] == 1000.00
        assert call_args['new_amount'] == 1500.00


@pytest.mark.asyncio
async def test_payment_service_publishes_event_on_create(test_db: AsyncSession, test_invoice: Invoice, test_student: Student):
    """Test that PaymentService publishes payment_created event"""
    payment_repo = PaymentRepository(test_db)
    invoice_repo = InvoiceRepository(test_db)
    student_repo = StudentRepository(test_db)
    payment_service = PaymentService(payment_repo, invoice_repo, student_repo)

    # Mock event service
    with patch('app.services.payment_service.event_service.publish_payment_created') as mock_publish:
        mock_publish.return_value = AsyncMock()

        # Create payment
        schema = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal('300.00'),
            payment_date=date.today(),
            payment_method=PaymentMethod.CARD,
            reference="TEST-REF-001"
        )

        payment = await payment_service.create_payment(schema)

        # Verify event was published
        assert mock_publish.called
        call_args = mock_publish.call_args[1]
        assert call_args['payment_id'] == payment.id
        assert call_args['invoice_id'] == test_invoice.id
        assert call_args['student_id'] == test_student.id
        assert call_args['school_id'] == test_student.school_id
        assert call_args['amount'] == 300.00


# ==================== Worker Tests ====================

@pytest.mark.asyncio
async def test_worker_handles_payment_created(test_db: AsyncSession, test_student: Student, test_invoice: Invoice, test_school: School):
    """Test that worker correctly processes payment_created event"""
    # Create a payment manually (not through service to avoid event)
    payment = Payment(
        invoice_id=test_invoice.id,
        amount=Decimal('400.00'),
        payment_date=date.today(),
        payment_method=PaymentMethod.CASH,
        reference="WORKER-TEST-001"
    )
    test_db.add(payment)
    await test_db.commit()
    await test_db.refresh(payment)

    # Mock the worker's get_db to return our test_db
    async def mock_get_db():
        return test_db

    # Call worker handler
    with patch('app.workers.account_worker.get_db', return_value=test_db):
        await handle_payment_created(
            ctx=None,
            payment_id=payment.id,
            invoice_id=test_invoice.id,
            student_id=test_student.id,
            school_id=test_school.id,
            amount=400.00,
            user_id=None
        )

    # Verify movements were created
    account_repo = AccountRepository(test_db)
    student_movements = await account_repo.get_movements_by_entity(
        MovementEntityType.STUDENT, test_student.id
    )
    school_movements = await account_repo.get_movements_by_entity(
        MovementEntityType.SCHOOL, test_school.id
    )

    assert len(student_movements) == 1
    assert len(school_movements) == 1

    # Verify student movement details
    student_movement = student_movements[0]
    assert student_movement.movement_type == MovementType.PAYMENT_RECEIVED
    assert student_movement.delta == Decimal('400.00')
    assert student_movement.related_entity_id == payment.id

    # Verify denormalized fields were updated
    # Query fresh instances since worker session was closed
    updated_student = await test_db.get(Student, test_student.id)
    updated_school = await test_db.get(School, test_school.id)

    assert updated_student.total_paid == Decimal('400.00')
    assert updated_school.total_paid == Decimal('400.00')


@pytest.mark.asyncio
async def test_worker_handles_invoice_created(test_db: AsyncSession, test_student: Student, test_school: School):
    """Test that worker correctly processes invoice_created event"""
    # Create invoice manually
    invoice = Invoice(
        student_id=test_student.id,
        invoice_number="WORKER-INV-001",
        amount=Decimal('800.00'),
        due_date=date.today() + timedelta(days=30),
        issue_date=date.today(),
        status=InvoiceStatus.PENDING
    )
    test_db.add(invoice)
    await test_db.commit()
    await test_db.refresh(invoice)

    # Call worker handler
    with patch('app.workers.account_worker.get_db', return_value=test_db):
        await handle_invoice_created(
            ctx=None,
            invoice_id=invoice.id,
            student_id=test_student.id,
            school_id=test_school.id,
            amount=800.00,
            user_id=None
        )

    # Verify movements were created
    account_repo = AccountRepository(test_db)
    student_movements = await account_repo.get_movements_by_entity(
        MovementEntityType.STUDENT, test_student.id
    )

    assert len(student_movements) == 1
    assert student_movements[0].movement_type == MovementType.INVOICE_CREATED
    assert student_movements[0].delta == Decimal('800.00')

    # Verify denormalized fields
    # Query fresh instances since worker session was closed
    updated_student = await test_db.get(Student, test_student.id)
    updated_school = await test_db.get(School, test_school.id)

    assert updated_student.total_invoiced == Decimal('800.00')
    assert updated_student.total_pending == Decimal('800.00')
    assert updated_school.total_invoiced == Decimal('800.00')


# ==================== Historical Query Tests ====================

@pytest.mark.asyncio
async def test_get_movements_by_period(test_db: AsyncSession, test_student: Student, test_school: School):
    """Test querying movements by date period"""
    account_repo = AccountRepository(test_db)

    # Create some movements
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)

    movement1 = AccountMovement(
        movement_type=MovementType.INVOICE_CREATED,
        entity_type=MovementEntityType.STUDENT,
        entity_id=test_student.id,
        field_name="total_invoiced",
        old_value=Decimal('0.00'),
        new_value=Decimal('100.00'),
        delta=Decimal('100.00'),
        created_at=yesterday,
        related_entity_type="Invoice",
        related_entity_id=1
    )
    movement2 = AccountMovement(
        movement_type=MovementType.PAYMENT_RECEIVED,
        entity_type=MovementEntityType.STUDENT,
        entity_id=test_student.id,
        field_name="total_paid",
        old_value=Decimal('0.00'),
        new_value=Decimal('50.00'),
        delta=Decimal('50.00'),
        created_at=now,
        related_entity_type="Payment",
        related_entity_id=1
    )

    test_db.add_all([movement1, movement2])
    await test_db.commit()

    # Query movements for the last 2 days
    start = yesterday - timedelta(hours=1)
    end = now + timedelta(hours=1)

    movements = await account_repo.get_movements_by_period(
        MovementEntityType.STUDENT, test_student.id, start, end
    )

    assert len(movements) == 2


@pytest.mark.asyncio
async def test_calculate_period_totals(test_db: AsyncSession, test_student: Student):
    """Test calculating totals for a specific period"""
    account_repo = AccountRepository(test_db)

    # Create movements
    now = datetime.utcnow()
    movements = [
        AccountMovement(
            movement_type=MovementType.INVOICE_CREATED,
            entity_type=MovementEntityType.STUDENT,
            entity_id=test_student.id,
            field_name="total_invoiced",
            old_value=Decimal('0.00'),
            new_value=Decimal('1000.00'),
            delta=Decimal('1000.00'),
            created_at=now - timedelta(days=5),
            related_entity_type="Invoice",
            related_entity_id=1
        ),
        AccountMovement(
            movement_type=MovementType.PAYMENT_RECEIVED,
            entity_type=MovementEntityType.STUDENT,
            entity_id=test_student.id,
            field_name="total_paid",
            old_value=Decimal('0.00'),
            new_value=Decimal('600.00'),
            delta=Decimal('600.00'),
            created_at=now - timedelta(days=3),
            related_entity_type="Payment",
            related_entity_id=1
        ),
        AccountMovement(
            movement_type=MovementType.PAYMENT_RECEIVED,
            entity_type=MovementEntityType.STUDENT,
            entity_id=test_student.id,
            field_name="total_paid",
            old_value=Decimal('600.00'),
            new_value=Decimal('800.00'),
            delta=Decimal('200.00'),
            created_at=now - timedelta(days=1),
            related_entity_type="Payment",
            related_entity_id=2
        ),
    ]
    test_db.add_all(movements)
    await test_db.commit()

    # Calculate totals for last 7 days
    totals = await account_repo.calculate_period_totals(
        MovementEntityType.STUDENT,
        test_student.id,
        now - timedelta(days=7),
        now
    )

    assert totals['total_invoiced'] == Decimal('1000.00')
    assert totals['total_paid'] == Decimal('800.00')
    assert totals['net_change'] == Decimal('200.00')
    assert totals['movement_count'] == 3


@pytest.mark.asyncio
async def test_snapshot_creation_and_retrieval(test_db: AsyncSession, test_student: Student):
    """Test creating and retrieving snapshots"""
    account_repo = AccountRepository(test_db)

    # Create a snapshot
    snapshot_date = date.today()
    snapshot = await account_repo.create_snapshot(
        entity_type=SnapshotEntityType.STUDENT,
        entity_id=test_student.id,
        snapshot_date=snapshot_date,
        snapshot_type=SnapshotType.DAILY,
        total_invoiced=Decimal('2000.00'),
        total_paid=Decimal('1500.00'),
        total_pending=Decimal('500.00')
    )

    assert snapshot.id is not None
    assert snapshot.total_invoiced == Decimal('2000.00')

    # Retrieve snapshot
    retrieved = await account_repo.get_snapshot_at_date(
        SnapshotEntityType.STUDENT,
        test_student.id,
        snapshot_date
    )

    assert retrieved is not None
    assert retrieved.id == snapshot.id
    assert retrieved.total_paid == Decimal('1500.00')


@pytest.mark.asyncio
async def test_get_account_status_at_date(test_db: AsyncSession, test_student: Student):
    """Test calculating account status at a specific date using snapshots + movements"""
    account_repo = AccountRepository(test_db)

    # Create a snapshot for 5 days ago
    snapshot_date = date.today() - timedelta(days=5)
    await account_repo.create_snapshot(
        entity_type=SnapshotEntityType.STUDENT,
        entity_id=test_student.id,
        snapshot_date=snapshot_date,
        snapshot_type=SnapshotType.DAILY,
        total_invoiced=Decimal('1000.00'),
        total_paid=Decimal('500.00'),
        total_pending=Decimal('500.00')
    )

    # Create movements after snapshot
    now = datetime.utcnow()
    movements = [
        AccountMovement(
            movement_type=MovementType.INVOICE_CREATED,
            entity_type=MovementEntityType.STUDENT,
            entity_id=test_student.id,
            field_name="total_invoiced",
            old_value=Decimal('1000.00'),
            new_value=Decimal('1500.00'),
            delta=Decimal('500.00'),
            created_at=now - timedelta(days=3),
            related_entity_type="Invoice",
            related_entity_id=1
        ),
        AccountMovement(
            movement_type=MovementType.PAYMENT_RECEIVED,
            entity_type=MovementEntityType.STUDENT,
            entity_id=test_student.id,
            field_name="total_paid",
            old_value=Decimal('500.00'),
            new_value=Decimal('800.00'),
            delta=Decimal('300.00'),
            created_at=now - timedelta(days=2),
            related_entity_type="Payment",
            related_entity_id=1
        ),
    ]
    test_db.add_all(movements)
    await test_db.commit()

    # Calculate status at yesterday (should include snapshot + movements)
    status = await account_repo.get_account_status_at_date(
        MovementEntityType.STUDENT,
        test_student.id,
        now - timedelta(days=1)
    )

    assert status['total_invoiced'] == Decimal('1500.00')  # 1000 + 500
    assert status['total_paid'] == Decimal('800.00')  # 500 + 300
    assert status['total_pending'] == Decimal('700.00')  # 1500 - 800
    assert status['used_snapshot'] is True
