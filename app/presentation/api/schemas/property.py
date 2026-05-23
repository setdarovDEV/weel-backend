from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class PropertyTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guid: str
    title: str
    slug: str
    icon_url: Optional[str] = None


class PropertyImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guid: str
    image_url: str
    order: int


class PropertyPriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    month_from: int
    month_to: int
    price_per_person: int
    price_on_working_days: int
    price_on_weekends: int


class PropertyServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guid: str
    title: str
    icon_url: Optional[str] = None


class PropertyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guid: str
    title: str
    city: str
    country: str = "Uzbekistan"
    guests: int
    bedrooms: int
    beds: int
    bathrooms: int
    is_recommended: bool = False
    verification_status: str
    images: List[PropertyImageRead] = []


class PropertyDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guid: str
    title: str
    description: Optional[str] = None
    city: str
    country: str = "Uzbekistan"
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    guests: int
    bedrooms: int
    beds: int
    bathrooms: int
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    is_allowed_alcohol: bool = False
    is_allowed_pets: bool = False
    is_allowed_corporate: bool = False
    is_quiet_hours: bool = False
    apartment_number: Optional[str] = None
    home_number: Optional[str] = None
    entrance_number: Optional[str] = None
    floor_number: Optional[str] = None
    pass_code: Optional[str] = None
    images: List[PropertyImageRead] = []
    prices: List[PropertyPriceRead] = []
    services: List[PropertyServiceRead] = []


class PropertyCreateRequest(BaseModel):
    property_type_id: str
    title: str
    description: Optional[str] = None
    city: str
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    guests: int = 1
    bedrooms: int = 0
    beds: int = 1
    bathrooms: int = 1
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    is_allowed_alcohol: bool = False
    is_allowed_pets: bool = False
    is_allowed_corporate: bool = False
    is_quiet_hours: bool = False
    apartment_number: Optional[str] = None
    home_number: Optional[str] = None
    entrance_number: Optional[str] = None
    floor_number: Optional[str] = None
    pass_code: Optional[str] = None
    prices: List[dict] = []
    service_ids: List[str] = []
