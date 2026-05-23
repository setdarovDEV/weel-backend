from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OtpResponseDto(BaseModel):
    phone_number: str
    expires_in: int
    code: Optional[str] = None


class ClientRegisterDto(BaseModel):
    phone_number: str
    first_name: str = ""
    last_name: str = ""


class PartnerRegisterDto(BaseModel):
    phone_number: str
    first_name: str = ""
    last_name: str = ""
    username: str = ""


class OtpVerifyDto(BaseModel):
    phone_number: str
    code: str


class TokenPairDto(BaseModel):
    access_token: str
    refresh_token: str


class ClientInfoDto(BaseModel):
    guid: str
    phone_number: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class PartnerInfoDto(BaseModel):
    guid: str
    phone_number: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class ClientVerifyResponseDto(BaseModel):
    access: str
    refresh: str
    client: ClientInfoDto


class PartnerVerifyResponseDto(BaseModel):
    access: str
    refresh: str
    partner: PartnerInfoDto


class TokenRefreshDto(BaseModel):
    refresh: str


class LogoutDto(BaseModel):
    refresh: str


class DeleteAccountDto(BaseModel):
    refresh: str
