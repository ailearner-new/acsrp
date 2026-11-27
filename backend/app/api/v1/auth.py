"""Authentication routes."""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from backend.app.core.config import settings
from backend.app.core.middleware import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> dict:
    """Get access token (demo mode)."""
    # In a real app, validate user credentials against DB
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Demo mode is disabled",
        )

    # Demo user
    user = {
        "sub": form_data.username,
        "role": "TENANT_ADMIN" if "admin" in form_data.username else "TIER1_AGENT",
    }

    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        subject=user, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def get_me(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get current user profile."""
    return current_user
