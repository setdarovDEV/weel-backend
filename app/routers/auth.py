from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ClientRegisterRequest, ClientLoginRequest,
    PartnerRegisterRequest, PartnerLoginRequest,
    OtpVerifyRequest, OtpResendRequest,
    TokenRefreshRequest, LogoutRequest, DeleteAccountRequest,
    OtpResponse, ClientVerifyResponse, PartnerVerifyResponse,
    TokenResponse, ClientInfo, PartnerInfo,
)
from app.services.auth_service import AuthService, OTPService
from app.utils.security import decode_token
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== CLIENT AUTH ====================

@router.post("/client/register/", response_model=OtpResponse)
async def client_register(data: ClientRegisterRequest, db: AsyncSession = Depends(get_db)):
    # Create user if not exists (store first/last name somewhere or just verify OTP first)
    user = await AuthService.get_or_create_user(db, data.phone_number)
    code = OTPService.generate_code()
    await OTPService.store_otp(data.phone_number, "client_register", code)
    # TODO: Send SMS via Celery
    logger.info(f"[DEV OTP] client_register {data.phone_number} -> {code}")
    return OtpResponse(phone_number=data.phone_number, expires_in=120, code=code if settings.environment == "development" else None)


@router.post("/client/login/", response_model=OtpResponse)
async def client_login(data: ClientLoginRequest, db: AsyncSession = Depends(get_db)):
    user = await AuthService.get_or_create_user(db, data.phone_number)
    code = OTPService.generate_code()
    await OTPService.store_otp(data.phone_number, "client_login", code)
    # TODO: Send SMS via Celery
    logger.info(f"[DEV OTP] client_login {data.phone_number} -> {code}")
    return OtpResponse(phone_number=data.phone_number, expires_in=120, code=code if settings.environment == "development" else None)


@router.post("/client/register/verify/", response_model=ClientVerifyResponse)
async def client_register_verify(data: OtpVerifyRequest, db: AsyncSession = Depends(get_db)):
    if not await OTPService.verify_otp(data.phone_number, "client_register", data.code):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    # We need first_name/last_name from the original request - for now simple approach
    # In real implementation, store registration data temporarily or accept in verify request
    user = await AuthService.get_or_create_user(db, data.phone_number)
    await AuthService.assign_role(db, user.guid, UserRole.CLIENT)
    client = await AuthService.create_client(db, user.guid, "", "")

    access, refresh = await AuthService.generate_token_pair(user.guid)
    await AuthService.store_refresh_token(db, refresh, user.guid)
    await db.commit()

    return ClientVerifyResponse(
        access=access,
        refresh=refresh,
        client=ClientInfo(
            guid=user.guid,
            phone_number=user.phone_number,
            first_name=client.first_name,
            last_name=client.last_name,
        ),
    )


@router.post("/client/login/verify/", response_model=ClientVerifyResponse)
async def client_login_verify(data: OtpVerifyRequest, db: AsyncSession = Depends(get_db)):
    if not await OTPService.verify_otp(data.phone_number, "client_login", data.code):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    user = await AuthService.get_or_create_user(db, data.phone_number)
    await AuthService.assign_role(db, user.guid, UserRole.CLIENT)

    result = await db.execute(select(Client).where(Client.user_id == user.guid))
    client = result.scalar_one_or_none()
    if not client:
        client = await AuthService.create_client(db, user.guid, "", "")

    access, refresh = await AuthService.generate_token_pair(user.guid)
    await AuthService.store_refresh_token(db, refresh, user.guid)
    await db.commit()

    return ClientVerifyResponse(
        access=access,
        refresh=refresh,
        client=ClientInfo(
            guid=user.guid,
            phone_number=user.phone_number,
            first_name=client.first_name,
            last_name=client.last_name,
        ),
    )


@router.post("/client/register/resend/", response_model=OtpResponse)
async def client_register_resend(data: OtpResendRequest):
    code = OTPService.generate_code()
    await OTPService.store_otp(data.phone_number, "client_register", code)
    logger.info(f"[DEV OTP] client_register_resend {data.phone_number} -> {code}")
    return OtpResponse(phone_number=data.phone_number, expires_in=120, code=code if settings.environment == "development" else None)


@router.post("/client/login/resend/", response_model=OtpResponse)
async def client_login_resend(data: OtpResendRequest):
    code = OTPService.generate_code()
    await OTPService.store_otp(data.phone_number, "client_login", code)
    logger.info(f"[DEV OTP] client_login_resend {data.phone_number} -> {code}")
    return OtpResponse(phone_number=data.phone_number, expires_in=120, code=code if settings.environment == "development" else None)


