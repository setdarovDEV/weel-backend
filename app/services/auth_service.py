import random
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.models.user import User
from app.utils.security import create_access_token, create_refresh_token, decode_token


# In-memory OTP fallback store (only for dev without Redis)
_memory_store: dict = {}
_refresh_store: dict = {}

def _cleanup_memory_store():
    now = datetime.now(timezone.utc)
    expired = [k for k, (_, exp) in _memory_store.items() if exp < now]
    for k in expired:
        del _memory_store[k]


def _cleanup_refresh_store():
    now = datetime.now(timezone.utc)
    expired = [k for k, v in list(_refresh_store.items()) if v.get("expires") and v["expires"] < now]
    for k in expired:
        del _refresh_store[k]


class OTPService:
    @staticmethod
    def _otp_key(phone: str, purpose: str) -> str:
        return f"otp:{purpose}:{phone}"

    @staticmethod
    def generate_code() -> str:
        return str(random.randint(1000, 9999))

    @staticmethod
    async def store_otp(phone: str, purpose: str, code: str, expiry: int = 120):
        key = OTPService._otp_key(phone, purpose)
        _memory_store[key] = (code, datetime.now(timezone.utc) + timedelta(seconds=expiry))
        _cleanup_memory_store()

    @staticmethod
    async def verify_otp(phone: str, purpose: str, code: str) -> bool:
        key = OTPService._otp_key(phone, purpose)
        if key in _memory_store:
            stored_code, expires = _memory_store[key]
            if expires > datetime.now(timezone.utc) and stored_code == code:
                del _memory_store[key]
                return True
        return False


class AuthService:
    @staticmethod
    async def get_or_create_user(db: AsyncSession, phone: str) -> User:
        result = await db.execute(select(User).where(User.phone_number == phone))
        user = result.scalar_one_or_none()
        if not user:
            user = User(phone_number=phone)
            db.add(user)
            await db.flush()
        return user

    @staticmethod
    async def generate_token_pair(user_id: int) -> Tuple[str, str]:
        access = create_access_token({"sub": str(user_id)})
        refresh = create_refresh_token({"sub": str(user_id)})
        return access, refresh

    @staticmethod
    async def store_refresh_token(db: AsyncSession, token: str, user_id: int):
        _cleanup_refresh_store()
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        _refresh_store[token_hash] = {"user_id": user_id, "expires": expires, "revoked": False}

    @staticmethod
    async def revoke_refresh_token(db: AsyncSession, token: str):
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if token_hash in _refresh_store:
            _refresh_store[token_hash]["revoked"] = True

    @staticmethod
    async def is_refresh_token_valid(db: AsyncSession, token: str) -> bool:
        _cleanup_refresh_store()
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        entry = _refresh_store.get(token_hash)
        if entry is None:
            return False
        if entry["revoked"]:
            return False
        if entry["expires"] < datetime.now(timezone.utc):
            del _refresh_store[token_hash]
            return False
        return True

    @staticmethod
    async def get_user_by_phone(db: AsyncSession, phone: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.phone_number == phone))
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int):
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_active = False
            await db.flush()
