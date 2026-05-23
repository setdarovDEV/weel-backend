from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


# ==================== OTP REQUESTS ====================

class ClientRegisterRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^998\d{9}$")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class ClientLoginRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^998\d{9}$")


class PartnerRegisterRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^998\d{9}$")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=3, max_length=100)


class PartnerLoginRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^998\d{9}$")


class OtpVerifyRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^998\d{9}$")
    code: str = Field(..., min_length=4, max_length=6)


class OtpResendRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^998\d{9}$")


# ==================== TOKEN ====================

class TokenRefreshRequest(BaseModel):
    refresh: Optional[str] = None


class TokenResponse(BaseModel):
    access: str
    refresh: str


# ==================== RESPONSES ====================

class OtpResponse(BaseModel):
    detail: str = "Code sent"
    phone_number: str
    expires_in: int = 120
    code: Optional[str] = None  # Only returned in development mode


class ClientInfo(BaseModel):
    guid: str
    phone_number: str
    first_name: Optional[str]
    last_name: Optional[str]

    @field_validator('guid', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


class PartnerInfo(BaseModel):
    guid: str
    phone_number: str
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]

    @field_validator('guid', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True


class ClientVerifyResponse(BaseModel):
    access: str
    refresh: str
    client: ClientInfo


class PartnerVerifyResponse(BaseModel):
    access: str
    refresh: str
    partner: PartnerInfo


class LogoutRequest(BaseModel):
    refresh: Optional[str] = None


class DeleteAccountRequest(BaseModel):
    refresh: Optional[str] = None
