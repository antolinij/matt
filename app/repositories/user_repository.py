"""
User Repository

Data access layer for User model operations.
Handles all database interactions for user management.
"""
from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, OperationalError, DataError
from datetime import datetime

from app.db.models.user import User
from app.core.exceptions import (
    DuplicateRecordException,
    DatabaseConnectionException,
    DatabaseOperationException,
    InvalidDataException
)


class UserRepository:
    """Repository for User model database operations"""

    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            db: SQLAlchemy async session
        """
        self.db = db

    async def create(self, user: User) -> User:
        """
        Create a new user in the database.

        Args:
            user: User model instance to create

        Returns:
            Created user with generated ID

        Raises:
            DuplicateRecordException: If username or email already exists
            DatabaseConnectionException: If database connection fails
            InvalidDataException: If data validation fails
            DatabaseOperationException: If operation fails for other reasons
        """
        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = str(e.orig).lower()

            # Check which constraint was violated
            if 'username' in error_msg or 'ix_users_username' in error_msg:
                raise DuplicateRecordException("User", "username", user.username)
            elif 'email' in error_msg or 'ix_users_email' in error_msg:
                raise DuplicateRecordException("User", "email", user.email)
            else:
                raise DatabaseOperationException("create", "User", str(e.orig))
        except DataError as e:
            await self.db.rollback()
            raise InvalidDataException("User", str(e.orig))
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("create", "User", str(e))

    async def get(self, user_id: int) -> Optional[User]:
        """
        Get a user by ID.

        Args:
            user_id: ID of the user to retrieve

        Returns:
            User model instance or None if not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            result = await self.db.execute(
                select(User).filter(User.id == user_id)
            )
            return result.scalar_one_or_none()
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get", "User", str(e))

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by username.

        Args:
            username: Username to search for

        Returns:
            User model instance or None if not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            result = await self.db.execute(
                select(User).filter(User.username == username)
            )
            return result.scalar_one_or_none()
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get_by_username", "User", str(e))

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email.

        Args:
            email: Email to search for

        Returns:
            User model instance or None if not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            result = await self.db.execute(
                select(User).filter(User.email == email)
            )
            return result.scalar_one_or_none()
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get_by_email", "User", str(e))

    async def get_by_username_or_email(self, identifier: str) -> Optional[User]:
        """
        Get a user by username or email.

        Args:
            identifier: Username or email to search for

        Returns:
            User model instance or None if not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            result = await self.db.execute(
                select(User).filter(
                    or_(User.username == identifier, User.email == identifier)
                )
            )
            return result.scalar_one_or_none()
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get_by_username_or_email", "User", str(e))

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get all users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of User model instances

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            result = await self.db.execute(
                select(User).offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except OperationalError as e:
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            raise DatabaseOperationException("get_all", "User", str(e))

    async def update(self, user: User) -> User:
        """
        Update a user in the database.

        Args:
            user: User model instance with updated values

        Returns:
            Updated user

        Raises:
            DuplicateRecordException: If username or email already exists
            DatabaseConnectionException: If database connection fails
            InvalidDataException: If data validation fails
            DatabaseOperationException: If operation fails for other reasons
        """
        try:
            username = user.username
            email = user.email
            user.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = str(e.orig).lower()

            # Check which constraint was violated
            if 'username' in error_msg or 'ix_users_username' in error_msg:
                raise DuplicateRecordException("User", "username", username)
            elif 'email' in error_msg or 'ix_users_email' in error_msg:
                raise DuplicateRecordException("User", "email", email)
            else:
                raise DatabaseOperationException("update", "User", str(e.orig))
        except DataError as e:
            await self.db.rollback()
            raise InvalidDataException("User", str(e.orig))
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("update", "User", str(e))

    async def update_last_login(self, user_id: int) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: ID of the user

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            user = await self.get(user_id)
            if user:
                user.last_login = datetime.utcnow()
                await self.db.commit()
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("update_last_login", "User", str(e))

    async def delete(self, user_id: int) -> bool:
        """
        Delete a user from the database.

        Args:
            user_id: ID of the user to delete

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseConnectionException: If database connection fails
            DatabaseOperationException: If operation fails
        """
        try:
            user = await self.get(user_id)
            if user:
                await self.db.delete(user)
                await self.db.commit()
                return True
            return False
        except OperationalError as e:
            await self.db.rollback()
            raise DatabaseConnectionException(str(e.orig))
        except Exception as e:
            await self.db.rollback()
            raise DatabaseOperationException("delete", "User", str(e))
