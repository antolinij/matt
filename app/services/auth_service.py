"""
Authentication Service

Business logic layer for user authentication operations.
Handles registration, login, token refresh, and password management.
"""
from typing import Optional
from fastapi import HTTPException, status

from app.repositories.user_repository import UserRepository
from app.db.models.user import User
from app.schemas import UserCreate, UserUpdate, Token
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class AuthService:
    """Service for authentication operations"""

    def __init__(self, user_repository: UserRepository):
        """
        Initialize service with repository.

        Args:
            user_repository: Repository for user data access
        """
        self.user_repository = user_repository

    async def register_user(self, user_data: UserCreate) -> User:
        """
        Register a new user.

        Args:
            user_data: User registration data

        Returns:
            Created user

        Raises:
            HTTPException: If username or email already exists
        """
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
        )

        return await self.user_repository.create(db_user)

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user by username/email and password.

        Args:
            username: Username or email
            password: Plain text password

        Returns:
            User if authentication successful, None otherwise
        """
        user = await self.user_repository.get_by_username_or_email(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def login(self, username: str, password: str) -> Token:
        """
        Login user and generate tokens.

        Args:
            username: Username or email
            password: Plain text password

        Returns:
            Token object with access and refresh tokens

        Raises:
            HTTPException: If authentication fails
        """
        user = await self.authenticate_user(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        # Update last login
        await self.user_repository.update_last_login(user.id)

        # Create tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    async def refresh_access_token(self, refresh_token: str) -> Token:
        """
        Generate new access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New token pair

        Raises:
            HTTPException: If refresh token is invalid or expired
        """
        try:
            payload = decode_token(refresh_token)
            token_type = payload.get("type")
            user_id = payload.get("sub")

            if token_type != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )

            # Verify user still exists and is active
            user = await self.user_repository.get(int(user_id))
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )

            # Generate new token pair
            new_access_token = create_access_token(data={"sub": str(user.id)})
            new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

            return Token(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_type="bearer"
            )

        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """
        Update user profile.

        Args:
            user_id: ID of user to update
            user_data: Updated user data

        Returns:
            Updated user

        Raises:
            HTTPException: If user not found or email already exists
        """
        user = await self.user_repository.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if new email already exists
        if user_data.email and user_data.email != user.email:
            existing_email = await self.user_repository.get_by_email(user_data.email)
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            user.email = user_data.email

        if user_data.full_name is not None:
            user.full_name = user_data.full_name

        if user_data.password:
            user.hashed_password = get_password_hash(user_data.password)

        return await self.user_repository.update(user)

    async def get_user(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User if found, None otherwise
        """
        return await self.user_repository.get(user_id)