# ==================== PARTNER AUTH ====================

@router.post("/partner/register/", response_model=OtpResponse)
async def partner_register(data: PartnerRegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await AuthService.get_or_create_user(db, data.phone_number)
    code = OTPService.generate_code()
    await OTPService.store_otp(data.phone_number, "partner_register", code)
    logger.info(f"[DEV OTP] partner_register {data.phone_number} -> {code}")
    return OtpResponse(phone_number=data.phone_number, expires_in=120, code=code if settings.environment == "development" else None)


@router.post("/partner/login/", response_model=OtpResponse)
async def partner_login(data: PartnerLoginRequest, db: AsyncSession = Depends(get_db)):
    user = await AuthService.get_or_create_user(db, data.phone_number)
    code = OTPService.generate_code()
    await OTPService.store_otp(data.phone_number, "partner_login", code)
    logger.info(f"[DEV OTP] partner_login {data.phone_number} -> {code}")
    return OtpResponse(phone_number=data.phone_number, expires_in=120, code=code if settings.environment == "development" else None)


@router.post("/partner/register/verify/", response_model=PartnerVerifyResponse)
async def partner_register_verify(data: OtpVerifyRequest, db: AsyncSession = Depends(get_db)):
    if not await OTPService.verify_otp(data.phone_number, "partner_register", data.code):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    user = await AuthService.get_or_create_user(db, data.phone_number)
    await AuthService.assign_role(db, user.guid, UserRole.PARTNER)
    partner = await AuthService.create_partner(db, user.guid, "", "", "")

    access, refresh = await AuthService.generate_token_pair(user.guid)
    await AuthService.store_refresh_token(db, refresh, user.guid)
    await db.commit()

    return PartnerVerifyResponse(
        access=access,
        refresh=refresh,
        partner=PartnerInfo(
            guid=user.guid,
            phone_number=user.phone_number,
            username=partner.username,
            first_name=partner.first_name,
            last_name=partner.last_name,
        ),
    )


@router.post("/partner/login/verify/", response_model=PartnerVerifyResponse)
async def partner_login_verify(data: OtpVerifyRequest, db: AsyncSession = Depends(get_db)):
    if not await OTPService.verify_otp(data.phone_number, "partner_login", data.code):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    user = await AuthService.get_or_create_user(db, data.phone_number)
    await AuthService.assign_role(db, user.guid, UserRole.PARTNER)

    result = await db.execute(select(Partner).where(Partner.user_id == user.guid))
    partner = result.scalar_one_or_none()
    if not partner:
        partner = await AuthService.create_partner(db, user.guid, "", "", "")

    access, refresh = await AuthService.generate_token_pair(user.guid)
    await AuthService.store_refresh_token(db, refresh, user.guid)
    await db.commit()

    return PartnerVerifyResponse(
        access=access,
        refresh=refresh,
        partner=PartnerInfo(
            guid=user.guid,
            phone_number=user.phone_number,
            username=partner.username,
            first_name=partner.first_name,
            last_name=partner.last_name,
        ),
    )


# ==================== SHARED ====================

@router.post("/refresh/", response_model=TokenResponse)
async def refresh_token(data: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    if not data.refresh or not await AuthService.is_refresh_token_valid(db, data.refresh):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    payload = decode_token(data.refresh)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    await AuthService.revoke_refresh_token(db, data.refresh)
    access, new_refresh = await AuthService.generate_token_pair(user_id)
    await AuthService.store_refresh_token(db, new_refresh, user_id)
    await db.commit()

    return TokenResponse(access=access, refresh=new_refresh)


@router.post("/client/logout/")
async def client_logout(data: LogoutRequest, db: AsyncSession = Depends(get_db)):
    await AuthService.revoke_refresh_token(db, data.refresh)
    await db.commit()
    return {"detail": "Successfully logged out"}


@router.post("/partner/logout/")
async def partner_logout(data: LogoutRequest, db: AsyncSession = Depends(get_db)):
    await AuthService.revoke_refresh_token(db, data.refresh)
    await db.commit()
    return {"detail": "Successfully logged out"}


@router.delete("/account/")
async def delete_account(data: DeleteAccountRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    await AuthService.revoke_refresh_token(db, data.refresh)
    await AuthService.delete_user(db, user_id)
    await db.commit()
    return {"detail": "Account deleted"}
