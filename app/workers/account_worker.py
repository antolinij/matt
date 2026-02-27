"""
Account Worker

Background worker for processing account-related events.
Handles movement creation and denormalized field updates.

Run with: arq app.workers.account_worker.WorkerSettings
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.db.models import (
    AccountMovement,
    MovementType,
    MovementEntityType,
    School,
    Student,
    Invoice,
    Payment,
    StudentStatus,
)

logger = logging.getLogger(__name__)

# Lazy initialization of database engine
_engine = None
_AsyncSessionLocal = None


def get_async_engine():
    """Get or create async engine"""
    global _engine, _AsyncSessionLocal
    if _engine is None:
        # Use asyncpg driver for async operations
        db_url = settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
        _engine = create_async_engine(db_url, echo=False)
        _AsyncSessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine, _AsyncSessionLocal


async def get_db():
    """Get database session"""
    _, AsyncSessionLocal = get_async_engine()
    async with AsyncSessionLocal() as session:
        return session


async def handle_payment_created(ctx, payment_id: int, invoice_id: int, student_id: int,
                                 school_id: int, amount: float, user_id: int = None):
    """
    Handle payment created event.

    Creates account movement and updates denormalized fields.
    """
    logger.info(f"Processing payment_created event for payment {payment_id}")

    db = await get_db()
    try:
        amount_decimal = Decimal(str(amount))

        # 1. Get student and calculate new values
        student = await db.get(Student, student_id)
        if not student:
            logger.error(f"Student {student_id} not found")
            return

        student_old_paid = student.total_paid
        student_new_paid = student.total_paid + amount_decimal

        # 2. Get school and calculate new values
        school = await db.get(School, school_id)
        if not school:
            logger.error(f"School {school_id} not found")
            return

        school_old_paid = school.total_paid
        school_new_paid = school.total_paid + amount_decimal

        # 3. Create movement record for student
        student_movement = AccountMovement(
            movement_type=MovementType.PAYMENT_RECEIVED,
            entity_type=MovementEntityType.STUDENT,
            entity_id=student_id,
            field_name="total_paid",
            old_value=student_old_paid,
            new_value=student_new_paid,
            delta=amount_decimal,
            related_entity_type="Payment",
            related_entity_id=payment_id,
            description=f"Payment ${amount} received for invoice #{invoice_id}",
            created_by_user_id=user_id,
        )

        # 4. Create movement record for school
        school_movement = AccountMovement(
            movement_type=MovementType.PAYMENT_RECEIVED,
            entity_type=MovementEntityType.SCHOOL,
            entity_id=school_id,
            field_name="total_paid",
            old_value=school_old_paid,
            new_value=school_new_paid,
            delta=amount_decimal,
            related_entity_type="Payment",
            related_entity_id=payment_id,
            description=f"Payment ${amount} received from student #{student_id}",
            created_by_user_id=user_id,
        )

        # 5. Update student denormalized fields
        student.total_paid = student_new_paid
        student.total_pending -= amount_decimal
        student.cache_updated_at = datetime.utcnow()

        # 6. Update school denormalized fields
        school.total_paid = school_new_paid
        school.total_pending -= amount_decimal
        school.cache_updated_at = datetime.utcnow()

        # 7. Commit all changes
        db.add(student_movement)
        db.add(school_movement)
        await db.commit()

        logger.info(f"Successfully processed payment_created event for payment {payment_id}")

    except Exception as e:
        await db.rollback()
        logger.error(f"Error processing payment_created event: {e}")
        raise  # arq will retry
    finally:
        await db.close()


async def handle_invoice_created(ctx, invoice_id: int, student_id: int,
                                 school_id: int, amount: float, user_id: int = None):
    """
    Handle invoice created event.

    Creates account movement and updates denormalized fields.
    """
    logger.info(f"Processing invoice_created event for invoice {invoice_id}")

    db = await get_db()
    try:
        amount_decimal = Decimal(str(amount))

        # 1. Get student and calculate new values
        student = await db.get(Student, student_id)
        if not student:
            logger.error(f"Student {student_id} not found")
            return

        student_old_invoiced = student.total_invoiced
        student_new_invoiced = student.total_invoiced + amount_decimal

        # 2. Get school and calculate new values
        school = await db.get(School, school_id)
        if not school:
            logger.error(f"School {school_id} not found")
            return

        school_old_invoiced = school.total_invoiced
        school_new_invoiced = school.total_invoiced + amount_decimal

        # 3. Create movement record for student
        student_movement = AccountMovement(
            movement_type=MovementType.INVOICE_CREATED,
            entity_type=MovementEntityType.STUDENT,
            entity_id=student_id,
            field_name="total_invoiced",
            old_value=student_old_invoiced,
            new_value=student_new_invoiced,
            delta=amount_decimal,
            related_entity_type="Invoice",
            related_entity_id=invoice_id,
            description=f"Invoice #{invoice_id} created for ${amount}",
            created_by_user_id=user_id,
        )

        # 4. Create movement record for school
        school_movement = AccountMovement(
            movement_type=MovementType.INVOICE_CREATED,
            entity_type=MovementEntityType.SCHOOL,
            entity_id=school_id,
            field_name="total_invoiced",
            old_value=school_old_invoiced,
            new_value=school_new_invoiced,
            delta=amount_decimal,
            related_entity_type="Invoice",
            related_entity_id=invoice_id,
            description=f"Invoice #{invoice_id} created for student #{student_id}",
            created_by_user_id=user_id,
        )

        # 5. Update student denormalized fields
        student.total_invoiced = student_new_invoiced
        student.total_pending += amount_decimal
        student.cache_updated_at = datetime.utcnow()

        # 6. Update school denormalized fields
        school.total_invoiced = school_new_invoiced
        school.total_pending += amount_decimal
        school.cache_updated_at = datetime.utcnow()

        # 7. Commit all changes
        db.add(student_movement)
        db.add(school_movement)
        await db.commit()

        logger.info(f"Successfully processed invoice_created event for invoice {invoice_id}")

    except Exception as e:
        await db.rollback()
        logger.error(f"Error processing invoice_created event: {e}")
        raise
    finally:
        await db.close()


async def handle_invoice_updated(ctx, invoice_id: int, student_id: int, school_id: int,
                                 old_amount: float, new_amount: float, user_id: int = None):
    """
    Handle invoice updated event.

    Creates account movement and updates denormalized fields.
    """
    logger.info(f"Processing invoice_updated event for invoice {invoice_id}")

    db = await get_db()
    try:
        old_amount_decimal = Decimal(str(old_amount))
        new_amount_decimal = Decimal(str(new_amount))
        delta = new_amount_decimal - old_amount_decimal

        # 1. Get student and calculate new values
        student = await db.get(Student, student_id)
        if not student:
            logger.error(f"Student {student_id} not found")
            return

        student_old_invoiced = student.total_invoiced
        student_new_invoiced = student.total_invoiced + delta

        # 2. Get school and calculate new values
        school = await db.get(School, school_id)
        if not school:
            logger.error(f"School {school_id} not found")
            return

        school_old_invoiced = school.total_invoiced
        school_new_invoiced = school.total_invoiced + delta

        # 3. Create movement record for student
        student_movement = AccountMovement(
            movement_type=MovementType.INVOICE_UPDATED,
            entity_type=MovementEntityType.STUDENT,
            entity_id=student_id,
            field_name="total_invoiced",
            old_value=student_old_invoiced,
            new_value=student_new_invoiced,
            delta=delta,
            related_entity_type="Invoice",
            related_entity_id=invoice_id,
            description=f"Invoice #{invoice_id} updated: ${old_amount} → ${new_amount}",
            created_by_user_id=user_id,
        )

        # 4. Create movement record for school
        school_movement = AccountMovement(
            movement_type=MovementType.INVOICE_UPDATED,
            entity_type=MovementEntityType.SCHOOL,
            entity_id=school_id,
            field_name="total_invoiced",
            old_value=school_old_invoiced,
            new_value=school_new_invoiced,
            delta=delta,
            related_entity_type="Invoice",
            related_entity_id=invoice_id,
            description=f"Invoice #{invoice_id} updated for student #{student_id}",
            created_by_user_id=user_id,
        )

        # 5. Update student denormalized fields
        student.total_invoiced = student_new_invoiced
        student.total_pending += delta
        student.cache_updated_at = datetime.utcnow()

        # 6. Update school denormalized fields
        school.total_invoiced = school_new_invoiced
        school.total_pending += delta
        school.cache_updated_at = datetime.utcnow()

        # 7. Commit all changes
        db.add(student_movement)
        db.add(school_movement)
        await db.commit()

        logger.info(f"Successfully processed invoice_updated event for invoice {invoice_id}")

    except Exception as e:
        await db.rollback()
        logger.error(f"Error processing invoice_updated event: {e}")
        raise
    finally:
        await db.close()


async def handle_student_enrolled(ctx, student_id: int, school_id: int, user_id: int = None):
    """
    Handle student enrolled event.

    Creates account movement and updates school student counts.
    """
    logger.info(f"Processing student_enrolled event for student {student_id}")

    db = await get_db()
    try:
        # 1. Create movement record for school
        school_movement = AccountMovement(
            movement_type=MovementType.STUDENT_ENROLLED,
            entity_type=MovementEntityType.SCHOOL,
            entity_id=school_id,
            field_name="total_students",
            old_value=None,
            new_value=None,
            delta=Decimal('1'),
            related_entity_type="Student",
            related_entity_id=student_id,
            description=f"Student #{student_id} enrolled",
            created_by_user_id=user_id,
        )

        # 2. Update school denormalized fields
        school = await db.get(School, school_id)
        if school:
            school_movement.old_value = Decimal(str(school.total_students))
            school.total_students += 1
            school.active_students += 1
            school.cache_updated_at = datetime.utcnow()
            school_movement.new_value = Decimal(str(school.total_students))

        # 3. Commit changes
        db.add(school_movement)
        await db.commit()

        logger.info(f"Successfully processed student_enrolled event for student {student_id}")

    except Exception as e:
        await db.rollback()
        logger.error(f"Error processing student_enrolled event: {e}")
        raise
    finally:
        await db.close()


async def handle_student_status_changed(ctx, student_id: int, school_id: int,
                                        old_status: str, new_status: str, user_id: int = None):
    """
    Handle student status changed event.

    Updates school active student count.
    """
    logger.info(f"Processing student_status_changed event for student {student_id}")

    db = await get_db()
    try:
        # Calculate change in active students
        was_active = old_status == StudentStatus.ACTIVE.value
        is_active = new_status == StudentStatus.ACTIVE.value

        if was_active and not is_active:
            delta = -1  # Student became inactive
        elif not was_active and is_active:
            delta = 1  # Student became active
        else:
            delta = 0  # No change in active status

        if delta != 0:
            # 1. Create movement record
            school_movement = AccountMovement(
                movement_type=MovementType.STUDENT_STATUS_CHANGED,
                entity_type=MovementEntityType.SCHOOL,
                entity_id=school_id,
                field_name="active_students",
                old_value=None,
                new_value=None,
                delta=Decimal(str(delta)),
                related_entity_type="Student",
                related_entity_id=student_id,
                description=f"Student #{student_id} status: {old_status} → {new_status}",
                created_by_user_id=user_id,
            )

            # 2. Update school denormalized fields
            school = await db.get(School, school_id)
            if school:
                school_movement.old_value = Decimal(str(school.active_students))
                school.active_students += delta
                school.cache_updated_at = datetime.utcnow()
                school_movement.new_value = Decimal(str(school.active_students))

            # 3. Commit changes
            db.add(school_movement)
            await db.commit()

        logger.info(f"Successfully processed student_status_changed event for student {student_id}")

    except Exception as e:
        await db.rollback()
        logger.error(f"Error processing student_status_changed event: {e}")
        raise
    finally:
        await db.close()


# Worker configuration
class WorkerSettings:
    """arq worker configuration"""
    functions = [
        handle_payment_created,
        handle_invoice_created,
        handle_invoice_updated,
        handle_student_enrolled,
        handle_student_status_changed,
    ]

    redis_settings = RedisSettings(
        host=getattr(settings, 'REDIS_HOST', 'localhost'),
        port=getattr(settings, 'REDIS_PORT', 6379),
        database=getattr(settings, 'REDIS_DB', 0),
    )

    job_timeout = 300  # 5 minutes
    max_jobs = 10  # Process up to 10 jobs concurrently
    max_tries = 3  # Retry failed jobs up to 3 times
    keep_result = 3600  # Keep results for 1 hour
