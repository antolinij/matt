"""School schemas (Pydantic models)"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SchoolBase(BaseModel):
    """Base school schema"""

    name: str = Field(..., min_length=1, max_length=255)
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class SchoolCreate(SchoolBase):
    """Schema for creating a school"""

    pass


class SchoolUpdate(BaseModel):
    """Schema for updating a school"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class School(SchoolBase):
    """Schema for school response"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
