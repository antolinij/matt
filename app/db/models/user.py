"""User ORM model for authentication"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserRole(str, Enum):
    """User role enumeration"""

    ADMIN = "admin"
    SCHOOL_ADMIN = "school_admin"
    TEACHER = "teacher"
    USER = "user"


class User(Base):
    """User database model for authentication and authorization"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)

    # Status and permissions
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_login = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email}, role={self.role})>"
