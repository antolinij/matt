"""Invoice ORM model"""
from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class InvoiceStatus(str, enum.Enum):
    """Invoice status enumeration"""
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(Base):
    """Invoice database model"""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    invoice_number = Column(String, unique=True, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    issue_date = Column(Date, nullable=False)
    description = Column(String, nullable=True)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    student = relationship("Student", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
