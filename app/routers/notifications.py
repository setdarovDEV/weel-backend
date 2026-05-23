from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import get_db
from app.dependencies import get_current_user, get_current_partner
from app.models.user import User
from app.models.notification import Notification
from app.models.user import UserDevice
from app.schemas.notification import DeviceTokenRequest, NotificationResponse, NotificationReadRequest

router = APIRouter()


@router.post("/device/")
async def register_device(
    data: DeviceTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check if device already exists
    result = await db.execute(
        select(UserDevice).where(
            and_(UserDevice.user_id == current_user.guid, UserDevice.fcm_token == data.fcm_token)
        )
    )
    if not result.scalar_one_or_none():
        db.add(UserDevice(user_id=current_user.guid, fcm_token=data.fcm_token, device_type=data.device_type))
        await db.commit()
    return {"detail": "Device registered"}


@router.get("/partner/", response_model=List[NotificationResponse])
async def get_partner_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(Notification.user_id == current_user.guid)
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * limit).limit(limit)
    )
    notifications = result.scalars().all()
    return [
        NotificationResponse(
            guid=n.guid,
            title=n.title_ru or n.title_uz,
            body=n.body_ru or n.body_uz,
            notification_type=n.notification_type,
            is_read=n.is_read,
            created_at=n.created_at,
        )
        for n in notifications
    ]


@router.post("/partner/read/")
async def mark_partner_notifications_read(
    data: NotificationReadRequest,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    if data.notification_ids:
        await db.execute(
            Notification.__table__.update().where(
                and_(
                    Notification.user_id == current_user.guid,
                    Notification.guid.in_(data.notification_ids),
                )
            ).values(is_read=True)
        )
    await db.commit()
    return {"detail": "Marked as read"}


@router.post("/partner/read-all/")
async def mark_all_partner_notifications_read(
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        Notification.__table__.update().where(
            Notification.user_id == current_user.guid
        ).values(is_read=True)
    )
    await db.commit()
    return {"detail": "All marked as read"}
