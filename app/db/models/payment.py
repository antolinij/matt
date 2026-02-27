"""Payment ORM model"""
from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class PaymentMethod(str, enum.Enum):
    """Payment method enumeration"""
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    OTHER = "other"


class Payment(Base):
    """Payment database model"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(Date, nullable=False)
    payment_method = Column(SQLEnum(PaymentMethod), default=PaymentMethod.OTHER, nullable=False)
    reference = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")
