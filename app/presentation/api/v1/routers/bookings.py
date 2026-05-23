from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.booking_service import BookingApplicationService
from app.infrastructure.database.models.user import User
from app.presentation.api.v1.deps import get_current_client, get_db
from app.presentation.api.schemas.booking import (
    BookingCancelRequest,
    BookingCreateRequest,
    BookingRead,
)

router = APIRouter()


def _build_booking_read(b) -> BookingRead:
    """Assemble BookingRead from merged 3NF/4NF booking."""
    client = b.client
    user = client.user if client else None
    prop = b.property

    return BookingRead(
        guid=str(b.guid),
        property=BookingRead.__fields__["property"].type_(
            guid=str(prop.guid), title=prop.title, city=prop.city
        ) if prop else None,
        client=BookingRead.__fields__["client"].type_(
            guid=str(user.guid) if user else "",
            phone_number=user.phone_number if user else "",
            first_name=client.first_name if client else None,
            last_name=client.last_name if client else None,
        ) if client else None,
        check_in=b.check_in,
        check_out=b.check_out,
        adults=b.adults,
        children=b.children,
        babies=b.babies,
        booking_number=b.booking_number,
        status=b.status,
        cancellation_reason=b.cancellation_reason,
        subtotal=b.subtotal,
        hold_amount=b.hold_amount,
        charge_amount=b.charge_amount,
        service_fee=b.service_fee,
        created_at=b.created_at,
    )


@router.post("/client/", response_model=BookingRead)
async def create_booking(
    data: BookingCreateRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    service = BookingApplicationService(db)
    booking = await service.create_booking(
        client_id=str(current_user.guid),
        property_id=data.property_id,
        check_in=data.check_in,
        check_out=data.check_out,
        adults=data.adults,
        children=data.children,
        babies=data.babies,
    )
    return _build_booking_read(booking)


@router.get("/client/", response_model=List[BookingRead])
async def list_client_bookings(
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    service = BookingApplicationService(db)
    bookings = await service.list_client_bookings(str(current_user.guid))
    return [_build_booking_read(b) for b in bookings]


@router.post("/client/{booking_id}/cancel/", response_model=BookingRead)
async def cancel_booking(
    booking_id: str,
    data: BookingCancelRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    service = BookingApplicationService(db)
    booking = await service.cancel_booking(
        booking_id=booking_id,
        client_id=str(current_user.guid),
        reason=data.reason,
    )
    return _build_booking_read(booking)
