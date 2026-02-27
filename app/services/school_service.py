"""School service for business logic"""
from typing import List, Optional
from app.repositories.school_repository import SchoolRepository
from app.schemas import School, SchoolCreate, SchoolUpdate, SchoolAccountStatus
from app.core.cache import cached, invalidate_cache_pattern


class SchoolService:
    """Service for School business logic"""

    def __init__(self, repository: SchoolRepository):
        self.repository = repository

    async def create_school(self, schema: SchoolCreate) -> School:
        """
        Create a new school

        Args:
            schema: SchoolCreate schema with school data

        Returns:
            School schema with created school data
        """
        db_school = await self.repository.create(
            name=schema.name,
            address=schema.address,
            phone=schema.phone,
            email=schema.email
        )

        # Invalidate list cache when creating new school
        await invalidate_cache_pattern("school:list:*")

        return School.model_validate(db_school)

    @cached(prefix="school:detail", ttl=300)  # Cache for 5 minutes
    async def get_school(self, school_id: int) -> Optional[School]:
        """
        Get a school by ID (cached)

        Args:
            school_id: ID of the school to retrieve

        Returns:
            School schema if found, None otherwise
        """
        db_school = await self.repository.get(school_id)
        if not db_school:
            return None
        return School.model_validate(db_school)

    @cached(prefix="school:list", ttl=180)  # Cache for 3 minutes
    async def get_all_schools(self, skip: int = 0, limit: int = 100) -> List[School]:
        """
        Get all schools with pagination (cached)

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of School schemas
        """
        db_schools = await self.repository.get_all(skip=skip, limit=limit)
        return [School.model_validate(school) for school in db_schools]

    async def update_school(self, school_id: int, schema: SchoolUpdate) -> Optional[School]:
        """
        Update a school

        Args:
            school_id: ID of the school to update
            schema: SchoolUpdate schema with updated data

        Returns:
            Updated School schema if found, None otherwise
        """
        # Check if school exists
        existing_school = await self.repository.get(school_id)
        if not existing_school:
            return None

        # Prepare update data (only include fields that are set)
        update_data = schema.model_dump(exclude_unset=True)

        db_school = await self.repository.update(school_id, **update_data)
        if not db_school:
            return None

        # Invalidate caches after update
        await invalidate_cache_pattern(f"school:detail:*{school_id}*")
        await invalidate_cache_pattern(f"school:account:*{school_id}*")
        await invalidate_cache_pattern("school:list:*")

        return School.model_validate(db_school)

    async def delete_school(self, school_id: int) -> bool:
        """
        Delete a school

        Args:
            school_id: ID of the school to delete

        Returns:
            True if deleted successfully, False otherwise

        Note:
            This will cascade delete all related students, invoices, and payments
        """
        # Check if school exists
        existing_school = await self.repository.get(school_id)
        if not existing_school:
            return False

        result = await self.repository.delete(school_id)

        # Invalidate all school-related caches after deletion
        await invalidate_cache_pattern(f"school:*{school_id}*")
        await invalidate_cache_pattern("school:list:*")
        await invalidate_cache_pattern("student:*")  # Students may be affected

        return result

    @cached(prefix="school:account", ttl=60)  # Cache for 1 minute (financial data changes frequently)
    async def get_account_status(self, school_id: int) -> Optional[SchoolAccountStatus]:
        """
        Get account status for a school (cached - 1 minute TTL)

        Args:
            school_id: ID of the school

        Returns:
            SchoolAccountStatus schema with financial summary, None if school not found
        """
        status_data = await self.repository.get_account_status(school_id)
        if not status_data:
            return None
        return SchoolAccountStatus.model_validate(status_data)

    @cached(prefix="school:student:account", ttl=60)  # Cache for 1 minute
    async def get_student_account_status(self, school_id: int, student_id: int):
        """
        Get account status for a specific student in a specific school (cached - 1 minute TTL)

        Args:
            school_id: ID of the school
            student_id: ID of the student

        Returns:
            StudentAccountStatus schema or None if not found/student doesn't belong to school
        """
        from app.schemas import StudentAccountStatus

        status_data = await self.repository.get_student_account_status(school_id, student_id)
        if not status_data:
            return None
        return StudentAccountStatus.model_validate(status_data)
