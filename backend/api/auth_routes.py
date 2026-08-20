"""
Authentication & Session Token API Routes
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from backend.core.security import create_access_token

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class TokenRequest(BaseModel):
    user_id: str
    display_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    display_name: str


@router.post("/token", response_model=TokenResponse)
async def generate_token(req: TokenRequest):
    if not req.user_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")
    
    token = create_access_token(user_id=req.user_id, display_name=req.display_name)
    return TokenResponse(
        access_token=token,
        user_id=req.user_id,
        display_name=req.display_name,
    )
