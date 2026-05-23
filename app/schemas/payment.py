from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from app.utils.enums import CardType


class CardResponse(BaseModel):
    id: str
    guid: str
    card_number: str
    expiry_date: str
    card_holder: str
    type: str

    @field_validator('guid', 'id', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


class AddCardRequest(BaseModel):
    card_number: str = Field(..., min_length=16, max_length=16)
    expiry_date: str = Field(..., pattern=r"^\d{2}/\d{2}$")
    card_holder: str = Field(..., min_length=1, max_length=255)


class AddCardResponse(BaseModel):
    session: str
    detail: str = "OTP sent"


class VerifyCardRequest(BaseModel):
    session_id: str
    otp_code: str = Field(..., min_length=4, max_length=6)


class ResendCardOtpRequest(BaseModel):
    session_id: str
