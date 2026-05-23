from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime, date
from app.utils.enums import BookingStatus, CalendarStatus


# ==================== BOOKING REQUESTS ====================

class BookingCreateRequest(BaseModel):
    property_id: str
    card_id: Optional[str]
    check_in: date
    check_out: date
    adults: int = Field(1, ge=1)
    children: int = Field(0, ge=0)
    babies: int = Field(0, ge=0)


class BookingCancelRequest(BaseModel):
    reason: Optional[str] = None


# ==================== BOOKING RESPONSES ====================

class BookingPriceResponse(BaseModel):
    subtotal: int
    hold_amount: int
    charge_amount: int
    service_fee: int
    service_fee_percentage: int

    class Config:
        from_attributes = True


class BookingPropertyResponse(BaseModel):
    guid: str
    title: str
    property_images: Optional[str]

    @field_validator('guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


class BookingClientResponse(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]

    class Config:
        from_attributes = True


class BookingResponse(BaseModel):
    guid: str
    property: Optional[BookingPropertyResponse]
    client: Optional[BookingClientResponse]
    check_in: date
    check_out: date
    adults: int
    children: int
    babies: int
    booking_price: Optional[BookingPriceResponse]
    booking_number: str
    status: str
    cancellation_reason: Optional[str]
    confirmed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    completed_at: Optional[datetime]

    @field_validator('guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


class BookingHistoryItem(BaseModel):
    guid: str
    property_guid: Optional[str]
    title: Optional[str]
    image_url: Optional[str]
    created_at: datetime
    category: Optional[str]
    status: str
    check_in: date
    check_out: date
    city: Optional[str]
    country: Optional[str]
    rating: Optional[float]
    booking_number: str
    price: Optional[int]
    currency: Optional[str]
    partner_name: Optional[str]
    partner_phone: Optional[str]
    latitude: Optional[str]
    longitude: Optional[str]

    @field_validator('guid', 'property_guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v


# ==================== CALENDAR ====================

class CalendarDateResponse(BaseModel):
    date: date
    status: str

    class Config:
        from_attributes = True


class CalendarBlockRequest(BaseModel):
    dates: List[date]


class CalendarHoldRequest(BaseModel):
    dates: List[date]
