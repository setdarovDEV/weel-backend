from typing import Optional

from pydantic import BaseModel, Field


class OtpResponse(BaseModel):
    phone: str
    expires_in: int
    code: Optional[str] = None


class ClientRegisterRequest(BaseModel):
    phone_number: str
    first_name: str = ""
    last_name: str = ""


class PartnerRegisterRequest(BaseModel):
    phone_number: str
    first_name: str = ""
    last_name: str = ""
    username: str = ""


class OtpVerifyRequest(BaseModel):
    phone_number: str
    code: str
    first_name: str = ""
    last_name: str = ""
    username: str = ""


class OtpResendRequest(BaseModel):
    phone_number: str


class TokenRefreshRequest(BaseModel):
    refresh: Optional[str] = None


class LogoutRequest(BaseModel):
    refresh: str


class DeleteAccountRequest(BaseModel):
    refresh: str


class TokenResponse(BaseModel):
    access: str
    refresh: str


class ClientInfo(BaseModel):
    guid: str
    phone_number: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class PartnerInfo(BaseModel):
    guid: str
    phone_number: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class ClientVerifyResponse(BaseModel):
    access: str
    refresh: str
    client: ClientInfo


class PartnerVerifyResponse(BaseModel):
    access: str
    refresh: str
    partner: PartnerInfo
