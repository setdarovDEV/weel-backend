"""Unified Authentication Router v2 (optimized for all user roles).

Endpoints:
- POST /otp/send/      - Send OTP (client/partner register/login)
- POST /otp/verify/     - Verify OTP and get tokens
- POST /admin/login/    - Admin username/password login
- POST /refresh/        - Refresh token pair
- POST /logout/         - Revoke refresh token
- GET /me/              - Get current user info
- DELETE /account/      - Soft delete account
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.auth_service import AuthApplicationService
from app.infrastructure.database.models.user import User
from app.presentation.api.v1.deps import get_auth_service, get_current_active_user
from app.presentation.api.schemas.auth_v2 import (
    AdminLoginRequest,
    DeleteAccountRequest,
    LogoutRequest,
    OtpSendRequest,
    OtpVerifyRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserInfoResponse,
    VerifyResponse,
)

router = APIRouter()


@router.post("/otp/send/")
async def send_otp(
    data: OtpSendRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    """Send OTP for register or login (client/partner)."""
    return await service.send_otp(
        phone=data.phone,
        purpose=data.purpose,
        role=data.role,
    )


@router.post("/otp/verify/", response_model=VerifyResponse)
async def verify_otp(
    data: OtpVerifyRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    """Verify OTP and return access/refresh tokens + user info."""
    return await service.verify_otp(
        phone=data.phone,
        code=data.code,
        purpose=data.purpose,
        role=data.role,
        first_name=data.first_name or "",
        last_name=data.last_name or "",
        username=data.username or "",
    )


@router.post("/admin/login/", response_model=TokenResponse)
async def admin_login(
    data: AdminLoginRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    """Admin login with username/email and password."""
    return await service.admin_login(
        email=data.email,
        password=data.password,
    )


@router.post("/refresh/", response_model=TokenResponse)
async def refresh_token(
    data: TokenRefreshRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    """Refresh access token using refresh token."""
    tokens = await service.refresh_tokens(data.refresh)
    return TokenResponse(access=tokens.access_token, refresh=tokens.refresh_token)


@router.post("/logout/")
async def logout(
    data: LogoutRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    """Logout and revoke refresh token."""
    await service.logout(data.refresh)
    return {"detail": "Successfully logged out"}


@router.get("/me/", response_model=UserInfoResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user),
):
    """Get current authenticated user info."""
    return UserInfoResponse(
        guid=str(current_user.guid),
        phone_number=current_user.phone_number,
        is_active=current_user.is_active,
        roles=[r.role for r in current_user.roles],
    )


@router.delete("/account/")
async def delete_account(
    data: DeleteAccountRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    """Soft delete current account."""
    await service.delete_account(data.refresh)
    return {"detail": "Account deleted"}
