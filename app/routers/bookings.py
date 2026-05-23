from typing import List, Optional
from datetime import datetime, timezone, timedelta, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.dependencies import get_current_user, get_current_client, get_current_partner
from app.models.user import User
from app.models.property import Property
from app.models.booking import Booking, CalendarDate
from app.schemas.booking import (
    BookingCreateRequest, BookingResponse, BookingCancelRequest,
    CalendarDateResponse, CalendarBlockRequest, CalendarHoldRequest,
    BookingPriceResponse, BookingPropertyResponse, BookingClientResponse,
)
from app.utils.enums import BookingStatus, CalendarStatus
import uuid
import random

router = APIRouter()


def generate_booking_number() -> str:
    return f"WEL-{random.randint(100000, 999999)}"


# ==================== CLIENT BOOKINGS ====================

@router.post("/client/", response_model=BookingResponse)
async def create_booking(
    data: BookingCreateRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    prop_result = await db.execute(select(Property).where(Property.guid == data.property_id))
    prop = prop_result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    check_query = select(CalendarDate).where(
        and_(
            CalendarDate.property_id == data.property_id,
            CalendarDate.date >= data.check_in,
            CalendarDate.date < data.check_out,
            CalendarDate.status != CalendarStatus.AVAILABLE.value,
        )
    )
    conflict = await db.execute(check_query)
    if conflict.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Selected dates are not available")

    nights = (data.check_out - data.check_in).days
    total = nights * 100000
    service_fee = int(total * 0.1)
    hold_amount = int(total * 0.2)

    booking = Booking(
        property_id=data.property_id,
        client_id=current_user.guid,
        check_in=datetime.combine(data.check_in, datetime.min.time()),
        check_out=datetime.combine(data.check_out, datetime.min.time()),
        adults=data.adults,
        children=data.children,
        babies=data.babies,
        booking_number=generate_booking_number(),
        status=BookingStatus.PENDING.value,
        subtotal=total,
        hold_amount=hold_amount,
        charge_amount=total - service_fee,
        service_fee=service_fee,
        service_fee_percentage=10,
    )
    db.add(booking)
    await db.flush()

    current_date = data.check_in
    while current_date < data.check_out:
        db.add(CalendarDate(
            property_id=data.property_id,
            date=datetime.combine(current_date, datetime.min.time()),
            status=CalendarStatus.HELD.value,
            booking_id=booking.guid,
        ))
        current_date += timedelta(days=1)

    await db.commit()
    await db.refresh(booking)

    return BookingResponse(
        guid=booking.guid,
        property=None,
        client=None,
        check_in=data.check_in,
        check_out=data.check_out,
        adults=booking.adults,
        children=booking.children,
        babies=booking.babies,
        booking_price=BookingPriceResponse(
            subtotal=total,
            hold_amount=hold_amount,
            charge_amount=total - service_fee,
            service_fee=service_fee,
            service_fee_percentage=10,
        ),
        booking_number=booking.booking_number,
        status=booking.status,
        cancellation_reason=None,
        confirmed_at=None,
        cancelled_at=None,
        completed_at=None,
    )


@router.get("/client/", response_model=List[BookingResponse])
async def get_client_bookings(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    query = select(Booking).where(Booking.client_id == current_user.guid).options(
        selectinload(Booking.property),
    )
    if status:
        query = query.where(Booking.status == status)
    query = query.order_by(Booking.created_at.desc())

    result = await db.execute(query)
    bookings = result.scalars().all()

    return [
        BookingResponse(
            guid=b.guid,
            property=BookingPropertyResponse(guid=b.property.guid, title=b.property.title, property_images=None) if b.property else None,
            client=None,
            check_in=b.check_in.date() if b.check_in else None,
            check_out=b.check_out.date() if b.check_out else None,
            adults=b.adults,
            children=b.children,
            babies=b.babies,
            booking_price=BookingPriceResponse(
                subtotal=b.subtotal,
                hold_amount=b.hold_amount,
                charge_amount=b.charge_amount,
                service_fee=b.service_fee,
                service_fee_percentage=b.service_fee_percentage,
            ),
            booking_number=b.booking_number,
            status=b.status,
            cancellation_reason=b.cancellation_reason,
            confirmed_at=b.confirmed_at,
            cancelled_at=b.cancelled_at,
            completed_at=b.completed_at,
        )
        for b in bookings
    ]


@router.get("/client/{booking_id}/", response_model=BookingResponse)
async def get_client_booking_detail(
    booking_id: str,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Booking).where(
            and_(Booking.guid == booking_id, Booking.client_id == current_user.guid)
        ).options(selectinload(Booking.property))
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    return BookingResponse(
        guid=booking.guid,
        property=BookingPropertyResponse(guid=booking.property.guid, title=booking.property.title, property_images=None) if booking.property else None,
        client=None,
        check_in=booking.check_in.date() if booking.check_in else None,
        check_out=booking.check_out.date() if booking.check_out else None,
        adults=booking.adults,
        children=booking.children,
        babies=booking.babies,
        booking_price=BookingPriceResponse(
            subtotal=booking.subtotal,
            hold_amount=booking.hold_amount,
            charge_amount=booking.charge_amount,
            service_fee=booking.service_fee,
            service_fee_percentage=booking.service_fee_percentage,
        ),
        booking_number=booking.booking_number,
        status=booking.status,
        cancellation_reason=booking.cancellation_reason,
        confirmed_at=booking.confirmed_at,
        cancelled_at=booking.cancelled_at,
        completed_at=booking.completed_at,
    )


@router.post("/client/{booking_id}/cancel/")
async def cancel_client_booking(
    booking_id: str,
    data: BookingCancelRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Booking).where(
            and_(Booking.guid == booking_id, Booking.client_id == current_user.guid)
        )
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status not in [BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]:
        raise HTTPException(status_code=400, detail="Cannot cancel this booking")

    booking.status = BookingStatus.CANCELLED.value
    booking.cancellation_reason = data.reason
    booking.cancelled_at = datetime.now(timezone.utc)

    await db.execute(
        CalendarDate.__table__.delete().where(
            and_(
                CalendarDate.booking_id == booking_id,
                CalendarDate.property_id == booking.property_id,
            )
        )
    )

    await db.commit()
    return {"detail": "Booking cancelled"}


@router.get("/client/history/", response_model=List[BookingResponse])
async def get_client_booking_history(
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    query = select(Booking).where(
        and_(
            Booking.client_id == current_user.guid,
            Booking.status.in_([BookingStatus.COMPLETED.value, BookingStatus.CANCELLED.value, BookingStatus.NO_SHOW.value]),
        )
    ).options(selectinload(Booking.property)).order_by(Booking.created_at.desc())

    result = await db.execute(query)
    bookings = result.scalars().all()

    return [
        BookingResponse(
            guid=b.guid,
            property=BookingPropertyResponse(guid=b.property.guid, title=b.property.title, property_images=None) if b.property else None,
            client=None,
            check_in=b.check_in.date() if b.check_in else None,
            check_out=b.check_out.date() if b.check_out else None,
            adults=b.adults,
            children=b.children,
            babies=b.babies,
            booking_price=BookingPriceResponse(
                subtotal=b.subtotal,
                hold_amount=b.hold_amount,
                charge_amount=b.charge_amount,
                service_fee=b.service_fee,
                service_fee_percentage=b.service_fee_percentage,
            ),
            booking_number=b.booking_number,
            status=b.status,
            cancellation_reason=b.cancellation_reason,
            confirmed_at=b.confirmed_at,
            cancelled_at=b.cancelled_at,
            completed_at=b.completed_at,
        )
        for b in bookings
    ]


# ==================== PARTNER BOOKINGS ====================

@router.get("/partner/", response_model=List[BookingResponse])
async def get_partner_bookings(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    prop_result = await db.execute(select(Property.guid).where(Property.partner_id == current_user.guid))
    property_ids = [r[0] for r in prop_result.all()]

    if not property_ids:
        return []

    query = select(Booking).where(Booking.property_id.in_(property_ids)).options(
        selectinload(Booking.property),
    )
    if status:
        query = query.where(Booking.status == status)

    query = query.order_by(Booking.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    bookings = result.scalars().all()

    return [
        BookingResponse(
            guid=b.guid,
            property=BookingPropertyResponse(guid=b.property.guid, title=b.property.title, property_images=None) if b.property else None,
            client=None,
            check_in=b.check_in.date() if b.check_in else None,
            check_out=b.check_out.date() if b.check_out else None,
            adults=b.adults,
            children=b.children,
            babies=b.babies,
            booking_price=BookingPriceResponse(
                subtotal=b.subtotal,
                hold_amount=b.hold_amount,
                charge_amount=b.charge_amount,
                service_fee=b.service_fee,
                service_fee_percentage=b.service_fee_percentage,
            ),
            booking_number=b.booking_number,
            status=b.status,
            cancellation_reason=b.cancellation_reason,
            confirmed_at=b.confirmed_at,
            cancelled_at=b.cancelled_at,
            completed_at=b.completed_at,
        )
        for b in bookings
    ]


@router.post("/partner/{booking_id}/accept/")
async def accept_booking(
    booking_id: str,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Booking).where(Booking.guid == booking_id).options(selectinload(Booking.property))
    )
    booking = result.scalar_one_or_none()
    if not booking or booking.property.partner_id != current_user.guid:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != BookingStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Booking is not pending")

    booking.status = BookingStatus.CONFIRMED.value
    booking.confirmed_at = datetime.now(timezone.utc)

    await db.execute(
        CalendarDate.__table__.update().where(
            and_(
                CalendarDate.booking_id == booking_id,
                CalendarDate.property_id == booking.property_id,
            )
        ).values(status=CalendarStatus.BOOKED.value)
    )

    await db.commit()
    return {"detail": "Booking accepted"}


@router.post("/partner/{booking_id}/cancel/")
async def partner_cancel_booking(
    booking_id: str,
    data: BookingCancelRequest,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Booking).where(Booking.guid == booking_id).options(selectinload(Booking.property))
    )
    booking = result.scalar_one_or_none()
    if not booking or booking.property.partner_id != current_user.guid:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = BookingStatus.CANCELLED.value
    booking.cancellation_reason = data.reason
    booking.cancelled_at = datetime.now(timezone.utc)

    await db.execute(
        CalendarDate.__table__.delete().where(
            and_(
                CalendarDate.booking_id == booking_id,
                CalendarDate.property_id == booking.property_id,
            )
        )
    )

    await db.commit()
    return {"detail": "Booking cancelled"}


@router.post("/partner/{booking_id}/complete/")
async def complete_booking(
    booking_id: str,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Booking).where(Booking.guid == booking_id).options(selectinload(Booking.property))
    )
    booking = result.scalar_one_or_none()
    if not booking or booking.property.partner_id != current_user.guid:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != BookingStatus.CONFIRMED.value:
        raise HTTPException(status_code=400, detail="Booking must be confirmed first")

    booking.status = BookingStatus.COMPLETED.value
    booking.completed_at = datetime.now(timezone.utc)

    await db.commit()
    return {"detail": "Booking completed"}


@router.post("/partner/{booking_id}/no_show/")
async def no_show_booking(
    booking_id: str,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Booking).where(Booking.guid == booking_id).options(selectinload(Booking.property))
    )
    booking = result.scalar_one_or_none()
    if not booking or booking.property.partner_id != current_user.guid:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != BookingStatus.CONFIRMED.value:
        raise HTTPException(status_code=400, detail="Booking must be confirmed first")

    booking.status = BookingStatus.NO_SHOW.value
    booking.completed_at = datetime.now(timezone.utc)

    await db.commit()
    return {"detail": "Marked as no-show"}


# ==================== CALENDAR ====================

@router.get("/properties/{property_id}/calendar/")
async def get_calendar(
    property_id: str,
    from_date: date,
    to_date: date,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    prop_result = await db.execute(
        select(Property).where(
            and_(Property.guid == property_id, Property.partner_id == current_user.guid)
        )
    )
    if not prop_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Property not found")

    result = await db.execute(
        select(CalendarDate).where(
            and_(
                CalendarDate.property_id == property_id,
                CalendarDate.date >= datetime.combine(from_date, datetime.min.time()),
                CalendarDate.date <= datetime.combine(to_date, datetime.min.time()),
            )
        ).order_by(CalendarDate.date)
    )
    dates = result.scalars().all()

    return [
        CalendarDateResponse(
            date=d.date.date() if d.date else None,
            status=d.status,
        )
        for d in dates
    ]


@router.post("/properties/{property_id}/calendar/block/")
async def block_calendar_dates(
    property_id: str,
    data: CalendarBlockRequest,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    prop_result = await db.execute(
        select(Property).where(
            and_(Property.guid == property_id, Property.partner_id == current_user.guid)
        )
    )
    if not prop_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Property not found")

    for d in data.dates:
        existing = await db.execute(
            select(CalendarDate).where(
                and_(
                    CalendarDate.property_id == property_id,
                    CalendarDate.date == datetime.combine(d, datetime.min.time()),
                    CalendarDate.status == CalendarStatus.BOOKED.value,
                )
            )
        )
        if existing.scalar_one_or_none():
            continue

        existing_free = await db.execute(
            select(CalendarDate).where(
                and_(
                    CalendarDate.property_id == property_id,
                    CalendarDate.date == datetime.combine(d, datetime.min.time()),
                )
            )
        )
        cal = existing_free.scalar_one_or_none()
        if cal:
            cal.status = CalendarStatus.BLOCKED.value
        else:
            db.add(CalendarDate(property_id=property_id, date=datetime.combine(d, datetime.min.time()), status=CalendarStatus.BLOCKED.value))

    await db.commit()
    return {"detail": "Dates blocked"}


@router.post("/properties/{property_id}/calendar/hold/")
async def hold_calendar_dates(
    property_id: str,
    data: CalendarHoldRequest,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    prop_result = await db.execute(
        select(Property).where(
            and_(Property.guid == property_id, Property.partner_id == current_user.guid)
        )
    )
    if not prop_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Property not found")

    for d in data.dates:
        existing = await db.execute(
            select(CalendarDate).where(
                and_(
                    CalendarDate.property_id == property_id,
                    CalendarDate.date == datetime.combine(d, datetime.min.time()),
                    CalendarDate.status == CalendarStatus.BOOKED.value,
                )
            )
        )
        if existing.scalar_one_or_none():
            continue

        existing_free = await db.execute(
            select(CalendarDate).where(
                and_(
                    CalendarDate.property_id == property_id,
                    CalendarDate.date == datetime.combine(d, datetime.min.time()),
                )
            )
        )
        cal = existing_free.scalar_one_or_none()
        if cal:
            cal.status = CalendarStatus.HELD.value
        else:
            db.add(CalendarDate(property_id=property_id, date=datetime.combine(d, datetime.min.time()), status=CalendarStatus.HELD.value))

    await db.commit()
    return {"detail": "Dates held"}


@router.post("/properties/{property_id}/calendar/unblock/")
async def unblock_calendar_dates(
    property_id: str,
    data: CalendarBlockRequest,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        CalendarDate.__table__.delete().where(
            and_(
                CalendarDate.property_id == property_id,
                CalendarDate.date.in_([datetime.combine(d, datetime.min.time()) for d in data.dates]),
                CalendarDate.status == CalendarStatus.BLOCKED.value,
            )
        )
    )
    await db.commit()
    return {"detail": "Dates unblocked"}


@router.post("/properties/{property_id}/calendar/unhold/")
async def unhold_calendar_dates(
    property_id: str,
    data: CalendarHoldRequest,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        CalendarDate.__table__.delete().where(
            and_(
                CalendarDate.property_id == property_id,
                CalendarDate.date.in_([datetime.combine(d, datetime.min.time()) for d in data.dates]),
                CalendarDate.status == CalendarStatus.HELD.value,
            )
        )
    )
    await db.commit()
    return {"detail": "Dates unheld"}
