from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ClientProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)


class PartnerProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    username: Optional[str] = Field(None, max_length=100)


class ClientProfileResponse(BaseModel):
    guid: str
    phone_number: str
    first_name: Optional[str]
    last_name: Optional[str]

    @field_validator('guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


class PartnerProfileResponse(BaseModel):
    guid: str
    phone_number: str
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    avatar_url: Optional[str]
    verification_status: str

    @field_validator('guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True
