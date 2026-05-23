from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import (
    ClientProfileUpdate, PartnerProfileUpdate,
    ClientProfileResponse, PartnerProfileResponse,
)

router = APIRouter()


# ==================== CLIENT PROFILE ====================

@router.get("/client/profile/", response_model=ClientProfileResponse)
async def get_client_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Client).where(Client.user_id == current_user.guid))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")

    return ClientProfileResponse(
        guid=current_user.guid,
        phone_number=current_user.phone_number,
        first_name=client.first_name,
        last_name=client.last_name,
    )


@router.patch("/client/profile/", response_model=ClientProfileResponse)
async def update_client_profile(
    data: ClientProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Client).where(Client.user_id == current_user.guid))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")

    if data.first_name is not None:
        client.first_name = data.first_name
    if data.last_name is not None:
        client.last_name = data.last_name

    await db.commit()
    await db.refresh(client)

    return ClientProfileResponse(
        guid=current_user.guid,
        phone_number=current_user.phone_number,
        first_name=client.first_name,
        last_name=client.last_name,
    )


# ==================== PARTNER PROFILE ====================

@router.get("/partner/profile/", response_model=PartnerProfileResponse)
async def get_partner_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Partner).where(Partner.user_id == current_user.guid))
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner profile not found")

    return PartnerProfileResponse(
        guid=current_user.guid,
        phone_number=current_user.phone_number,
        username=partner.username,
        first_name=partner.first_name,
        last_name=partner.last_name,
        avatar_url=partner.avatar_url,
        verification_status=partner.verification_status,
    )


@router.patch("/partner/profile/", response_model=PartnerProfileResponse)
async def update_partner_profile(
    data: PartnerProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Partner).where(Partner.user_id == current_user.guid))
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner profile not found")

    if data.first_name is not None:
        partner.first_name = data.first_name
    if data.last_name is not None:
        partner.last_name = data.last_name
    if data.username is not None:
        partner.username = data.username

    await db.commit()
    await db.refresh(partner)

    return PartnerProfileResponse(
        guid=current_user.guid,
        phone_number=current_user.phone_number,
        username=partner.username,
        first_name=partner.first_name,
        last_name=partner.last_name,
        avatar_url=partner.avatar_url,
        verification_status=partner.verification_status,
    )


@router.delete("/partner/profile/")
async def delete_partner_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.auth_service import AuthService
    await AuthService.delete_user(db, current_user.guid)
    await db.commit()
    return {"detail": "Partner account deleted"}
