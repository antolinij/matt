"""Student ORM model"""
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Enum as SQLEnum, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal
import enum
from app.core.database import Base


class StudentStatus(str, enum.Enum):
    """Student status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    GRADUATED = "graduated"


class Student(Base):
    """Student database model"""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    enrollment_date = Column(Date, nullable=True)
    status = Column(SQLEnum(StudentStatus), default=StudentStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Denormalized fields for fast queries (updated by events)
    total_invoiced = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'), server_default='0.00')
    total_paid = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'), server_default='0.00')
    total_pending = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'), server_default='0.00')
    cache_updated_at = Column(DateTime, nullable=True)  # When cache was last updated

    # Relationships
    school = relationship("School", back_populates="students")
    invoices = relationship("Invoice", back_populates="student", cascade="all, delete-orphan")
