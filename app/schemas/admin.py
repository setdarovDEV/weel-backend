from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime


class AdminLoginRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class AdminAuthResponse(BaseModel):
    access: str
    refresh: str
    user: dict


class UserListItem(BaseModel):
    guid: str
    phone_number: str
    first_name: Optional[str]
    last_name: Optional[str]
    created_at: datetime

    @field_validator('guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


class AdminBookingFilter(BaseModel):
    status: Optional[str] = None
    region: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None
    overdue: Optional[bool] = None


class AdminPropertyUpdate(BaseModel):
    verification_status: Optional[str] = None
    is_archived: Optional[bool] = None
    is_recommended: Optional[bool] = None


class StoryModerateRequest(BaseModel):
    is_verified: bool


class DashboardStats(BaseModel):
    total_users: int
    total_partners: int
    total_properties: int
    total_bookings: int
    pending_verifications: int
