"""Optimized authentication schemas for unified auth router."""

from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================
# OTP (client / partner)
# ============================================================
class OtpSendRequest(BaseModel):
    phone: str = Field(..., description="Phone number, e.g. +998901234567")
    purpose: str = Field(..., description="register | login")
    role: str = Field(..., description="client | partner")


class OtpVerifyRequest(BaseModel):
    phone: str
    code: str
    purpose: str = Field(..., description="register | login")
    role: str = Field(..., description="client | partner")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None


# ============================================================
# Admin Login
# ============================================================
class AdminLoginRequest(BaseModel):
    email: str
    password: str


# ============================================================
# Token
# ============================================================
class TokenRefreshRequest(BaseModel):
    refresh: Optional[str] = None


class LogoutRequest(BaseModel):
    refresh: Optional[str] = None


class DeleteAccountRequest(BaseModel):
    refresh: Optional[str] = None


class TokenResponse(BaseModel):
    access: str
    refresh: str


# ============================================================
# User Info
# ============================================================
class UserInfoResponse(BaseModel):
    guid: str
    phone_number: str
    is_active: bool
    roles: List[str]


# ============================================================
# Verify Response (role-aware)
# ============================================================
class UserProfile(BaseModel):
    guid: str
    phone_number: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    role: str


class VerifyResponse(BaseModel):
    access: str
    refresh: str
    user: UserProfile
