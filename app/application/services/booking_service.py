import random
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import BookingStatus
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.logging_config import get_logger
from app.infrastructure.database.models.booking import (
    Booking,
    BookingStatusLog,
    CalendarDate,
)
from app.infrastructure.database.models.property import Property
from app.infrastructure.database.models.user import ClientProfile

logger = get_logger(__name__)


def generate_booking_number() -> str:
    return f"WEL-{random.randint(100000, 999999)}"


class BookingApplicationService:
    """Application service for Booking aggregate use cases (practical 3NF/4NF)."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_booking(
        self,
        client_id: str,
        property_id: str,
        check_in: datetime,
        check_out: datetime,
        adults: int = 1,
        children: int = 0,
        babies: int = 0,
    ) -> Booking:
        if check_in >= check_out:
            raise ValidationException("check_in must be before check_out")

        prop_result = await self._db.execute(select(Property).where(Property.guid == property_id))
        prop: Optional[Property] = prop_result.scalar_one_or_none()
        if not prop:
            raise NotFoundException("Property not found")

        # Check availability
        conflict = await self._db.execute(
            select(CalendarDate).where(
                and_(
                    CalendarDate.property_id == property_id,
                    CalendarDate.date >= check_in,
                    CalendarDate.date < check_out,
                    CalendarDate.status != "available",
                )
            )
        )
        if conflict.scalar_one_or_none():
            raise ConflictException("Selected dates are not available")

        nights = (check_out - check_in).days
        total = nights * 100000
        service_fee = int(total * 0.1)
        hold_amount = int(total * 0.2)

        # Core booking with merged financial facts
        booking = Booking(
            property_id=property_id,
            client_id=client_id,
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
            babies=babies,
            booking_number=generate_booking_number(),
            status=BookingStatus.PENDING.value,
            # Financials merged (1:1 facts)
            subtotal=total,
            hold_amount=hold_amount,
            charge_amount=total,
            service_fee=service_fee,
            service_fee_percentage=10,
        )
        self._db.add(booking)
        await self._db.flush()

        # Audit trail
        self._db.add(
            BookingStatusLog(
                booking_id=booking.guid,
                previous_status=None,
                new_status=BookingStatus.PENDING.value,
            )
        )

        await self._db.flush()
        logger.info(f"Booking created {booking.booking_number} for property {property_id}")
        return booking

    async def get_booking(self, booking_id: str) -> Booking:
        result = await self._db.execute(
            select(Booking)
            .where(Booking.guid == booking_id)
            .options(
                selectinload(Booking.property).selectinload(Property.location_ref),
                selectinload(Booking.client).selectinload(ClientProfile.user),
            )
        )
        booking: Optional[Booking] = result.scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking not found")
        return booking

    async def list_client_bookings(self, client_id: str) -> List[Booking]:
        result = await self._db.execute(
            select(Booking)
            .where(Booking.client_id == client_id)
            .order_by(Booking.created_at.desc())
        )
        return list(result.scalars().all())

    async def cancel_booking(self, booking_id: str, client_id: str, reason: Optional[str] = None) -> Booking:
        booking = await self.get_booking(booking_id)
        if str(booking.client_id) != client_id:
            raise ValidationException("Not your booking")
        if booking.status == BookingStatus.CANCELLED.value:
            raise ValidationException("Already cancelled")

        old_status = booking.status
        booking.status = BookingStatus.CANCELLED.value
        booking.cancellation_reason = reason
        booking.cancelled_at = datetime.now(timezone.utc)
        await self._db.flush()

        # Audit trail
        self._db.add(
            BookingStatusLog(
                booking_id=booking.guid,
                previous_status=old_status,
                new_status=BookingStatus.CANCELLED.value,
            )
        )
        await self._db.flush()
        return booking
