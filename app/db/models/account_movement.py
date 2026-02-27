"""
Account Movement Model

Tracks every change to account balances for complete audit trail and historical queries.
This enables answering questions like:
- How much did a student pay in January?
- What was the school's revenue last quarter?
- Show me all account changes for this student
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum as SQLEnum, Index
from sqlalchemy.sql import func
from datetime import datetime
from decimal import Decimal
import enum

from app.core.database import Base


class MovementType(str, enum.Enum):
    """Type of account movement"""
    # Invoice events
    INVOICE_CREATED = "invoice_created"
    INVOICE_UPDATED = "invoice_updated"
    INVOICE_CANCELLED = "invoice_cancelled"

    # Payment events
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_REFUNDED = "payment_refunded"

    # Student events
    STUDENT_ENROLLED = "student_enrolled"
    STUDENT_WITHDRAWN = "student_withdrawn"
    STUDENT_STATUS_CHANGED = "student_status_changed"

    # Adjustment events
    MANUAL_ADJUSTMENT = "manual_adjustment"
    BALANCE_CORRECTION = "balance_correction"


class EntityType(str, enum.Enum):
    """Type of entity the movement is for"""
    SCHOOL = "school"
    STUDENT = "student"


class AccountMovement(Base):
    """
    Account Movement - Event Log for all balance changes

    This table provides:
    - Complete audit trail
    - Historical reporting capability
    - Compliance and debugging
    - Event sourcing foundation
    """
    __tablename__ = "account_movements"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Movement classification
    movement_type = Column(SQLEnum(MovementType), nullable=False)
    entity_type = Column(SQLEnum(EntityType), nullable=False)
    entity_id = Column(Integer, nullable=False)  # school_id or student_id

    # What changed
    field_name = Column(String(50), nullable=False)  # "total_invoiced", "total_paid", "total_students"
    old_value = Column(Numeric(10, 2), nullable=True)  # Previous value
    new_value = Column(Numeric(10, 2), nullable=False)  # New value
    delta = Column(Numeric(10, 2), nullable=False)  # Change amount (new - old)

    # Context - what caused this change
    related_entity_type = Column(String(50), nullable=True)  # "Invoice", "Payment", "Student"
    related_entity_id = Column(Integer, nullable=True)  # ID of the invoice/payment/student
    description = Column(String(500), nullable=True)  # Human-readable description

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    created_by_user_id = Column(Integer, nullable=True)  # Who made this change

    # Indexes for fast queries
    __table_args__ = (
        # Query by entity (e.g., all movements for school #5)
        Index('ix_account_movements_entity', 'entity_type', 'entity_id', 'created_at'),

        # Query by movement type (e.g., all payments received)
        Index('ix_account_movements_type', 'movement_type', 'created_at'),

        # Query by date range (e.g., all movements in January)
        Index('ix_account_movements_date', 'created_at'),

        # Query related entity (e.g., find movement for invoice #123)
        Index('ix_account_movements_related', 'related_entity_type', 'related_entity_id'),
    )

    def __repr__(self):
        return (
            f"<AccountMovement(id={self.id}, "
            f"type={self.movement_type}, "
            f"entity={self.entity_type}:{self.entity_id}, "
            f"delta={self.delta})>"
        )

    @property
    def amount_formatted(self) -> str:
        """Format delta for display"""
        sign = "+" if self.delta > 0 else ""
        return f"{sign}${abs(self.delta):,.2f}"
