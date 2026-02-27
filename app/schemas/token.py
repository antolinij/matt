"""Token Pydantic schemas for authentication"""
from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for decoded token payload"""
    user_id: Optional[int] = None
    username: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str
