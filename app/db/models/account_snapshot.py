"""
Account Snapshot Model

Stores periodic snapshots of account state for fast historical queries.
This enables answering questions like:
- How many students did the school have on January 31st?
- What was the outstanding balance at the end of last quarter?
- Show me monthly revenue for the past year
"""
from sqlalchemy import Column, Integer, Date, Numeric, DateTime, Enum as SQLEnum, Index, UniqueConstraint
from sqlalchemy.sql import func
from datetime import datetime, date
from decimal import Decimal
import enum

from app.core.database import Base


class SnapshotType(str, enum.Enum):
    """Frequency of snapshot"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class EntityType(str, enum.Enum):
    """Type of entity the snapshot is for"""
    SCHOOL = "school"
    STUDENT = "student"


class AccountSnapshot(Base):
    """
    Account Snapshot - Point-in-time state for fast historical queries

    This table provides:
    - Fast historical queries (no aggregation needed)
    - Trend analysis
    - Reporting dashboards
    - Time-series data
    """
    __tablename__ = "account_snapshots"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Snapshot identification
    entity_type = Column(SQLEnum(EntityType), nullable=False)
    entity_id = Column(Integer, nullable=False)  # school_id or student_id
    snapshot_date = Column(Date, nullable=False)  # Date this snapshot represents
    snapshot_type = Column(SQLEnum(SnapshotType), nullable=False, default=SnapshotType.DAILY)

    # Student counts (for schools only, NULL for students)
    total_students = Column(Integer, nullable=True)
    active_students = Column(Integer, nullable=True)
    inactive_students = Column(Integer, nullable=True)

    # Financial data (for both schools and students)
    total_invoiced = Column(Numeric(10, 2), nullable=False, default=0)
    total_paid = Column(Numeric(10, 2), nullable=False, default=0)
    total_pending = Column(Numeric(10, 2), nullable=False, default=0)

    # Invoice counts
    total_invoices = Column(Integer, nullable=True)
    paid_invoices = Column(Integer, nullable=True)
    pending_invoices = Column(Integer, nullable=True)
    overdue_invoices = Column(Integer, nullable=True)

    # Payment counts
    total_payments = Column(Integer, nullable=True)
    payments_this_period = Column(Integer, nullable=True)  # Since last snapshot

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())

    # Constraints
    __table_args__ = (
        # One snapshot per entity per date per type
        UniqueConstraint(
            'entity_type',
            'entity_id',
            'snapshot_date',
            'snapshot_type',
            name='uq_snapshot_entity_date_type'
        ),

        # Fast queries by entity and date
        Index('ix_snapshots_entity_date', 'entity_type', 'entity_id', 'snapshot_date'),

        # Fast queries by snapshot type
        Index('ix_snapshots_type_date', 'snapshot_type', 'snapshot_date'),

        # Fast queries by date range
        Index('ix_snapshots_date', 'snapshot_date'),
    )

    def __repr__(self):
        return (
            f"<AccountSnapshot(id={self.id}, "
            f"entity={self.entity_type}:{self.entity_id}, "
            f"date={self.snapshot_date}, "
            f"type={self.snapshot_type})>"
        )

    @property
    def collection_rate(self) -> float:
        """Calculate collection rate (paid / invoiced)"""
        if not self.total_invoiced or self.total_invoiced == 0:
            return 0.0
        return float((self.total_paid / self.total_invoiced) * 100)

    @property
    def outstanding_rate(self) -> float:
        """Calculate outstanding rate (pending / invoiced)"""
        if not self.total_invoiced or self.total_invoiced == 0:
            return 0.0
        return float((self.total_pending / self.total_invoiced) * 100)
