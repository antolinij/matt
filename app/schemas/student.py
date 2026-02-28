"""Student schemas (Pydantic models)"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models import StudentStatus


class StudentBase(BaseModel):
    """Base student schema"""

    school_id: int
    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    enrollment_date: Optional[date] = None
    status: StudentStatus = StudentStatus.ACTIVE


class StudentCreate(StudentBase):
    """Schema for creating a student"""

    pass


class StudentUpdate(BaseModel):
    """Schema for updating a student"""

    school_id: Optional[int] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=255)
    last_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    enrollment_date: Optional[date] = None
    status: Optional[StudentStatus] = None


class Student(StudentBase):
    """Schema for student response"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
