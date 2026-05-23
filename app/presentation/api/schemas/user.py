from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guid: str
    phone_number: str
    is_active: bool


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class PartnerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    verification_status: str
