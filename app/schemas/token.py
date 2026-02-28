"""Token Pydantic schemas for authentication"""

from typing import Optional

from pydantic import BaseModel


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
