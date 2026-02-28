"""
School API Routes

This module defines all HTTP endpoints for school management operations.
All routes use dependency injection for services and follow RESTful conventions.
All endpoints require JWT authentication.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_school_service
from app.core.security import get_current_active_user
from app.schemas import (School, SchoolAccountStatus, SchoolCreate,
                         SchoolUpdate, StudentAccountStatus, User)
from app.services.school_service import SchoolService

router = APIRouter(prefix="/schools", tags=["schools"])


@router.post("", response_model=School, status_code=status.HTTP_201_CREATED)
async def create_school(
    school: SchoolCreate,
    service: SchoolService = Depends(get_school_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new school. 🔒 Requires authentication.

    Args:
        school: SchoolCreate schema with school data
        service: Injected SchoolService instance
        current_user: Currently authenticated user

    Returns:
        Created school with generated ID and timestamps

    Raises:
        HTTPException: If validation fails or database error occurs
    """
    return await service.create_school(school)


@router.get("", response_model=List[School])
async def list_schools(
    skip: int = 0,
    limit: int = 100,
    service: SchoolService = Depends(get_school_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all schools with pagination. 🔒 Requires authentication.

    Args:
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100)
        service: Injected SchoolService instance
        current_user: Currently authenticated user

    Returns:
        List of School schemas
    """
    return await service.get_all_schools(skip=skip, limit=limit)


@router.get("/{school_id}", response_model=School)
async def get_school(
    school_id: int,
    service: SchoolService = Depends(get_school_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific school by ID. 🔒 Requires authentication.

    Args:
        school_id: ID of the school to retrieve
        service: Injected SchoolService instance
        current_user: Currently authenticated user

    Returns:
        School schema with all details

    Raises:
        HTTPException 404: If school not found
    """
    school = await service.get_school(school_id)
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="School not found"
        )
    return school


@router.put("/{school_id}", response_model=School)
async def update_school(
    school_id: int,
    school: SchoolUpdate,
    service: SchoolService = Depends(get_school_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a school's information. 🔒 Requires authentication.

    Args:
        school_id: ID of the school to update
        school: SchoolUpdate schema with updated data
        service: Injected SchoolService instance
        current_user: Currently authenticated user

    Returns:
        Updated School schema

    Raises:
        HTTPException 404: If school not found
    """
    updated_school = await service.update_school(school_id, school)
    if not updated_school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="School not found"
        )
    return updated_school


@router.delete("/{school_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_school(
    school_id: int,
    service: SchoolService = Depends(get_school_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a school. 🔒 Requires authentication.

    Args:
        school_id: ID of the school to delete
        service: Injected SchoolService instance
        current_user: Currently authenticated user

    Returns:
        None (204 No Content on success)

    Raises:
        HTTPException 404: If school not found

    Note:
        This will cascade delete all related students, invoices, and payments
    """
    success = await service.delete_school(school_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="School not found"
        )
    return None


@router.get("/{school_id}/account-status", response_model=SchoolAccountStatus)
async def get_school_account_status(
    school_id: int,
    service: SchoolService = Depends(get_school_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get comprehensive account status for a school. 🔒 Requires authentication.

    Retrieves financial summary including:
    - Total number of students (all and active)
    - Total invoiced amount across all students
    - Total paid amount
    - Total pending/outstanding amount
    - Detailed list of all invoices with payment status

    Args:
        school_id: ID of the school
        service: Injected SchoolService instance
        current_user: Currently authenticated user

    Returns:
        SchoolAccountStatus schema with complete financial overview

    Raises:
        HTTPException 404: If school not found
    """
    account_status = await service.get_account_status(school_id)
    if not account_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="School not found"
        )
    return account_status


@router.get(
    "/{school_id}/students/{student_id}/account-status",
    response_model=StudentAccountStatus,
)
async def get_school_student_account_status(
    school_id: int,
    student_id: int,
    service: SchoolService = Depends(get_school_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get account status for a specific student within a specific school. 🔒 Requires authentication.

    This endpoint follows RESTful nested resource pattern and validates that
    the student belongs to the specified school before returning their financial data.

    Retrieves:
    - Student information
    - Total invoiced amount for this student
    - Total paid amount
    - Total pending/outstanding amount
    - Detailed list of all invoices with payment status

    Args:
        school_id: ID of the school
        student_id: ID of the student
        service: Injected SchoolService instance
        current_user: Currently authenticated user

    Returns:
        StudentAccountStatus schema with complete financial overview

    Raises:
        HTTPException 404: If school not found, student not found, or student doesn't belong to school

    Example:
        GET /api/schools/11/students/8/account-status
        Returns account status for student 8 ONLY if they belong to school 11
    """
    account_status = await service.get_student_account_status(school_id, student_id)
    if not account_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found, student not found, or student doesn't belong to this school",
        )
    return account_status
