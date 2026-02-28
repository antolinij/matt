"""User Pydantic schemas for API requests/responses"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema with common fields"""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user registration"""

    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login"""

    username: str = Field(..., description="Username or email")
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile"""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)


class User(UserBase):
    """Schema for user response (excludes password)"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_superuser: bool
    role: UserRole
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None


class UserInDB(User):
    """Schema for user in database (includes hashed password)"""

    hashed_password: str
