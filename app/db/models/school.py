"""School ORM model"""
from sqlalchemy import Column, Integer, String, DateTime, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal
from app.core.database import Base


class School(Base):
    """School database model"""
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Denormalized fields for fast queries (updated by events)
    total_students = Column(Integer, nullable=False, default=0, server_default='0')
    active_students = Column(Integer, nullable=False, default=0, server_default='0')
    total_invoiced = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'), server_default='0.00')
    total_paid = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'), server_default='0.00')
    total_pending = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'), server_default='0.00')
    cache_updated_at = Column(DateTime, nullable=True)  # When cache was last updated

    # Relationships
    students = relationship("Student", back_populates="school", cascade="all, delete-orphan")
