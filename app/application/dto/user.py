from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserReadDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guid: str
    phone_number: str
    is_active: bool
    is_deleted: bool


class ClientReadDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class PartnerReadDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    verification_status: str


class AdminReadDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: EmailStr
    is_staff: bool
    is_superuser: bool
