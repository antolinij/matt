"""Student service for business logic"""
from typing import List, Optional
from app.repositories.student_repository import StudentRepository
from app.repositories.school_repository import SchoolRepository
from app.schemas import Student, StudentCreate, StudentUpdate, StudentAccountStatus
from app.core.exceptions import ForeignKeyViolationException


class StudentService:
    """Service for Student business logic"""

    def __init__(self, repository: StudentRepository, school_repository: SchoolRepository):
        self.repository = repository
        self.school_repository = school_repository

    async def create_student(self, schema: StudentCreate) -> Optional[Student]:
        """
        Create a new student

        Args:
            schema: StudentCreate schema with student data

        Returns:
            Student schema with created student data, None if school doesn't exist

        Business Rules:
            - School must exist before creating a student
        """
        # Verify school exists
        school = await self.school_repository.get(schema.school_id)
        if not school:
            raise ForeignKeyViolationException("Student", "school_id", schema.school_id)

        db_student = await self.repository.create(
            school_id=schema.school_id,
            first_name=schema.first_name,
            last_name=schema.last_name,
            email=schema.email,
            enrollment_date=schema.enrollment_date,
            status=schema.status
        )
        return Student.model_validate(db_student)

    async def get_student(self, student_id: int) -> Optional[Student]:
        """
        Get a student by ID

        Args:
            student_id: ID of the student to retrieve

        Returns:
            Student schema if found, None otherwise
        """
        db_student = await self.repository.get(student_id)
        if not db_student:
            return None
        return Student.model_validate(db_student)

    async def get_all_students(
        self,
        skip: int = 0,
        limit: int = 100,
        school_id: Optional[int] = None
    ) -> List[Student]:
        """
        Get all students with pagination and optional school filter

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            school_id: Optional school ID to filter by

        Returns:
            List of Student schemas
        """
        db_students = await self.repository.get_all(
            skip=skip,
            limit=limit,
            school_id=school_id
        )
        return [Student.model_validate(student) for student in db_students]

    async def update_student(self, student_id: int, schema: StudentUpdate) -> Optional[Student]:
        """
        Update a student

        Args:
            student_id: ID of the student to update
            schema: StudentUpdate schema with updated data

        Returns:
            Updated Student schema if found, None otherwise

        Business Rules:
            - If changing school_id, new school must exist
        """
        # Check if student exists
        existing_student = await self.repository.get(student_id)
        if not existing_student:
            return None

        # If updating school_id, verify new school exists
        update_data = schema.model_dump(exclude_unset=True)
        if 'school_id' in update_data:
            new_school = await self.school_repository.get(update_data['school_id'])
            if not new_school:
                raise ForeignKeyViolationException("Student", "school_id", update_data["school_id"])

        db_student = await self.repository.update(student_id, **update_data)
        if not db_student:
            return None
        return Student.model_validate(db_student)

    async def delete_student(self, student_id: int) -> bool:
        """
        Delete a student

        Args:
            student_id: ID of the student to delete

        Returns:
            True if deleted successfully, False otherwise

        Note:
            This will cascade delete all related invoices and payments
        """
        # Check if student exists
        existing_student = await self.repository.get(student_id)
        if not existing_student:
            return False

        return await self.repository.delete(student_id)

    async def get_account_status(
        self,
        student_id: int,
        school_id: Optional[int] = None
    ) -> Optional[StudentAccountStatus]:
        """
        Get account status for a student (all financial data)

        Args:
            student_id: ID of the student
            school_id: Optional - If provided, validates that student belongs to this school

        Returns:
            StudentAccountStatus schema with financial summary,
            None if student not found or doesn't belong to specified school
        """
        # If school_id provided, validate student belongs to that school
        if school_id is not None:
            student = await self.repository.get(student_id)
            if not student or student.school_id != school_id:
                return None

        status_data = await self.repository.get_account_status(student_id)
        if not status_data:
            return None
        return StudentAccountStatus.model_validate(status_data)
