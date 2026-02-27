"""
Event Service

Publishes events to message queue for asynchronous processing.
Used to decouple payment/invoice creation from account movement tracking.
"""
from typing import Dict, Any, Optional
import logging
from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings

logger = logging.getLogger(__name__)


class EventService:
    """
    Service for publishing events to message queue.

    Events are processed asynchronously by background workers,
    allowing fast API responses while maintaining data consistency.
    """

    def __init__(self):
        self._pool = None

    async def get_pool(self):
        """Get or create Redis connection pool"""
        if self._pool is None:
            self._pool = await create_pool(
                RedisSettings(
                    host=getattr(settings, 'REDIS_HOST', 'localhost'),
                    port=getattr(settings, 'REDIS_PORT', 6379),
                    database=getattr(settings, 'REDIS_DB', 0),
                )
            )
        return self._pool

    async def publish_payment_created(
        self,
        payment_id: int,
        invoice_id: int,
        student_id: int,
        school_id: int,
        amount: float,
        user_id: Optional[int] = None
    ) -> None:
        """
        Publish payment created event.

        Args:
            payment_id: ID of the payment
            invoice_id: ID of the invoice
            student_id: ID of the student
            school_id: ID of the school
            amount: Payment amount
            user_id: ID of the user who created the payment
        """
        try:
            pool = await self.get_pool()
            await pool.enqueue_job(
                'handle_payment_created',
                payment_id=payment_id,
                invoice_id=invoice_id,
                student_id=student_id,
                school_id=school_id,
                amount=amount,
                user_id=user_id,
            )
            logger.info(f"Published payment_created event for payment {payment_id}")
        except Exception as e:
            logger.error(f"Failed to publish payment_created event: {e}")
            # Don't raise - we don't want to fail the payment creation
            # Event will be missing, but can be regenerated from database if needed

    async def publish_invoice_created(
        self,
        invoice_id: int,
        student_id: int,
        school_id: int,
        amount: float,
        user_id: Optional[int] = None
    ) -> None:
        """
        Publish invoice created event.

        Args:
            invoice_id: ID of the invoice
            student_id: ID of the student
            school_id: ID of the school
            amount: Invoice amount
            user_id: ID of the user who created the invoice
        """
        try:
            pool = await self.get_pool()
            await pool.enqueue_job(
                'handle_invoice_created',
                invoice_id=invoice_id,
                student_id=student_id,
                school_id=school_id,
                amount=amount,
                user_id=user_id,
            )
            logger.info(f"Published invoice_created event for invoice {invoice_id}")
        except Exception as e:
            logger.error(f"Failed to publish invoice_created event: {e}")

    async def publish_invoice_updated(
        self,
        invoice_id: int,
        student_id: int,
        school_id: int,
        old_amount: float,
        new_amount: float,
        user_id: Optional[int] = None
    ) -> None:
        """
        Publish invoice updated event.

        Args:
            invoice_id: ID of the invoice
            student_id: ID of the student
            school_id: ID of the school
            old_amount: Previous invoice amount
            new_amount: New invoice amount
            user_id: ID of the user who updated the invoice
        """
        try:
            pool = await self.get_pool()
            await pool.enqueue_job(
                'handle_invoice_updated',
                invoice_id=invoice_id,
                student_id=student_id,
                school_id=school_id,
                old_amount=old_amount,
                new_amount=new_amount,
                user_id=user_id,
            )
            logger.info(f"Published invoice_updated event for invoice {invoice_id}")
        except Exception as e:
            logger.error(f"Failed to publish invoice_updated event: {e}")

    async def publish_student_enrolled(
        self,
        student_id: int,
        school_id: int,
        user_id: Optional[int] = None
    ) -> None:
        """
        Publish student enrolled event.

        Args:
            student_id: ID of the student
            school_id: ID of the school
            user_id: ID of the user who enrolled the student
        """
        try:
            pool = await self.get_pool()
            await pool.enqueue_job(
                'handle_student_enrolled',
                student_id=student_id,
                school_id=school_id,
                user_id=user_id,
            )
            logger.info(f"Published student_enrolled event for student {student_id}")
        except Exception as e:
            logger.error(f"Failed to publish student_enrolled event: {e}")

    async def publish_student_status_changed(
        self,
        student_id: int,
        school_id: int,
        old_status: str,
        new_status: str,
        user_id: Optional[int] = None
    ) -> None:
        """
        Publish student status changed event.

        Args:
            student_id: ID of the student
            school_id: ID of the school
            old_status: Previous student status
            new_status: New student status
            user_id: ID of the user who changed the status
        """
        try:
            pool = await self.get_pool()
            await pool.enqueue_job(
                'handle_student_status_changed',
                student_id=student_id,
                school_id=school_id,
                old_status=old_status,
                new_status=new_status,
                user_id=user_id,
            )
            logger.info(f"Published student_status_changed event for student {student_id}")
        except Exception as e:
            logger.error(f"Failed to publish student_status_changed event: {e}")

    async def close(self):
        """Close Redis connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None


# Global event service instance
event_service = EventService()
