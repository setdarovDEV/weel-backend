from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainException
from app.core.logging_config import get_logger
from app.presentation.api.v1.deps import get_auth_service, get_db
from app.presentation.api.schemas.auth import (
    ClientInfo,
    ClientRegisterRequest,
    ClientVerifyResponse,
    DeleteAccountRequest,
    LogoutRequest,
    OtpResendRequest,
    OtpResponse,
    OtpVerifyRequest,
    PartnerInfo,
    PartnerRegisterRequest,
    PartnerVerifyResponse,
    TokenRefreshRequest,
    TokenResponse,
)
from app.application.services.auth_service import AuthApplicationService

logger = get_logger(__name__)
router = APIRouter()


# ==================== CLIENT AUTH ====================

@router.post("/client/register/", response_model=OtpResponse)
async def client_register(
    data: ClientRegisterRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    return await service.send_otp(data.phone_number, "register", "client")


@router.post("/client/login/", response_model=OtpResponse)
async def client_login(
    data: OtpResendRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    return await service.send_otp(data.phone_number, "login", "client")


@router.post("/client/register/verify/", response_model=ClientVerifyResponse)
async def client_register_verify(
    data: OtpVerifyRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    result = await service.verify_otp(
        data.phone_number, data.code, "register", "client",
        first_name=data.first_name, last_name=data.last_name
    )
    return ClientVerifyResponse(
        access=result.access,
        refresh=result.refresh,
        client=ClientInfo(
            guid=result.user.guid,
            phone_number=result.user.phone_number,
            first_name=result.user.first_name,
            last_name=result.user.last_name,
        ),
    )


@router.post("/client/login/verify/", response_model=ClientVerifyResponse)
async def client_login_verify(
    data: OtpVerifyRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    result = await service.verify_otp(
        data.phone_number, data.code, "login", "client",
        first_name=data.first_name, last_name=data.last_name
    )
    return ClientVerifyResponse(
        access=result.access,
        refresh=result.refresh,
        client=ClientInfo(
            guid=result.user.guid,
            phone_number=result.user.phone_number,
            first_name=result.user.first_name,
            last_name=result.user.last_name,
        ),
    )


@router.post("/client/register/resend/", response_model=OtpResponse)
async def client_register_resend(
    data: OtpResendRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    return await service.send_otp(data.phone_number, "register", "client")


@router.post("/client/login/resend/", response_model=OtpResponse)
async def client_login_resend(
    data: OtpResendRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    return await service.send_otp(data.phone_number, "login", "client")


# ==================== PARTNER AUTH ====================

@router.post("/partner/register/", response_model=OtpResponse)
async def partner_register(
    data: PartnerRegisterRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    return await service.send_otp(data.phone_number, "register", "partner")


@router.post("/partner/login/", response_model=OtpResponse)
async def partner_login(
    data: OtpResendRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    return await service.send_otp(data.phone_number, "login", "partner")


@router.post("/partner/register/verify/", response_model=PartnerVerifyResponse)
async def partner_register_verify(
    data: PartnerRegisterRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    result = await service.verify_otp(
        data.phone_number, "", "register", "partner",
        first_name=data.first_name, last_name=data.last_name, username=data.username
    )
    return PartnerVerifyResponse(
        access=result.access,
        refresh=result.refresh,
        partner=PartnerInfo(
            guid=result.user.guid,
            phone_number=result.user.phone_number,
            username=result.user.username,
            first_name=result.user.first_name,
            last_name=result.user.last_name,
        ),
    )


@router.post("/partner/login/verify/", response_model=PartnerVerifyResponse)
async def partner_login_verify(
    data: OtpVerifyRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    result = await service.verify_otp(
        data.phone_number, data.code, "login", "partner",
        first_name=data.first_name, last_name=data.last_name, username=data.username
    )
    return PartnerVerifyResponse(
        access=result.access,
        refresh=result.refresh,
        partner=PartnerInfo(
            guid=result.user.guid,
            phone_number=result.user.phone_number,
            username=result.user.username,
            first_name=result.user.first_name,
            last_name=result.user.last_name,
        ),
    )


@router.post("/partner/register/resend/", response_model=OtpResponse)
async def partner_register_resend(
    data: OtpResendRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    return await service.send_otp(data.phone_number, "register", "partner")


@router.post("/partner/login/resend/", response_model=OtpResponse)
async def partner_login_resend(
    data: OtpResendRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    return await service.send_otp(data.phone_number, "login", "partner")


# ==================== SHARED ====================

@router.post("/refresh/", response_model=TokenResponse)
async def refresh_token(
    data: TokenRefreshRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    tokens = await service.refresh_tokens(data.refresh)
    return TokenResponse(access=tokens.access, refresh=tokens.refresh)


@router.post("/client/logout/")
async def client_logout(
    data: LogoutRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    await service.logout(data.refresh)
    return {"detail": "Successfully logged out"}


@router.post("/partner/logout/")
async def partner_logout(
    data: LogoutRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    await service.logout(data.refresh)
    return {"detail": "Successfully logged out"}


@router.delete("/account/")
async def delete_account(
    data: DeleteAccountRequest,
    service: AuthApplicationService = Depends(get_auth_service),
):
    await service.delete_account(data.refresh)
    return {"detail": "Account deleted"}
