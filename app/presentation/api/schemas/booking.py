from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class BookingClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guid: str
    phone_number: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class BookingPropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guid: str
    title: str
    city: str


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guid: str
    property: BookingPropertyRead
    client: BookingClientRead
    check_in: datetime
    check_out: datetime
    adults: int
    children: int
    babies: int
    booking_number: str
    status: str
    cancellation_reason: Optional[str] = None
    subtotal: int
    hold_amount: int
    charge_amount: int
    service_fee: int
    created_at: datetime


class BookingCreateRequest(BaseModel):
    property_id: str
    check_in: datetime
    check_out: datetime
    adults: int = 1
    children: int = 0
    babies: int = 0


class BookingCancelRequest(BaseModel):
    reason: Optional[str] = None
