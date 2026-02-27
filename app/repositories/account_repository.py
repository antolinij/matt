"""Account repository for historical queries"""
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AccountMovement,
    AccountSnapshot,
    MovementType,
    MovementEntityType,
    SnapshotType,
    SnapshotEntityType,
)


class AccountRepository:
    """Repository for historical account queries"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Movement Queries ====================

    async def get_movements_by_entity(
        self,
        entity_type: MovementEntityType,
        entity_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[AccountMovement]:
        """
        Get all movements for a specific entity (school or student).

        Args:
            entity_type: Type of entity (SCHOOL or STUDENT)
            entity_id: ID of the entity
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of AccountMovement objects ordered by created_at DESC
        """
        stmt = (
            select(AccountMovement)
            .where(
                and_(
                    AccountMovement.entity_type == entity_type,
                    AccountMovement.entity_id == entity_id
                )
            )
            .order_by(AccountMovement.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_movements_by_period(
        self,
        entity_type: MovementEntityType,
        entity_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[AccountMovement]:
        """
        Get movements for an entity within a date range.

        Args:
            entity_type: Type of entity (SCHOOL or STUDENT)
            entity_id: ID of the entity
            start_date: Start of period
            end_date: End of period

        Returns:
            List of AccountMovement objects ordered by created_at
        """
        stmt = (
            select(AccountMovement)
            .where(
                and_(
                    AccountMovement.entity_type == entity_type,
                    AccountMovement.entity_id == entity_id,
                    AccountMovement.created_at >= start_date,
                    AccountMovement.created_at <= end_date
                )
            )
            .order_by(AccountMovement.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_movements_by_type(
        self,
        entity_type: MovementEntityType,
        entity_id: int,
        movement_type: MovementType,
        skip: int = 0,
        limit: int = 100
    ) -> List[AccountMovement]:
        """
        Get movements of a specific type for an entity.

        Args:
            entity_type: Type of entity (SCHOOL or STUDENT)
            entity_id: ID of the entity
            movement_type: Type of movement to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of AccountMovement objects
        """
        stmt = (
            select(AccountMovement)
            .where(
                and_(
                    AccountMovement.entity_type == entity_type,
                    AccountMovement.entity_id == entity_id,
                    AccountMovement.movement_type == movement_type
                )
            )
            .order_by(AccountMovement.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def calculate_period_totals(
        self,
        entity_type: MovementEntityType,
        entity_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """
        Calculate aggregated totals for an entity during a period.

        Args:
            entity_type: Type of entity (SCHOOL or STUDENT)
            entity_id: ID of the entity
            start_date: Start of period
            end_date: End of period

        Returns:
            Dictionary with total_invoiced, total_paid, and net_change
        """
        # Get all movements in period
        movements = await self.get_movements_by_period(
            entity_type, entity_id, start_date, end_date
        )

        total_invoiced = Decimal('0.00')
        total_paid = Decimal('0.00')

        for movement in movements:
            if movement.movement_type in [MovementType.INVOICE_CREATED, MovementType.INVOICE_UPDATED]:
                total_invoiced += movement.delta
            elif movement.movement_type == MovementType.PAYMENT_RECEIVED:
                total_paid += movement.delta

        return {
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "net_change": total_invoiced - total_paid,
            "movement_count": len(movements)
        }

    # ==================== Snapshot Queries ====================

    async def get_snapshot_at_date(
        self,
        entity_type: SnapshotEntityType,
        entity_id: int,
        target_date: date,
        snapshot_type: SnapshotType = SnapshotType.DAILY
    ) -> Optional[AccountSnapshot]:
        """
        Get snapshot for a specific date (or closest available before that date).

        Args:
            entity_type: Type of entity (SCHOOL or STUDENT)
            entity_id: ID of the entity
            target_date: Date to get snapshot for
            snapshot_type: Type of snapshot (DAILY, MONTHLY, etc.)

        Returns:
            AccountSnapshot if found, None otherwise
        """
        stmt = (
            select(AccountSnapshot)
            .where(
                and_(
                    AccountSnapshot.entity_type == entity_type,
                    AccountSnapshot.entity_id == entity_id,
                    AccountSnapshot.snapshot_type == snapshot_type,
                    AccountSnapshot.snapshot_date <= target_date
                )
            )
            .order_by(AccountSnapshot.snapshot_date.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_snapshots_by_period(
        self,
        entity_type: SnapshotEntityType,
        entity_id: int,
        start_date: date,
        end_date: date,
        snapshot_type: SnapshotType = SnapshotType.DAILY
    ) -> List[AccountSnapshot]:
        """
        Get all snapshots for an entity within a date range.

        Args:
            entity_type: Type of entity (SCHOOL or STUDENT)
            entity_id: ID of the entity
            start_date: Start of period
            end_date: End of period
            snapshot_type: Type of snapshot

        Returns:
            List of AccountSnapshot objects ordered by date
        """
        stmt = (
            select(AccountSnapshot)
            .where(
                and_(
                    AccountSnapshot.entity_type == entity_type,
                    AccountSnapshot.entity_id == entity_id,
                    AccountSnapshot.snapshot_type == snapshot_type,
                    AccountSnapshot.snapshot_date >= start_date,
                    AccountSnapshot.snapshot_date <= end_date
                )
            )
            .order_by(AccountSnapshot.snapshot_date)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_snapshot(
        self,
        entity_type: SnapshotEntityType,
        entity_id: int,
        snapshot_date: date,
        snapshot_type: SnapshotType,
        total_students: Optional[int] = None,
        active_students: Optional[int] = None,
        total_invoiced: Decimal = Decimal('0.00'),
        total_paid: Decimal = Decimal('0.00'),
        total_pending: Decimal = Decimal('0.00')
    ) -> AccountSnapshot:
        """
        Create a new snapshot.

        Args:
            entity_type: Type of entity (SCHOOL or STUDENT)
            entity_id: ID of the entity
            snapshot_date: Date of the snapshot
            snapshot_type: Type of snapshot
            total_students: Total student count (for schools only)
            active_students: Active student count (for schools only)
            total_invoiced: Total invoiced amount
            total_paid: Total paid amount
            total_pending: Total pending amount

        Returns:
            Created AccountSnapshot object
        """
        snapshot = AccountSnapshot(
            entity_type=entity_type,
            entity_id=entity_id,
            snapshot_date=snapshot_date,
            snapshot_type=snapshot_type,
            total_students=total_students,
            active_students=active_students,
            total_invoiced=total_invoiced,
            total_paid=total_paid,
            total_pending=total_pending
        )
        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)
        return snapshot

    # ==================== Advanced Queries ====================

    async def get_account_status_at_date(
        self,
        entity_type: MovementEntityType,
        entity_id: int,
        target_date: datetime
    ) -> dict:
        """
        Calculate account status at a specific point in time.

        Strategy:
        1. Get closest snapshot before target date (if available)
        2. Apply movements from snapshot date to target date
        3. Return calculated totals

        Args:
            entity_type: Type of entity (SCHOOL or STUDENT)
            entity_id: ID of the entity
            target_date: Date to calculate status for

        Returns:
            Dictionary with total_invoiced, total_paid, total_pending
        """
        # Convert datetime to date for snapshot query
        target_date_only = target_date.date()

        # Try to get closest snapshot
        snapshot = await self.get_snapshot_at_date(
            SnapshotEntityType(entity_type.value),
            entity_id,
            target_date_only
        )

        if snapshot:
            # Start from snapshot values
            total_invoiced = snapshot.total_invoiced
            total_paid = snapshot.total_paid
            total_pending = snapshot.total_pending
            start_date = datetime.combine(snapshot.snapshot_date, datetime.min.time())
        else:
            # No snapshot, start from zero
            total_invoiced = Decimal('0.00')
            total_paid = Decimal('0.00')
            total_pending = Decimal('0.00')
            start_date = datetime.min

        # Get movements from snapshot/start to target date
        movements = await self.get_movements_by_period(
            entity_type, entity_id, start_date, target_date
        )

        # Apply movements
        for movement in movements:
            if movement.field_name == "total_invoiced":
                total_invoiced += movement.delta
            elif movement.field_name == "total_paid":
                total_paid += movement.delta

        # Recalculate pending
        total_pending = total_invoiced - total_paid

        return {
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "total_pending": total_pending,
            "calculated_at": target_date,
            "used_snapshot": snapshot is not None,
            "snapshot_date": snapshot.snapshot_date if snapshot else None
        }
