from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.utils.enums import Currency, VerificationStatus


# ==================== LOCATION ====================

class RegionResponse(BaseModel):
    id: int
    guid: str
    title: str
    img_url: Optional[str]

    @field_validator('guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


class DistrictResponse(BaseModel):
    id: int
    guid: str
    region_id: int
    title: str
    region: Optional[RegionResponse]

    @field_validator('guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


class PrefectureResponse(BaseModel):
    id: int
    guid: str
    district_id: int
    title: str

    @field_validator('guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


# ==================== PROPERTY TYPE & SERVICE ====================

class PropertyTypeResponse(BaseModel):
    guid: str
    title: str
    icon_url: Optional[str]
    slug: str

    @field_validator('guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


class PropertyServiceResponse(BaseModel):
    guid: str
    title: str
    icon_url: Optional[str]

    @field_validator('guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


# ==================== PROPERTY BASE ====================

class PropertyLocationBase(BaseModel):
    latitude: Optional[str]
    longitude: Optional[str]
    country: str = "Uzbekistan"
    city: str
    region_id: Optional[int]
    district_id: Optional[int]
    prefecture_id: Optional[int]


class PropertyLocationResponse(PropertyLocationBase):
    region: Optional[RegionResponse] = None
    district: Optional[DistrictResponse] = None
    prefecture: Optional[PrefectureResponse] = None

    class Config:
        from_attributes = True


class PropertyDetailBase(BaseModel):
    description_ru: Optional[str]
    description_uz: Optional[str]
    description_en: Optional[str]
    check_in_time: Optional[str]
    check_out_time: Optional[str]
    is_allowed_alcohol: bool = False
    is_allowed_pets: bool = False
    is_allowed_corporate: bool = False
    is_quiet_hours: bool = False

    class Config:
        from_attributes = True


class PropertyRoomBase(BaseModel):
    guests: int = 1
    bedrooms: int = 0
    beds: int = 1
    bathrooms: int = 1

    class Config:
        from_attributes = True


class PropertyImageResponse(BaseModel):
    guid: str
    image_url: str
    order: int

    @field_validator('guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


class PropertyPriceBase(BaseModel):
    month_from: int
    month_to: int
    price_per_person: int = 0
    price_on_working_days: int = 0
    price_on_weekends: int = 0


class PropertyPriceResponse(PropertyPriceBase):
    id: int

    class Config:
        from_attributes = True


# ==================== PROPERTY LIST ====================

class PropertyListItem(BaseModel):
    guid: str
    title: str
    location: Optional[PropertyLocationResponse]
    images: List[PropertyImageResponse]
    average_rating: Optional[float] = None
    comment_count: int = 0
    property_type_guid: str
    property_type_name: Optional[str]
    price: Optional[int]
    currency: str

    @field_validator('guid', 'property_type_guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


class PropertyListResponse(BaseModel):
    count: int
    next: Optional[str]
    previous: Optional[str]
    results: List[PropertyListItem]


# ==================== PROPERTY DETAIL ====================

class PropertyDetailResponse(BaseModel):
    guid: str
    title: str
    location: Optional[PropertyLocationResponse]
    images: List[PropertyImageResponse]
    average_rating: Optional[float]
    comment_count: int
    description: Optional[str]
    services: List[PropertyServiceResponse]
    room: Optional[PropertyRoomBase]
    is_allowed_alcohol: bool
    is_allowed_pets: bool
    is_allowed_corporate: bool
    is_quiet_hours: bool
    check_in_time: Optional[str]
    check_out_time: Optional[str]
    property_type_guid: str
    property_type_name: Optional[str]
    price: Optional[int]
    currency: str

    @field_validator('guid', 'property_type_guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


# ==================== CREATE / UPDATE ====================

class PropertyCreateBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    currency: str = Currency.UZS.value
    property_type_id: str
    location: PropertyLocationBase
    detail: PropertyDetailBase
    room: PropertyRoomBase
    services: List[str] = []
    prices: List[PropertyPriceBase] = []


class CottageCreateRequest(PropertyCreateBase):
    pass


class ApartmentCreateRequest(PropertyCreateBase):
    apartment_number: Optional[str]
    home_number: Optional[str]
    entrance_number: Optional[str]
    floor_number: Optional[str]
    pass_code: Optional[str]


class PropertyUpdateBase(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    currency: Optional[str]
    location: Optional[PropertyLocationBase]
    detail: Optional[PropertyDetailBase]
    room: Optional[PropertyRoomBase]
    services: Optional[List[str]]
    prices: Optional[List[PropertyPriceBase]]


class CottageUpdateRequest(PropertyUpdateBase):
    pass


class ApartmentUpdateRequest(PropertyUpdateBase):
    apartment_number: Optional[str]
    home_number: Optional[str]
    entrance_number: Optional[str]
    floor_number: Optional[str]
    pass_code: Optional[str]
