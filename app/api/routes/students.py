"""
Student API Routes

This module defines all HTTP endpoints for student management operations.
All routes use dependency injection for services and follow RESTful conventions.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from app.schemas import Student, StudentCreate, StudentUpdate, StudentAccountStatus, User
from app.services.student_service import StudentService
from app.core.security import get_current_active_user
from app.api.dependencies import get_student_service

router = APIRouter(prefix="/students", tags=["students"])


@router.post("", response_model=Student, status_code=status.HTTP_201_CREATED)
async def create_student(
    student: StudentCreate,
    service: StudentService = Depends(get_student_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new student. 🔒 Requires authentication.

    Args:
        student: StudentCreate schema with student data
        service: Injected StudentService instance

    Returns:
        Created student with generated ID and timestamps

    Raises:
        HTTPException 404: If the specified school does not exist
    """
    created_student = await service.create_student(student)
    if not created_student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    return created_student


@router.get("", response_model=List[Student])
async def list_students(
    skip: int = 0,
    limit: int = 100,
    school_id: Optional[int] = Query(None, description="Filter by school ID"),
    service: StudentService = Depends(get_student_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all students with pagination and optional filtering. 🔒 Requires authentication.

    Args:
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100)
        school_id: Optional school ID to filter students by
        service: Injected StudentService instance

    Returns:
        List of Student schemas
    """
    return await service.get_all_students(skip=skip, limit=limit, school_id=school_id)


@router.get("/{student_id}", response_model=Student)
async def get_student(
    student_id: int,
    service: StudentService = Depends(get_student_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific student by ID. 🔒 Requires authentication.

    Args:
        student_id: ID of the student to retrieve
        service: Injected StudentService instance

    Returns:
        Student schema with all details

    Raises:
        HTTPException 404: If student not found
    """
    student = await service.get_student(student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    return student


@router.put("/{student_id}", response_model=Student)
async def update_student(
    student_id: int,
    student: StudentUpdate,
    service: StudentService = Depends(get_student_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a student's information. 🔒 Requires authentication.

    Args:
        student_id: ID of the student to update
        student: StudentUpdate schema with updated data
        service: Injected StudentService instance

    Returns:
        Updated Student schema

    Raises:
        HTTPException 404: If student not found or new school_id does not exist
    """
    updated_student = await service.update_student(student_id, student)
    if not updated_student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found or invalid school_id"
        )
    return updated_student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: int,
    service: StudentService = Depends(get_student_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a student. 🔒 Requires authentication.

    Args:
        student_id: ID of the student to delete
        service: Injected StudentService instance

    Returns:
        None (204 No Content on success)

    Raises:
        HTTPException 404: If student not found

    Note:
        This will cascade delete all related invoices and payments
    """
    success = await service.delete_student(student_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    return None


@router.get("/{student_id}/account-status", response_model=StudentAccountStatus)
async def get_student_account_status(
    student_id: int,
    school_id: Optional[int] = Query(None, description="Validate that student belongs to this school"),
    service: StudentService = Depends(get_student_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get comprehensive account status for a student. 🔒 Requires authentication.

    Retrieves financial summary including:
    - Total invoiced amount
    - Total paid amount
    - Total pending/outstanding amount
    - Detailed list of all invoices with payment status

    Args:
        student_id: ID of the student
        school_id: Optional - If provided, validates that student belongs to this school
        service: Injected StudentService instance
        current_user: Currently authenticated user

    Returns:
        StudentAccountStatus schema with complete financial overview

    Raises:
        HTTPException 404: If student not found or student doesn't belong to specified school

    Examples:
        - GET /api/students/1/account-status
          Returns account status for student 1 (any school)

        - GET /api/students/1/account-status?school_id=5
          Returns account status for student 1 ONLY if they belong to school 5
          Otherwise returns 404
    """
    account_status = await service.get_account_status(student_id, school_id=school_id)
    if not account_status:
        if school_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student not found or doesn't belong to school {school_id}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
    return account_status
