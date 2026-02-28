"""
Authentication API Routes

This module defines all HTTP endpoints for authentication operations including
registration, login, token refresh, and user profile management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import get_auth_service
from app.core.security import get_current_active_user
from app.schemas import RefreshTokenRequest, Token, User, UserCreate
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate, auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user account.

    Args:
        user_data: UserCreate schema with registration information
        auth_service: Injected AuthService instance

    Returns:
        Created user (without password)

    Raises:
        HTTPException 400: If username or email already exists
    """
    user = await auth_service.register_user(user_data)
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Login and receive access and refresh tokens.

    Args:
        form_data: OAuth2 form with username and password
        auth_service: Injected AuthService instance

    Returns:
        Token object with access_token and refresh_token

    Raises:
        HTTPException 401: If credentials are invalid
        HTTPException 400: If user is inactive
    """
    token = await auth_service.login(form_data.username, form_data.password)
    return token


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Get a new access token using a refresh token.

    When your access token expires (after 15 minutes), use this endpoint
    to get a new access token without requiring the user to log in again.

    Args:
        refresh_request: RefreshTokenRequest with refresh_token
        auth_service: Injected AuthService instance

    Returns:
        New token pair (access_token and refresh_token)

    Raises:
        HTTPException 401: If refresh token is invalid or expired
    """
    token = await auth_service.refresh_access_token(refresh_request.refresh_token)
    return token


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get the current authenticated user's information.

    This endpoint requires a valid access token in the Authorization header.

    Args:
        current_user: Current authenticated user from token

    Returns:
        User information (without password)

    Raises:
        HTTPException 401: If token is invalid or expired
        HTTPException 400: If user is inactive
    """
    return current_user


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(current_user: User = Depends(get_current_active_user)):
    """
    Logout the current user.

    Note: Since JWT tokens are stateless, this endpoint primarily exists
    for client-side token deletion. The client should:
    1. Delete both access_token and refresh_token from storage
    2. Stop including the token in subsequent requests

    For a more secure logout with token blacklisting, you would need
    to implement a token blacklist in Redis or database.

    Args:
        current_user: Current authenticated user from token

    Returns:
        Success message
    """
    return {
        "message": "Successfully logged out. Please delete tokens from client storage."
    }
