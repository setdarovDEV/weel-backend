"""Unified Authentication Application Service.

Optimized for all user roles (client, partner, admin) with minimal endpoints.
"""

import hashlib
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import UserRole
from app.core.exceptions import (
    AuthenticationException,
    NotFoundException,
    ValidationException,
)
from app.core.logging_config import get_logger
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.infrastructure.cache.redis_cache import RedisCache
from app.infrastructure.database.models.user import User
from app.presentation.api.schemas.auth_v2 import (
    TokenResponse,
    UserProfile,
    VerifyResponse,
)

logger = get_logger(__name__)

# In-memory refresh token store (dev fallback without DB table)
_refresh_store: dict = {}


def _cleanup_refresh_store():
    now = datetime.now(timezone.utc)
    expired = [k for k, v in list(_refresh_store.items()) if v.get("expires") and v["expires"] < now]
    for k in expired:
        del _refresh_store[k]


class OTPService:
    """OTP generation and verification using Redis."""

    TTL_SECONDS = 120

    @staticmethod
    def _key(phone: str, purpose: str, role: str) -> str:
        return f"otp:{purpose}:{role}:{phone}"

    @staticmethod
    def generate_code() -> str:
        return str(random.randint(1000, 9999))

    @classmethod
    async def store(cls, phone: str, purpose: str, role: str, code: str) -> None:
        key = cls._key(phone, purpose, role)
        await RedisCache.set(key, code, expire=cls.TTL_SECONDS)
        logger.info(f"OTP stored for {phone} purpose={purpose} role={role}")

    @classmethod
    async def verify(cls, phone: str, purpose: str, role: str, code: str) -> bool:
        key = cls._key(phone, purpose, role)
        stored = await RedisCache.get(key)
        if stored and stored == code:
            await RedisCache.delete(key)
            return True
        return False


class AuthApplicationService:
    """Unified auth service for all roles."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Core Users
    # ------------------------------------------------------------------
    async def get_or_create_user(self, phone: str) -> User:
        result = await self._db.execute(select(User).where(User.phone_number == phone))
        user: Optional[User] = result.scalar_one_or_none()
        if not user:
            user = User(phone_number=phone, role="client")
            self._db.add(user)
            await self._db.flush()
            logger.info(f"Created new user {phone}")
        return user

    async def soft_delete_user(self, user_id: str) -> None:
        result = await self._db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if user:
            user.is_active = False
            await self._db.flush()

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------
    async def assign_role(self, user_id: str, role: UserRole) -> None:
        result = await self._db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if user:
            user.role = role.value
            await self._db.flush()

    # ------------------------------------------------------------------
    # Profiles
    # ------------------------------------------------------------------
    async def get_or_create_client(self, user_id: str, first_name: str = "", last_name: str = "") -> User:
        result = await self._db.execute(select(User).where(User.id == int(user_id)))
        user: Optional[User] = result.scalar_one_or_none()
        if not user:
            raise NotFoundException("User not found")
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        await self._db.flush()
        return user

    async def get_or_create_partner(
        self, user_id: str, first_name: str = "", last_name: str = "", username: str = ""
    ) -> User:
        result = await self._db.execute(select(User).where(User.id == int(user_id)))
        user: Optional[User] = result.scalar_one_or_none()
        if not user:
            raise NotFoundException("User not found")
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if username:
            user.username = username
        await self._db.flush()
        return user

    # ------------------------------------------------------------------
    # Tokens (in-memory store, no DB table)
    # ------------------------------------------------------------------
    async def generate_token_pair(self, user_id: str) -> TokenResponse:
        access = create_access_token({"sub": user_id})
        refresh = create_refresh_token({"sub": user_id})
        return TokenResponse(access=access, refresh=refresh)

    async def store_refresh_token(self, token: str, user_id: str) -> None:
        _cleanup_refresh_store()
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        _refresh_store[token_hash] = {"user_id": int(user_id), "expires": expires, "revoked": False}

    async def revoke_refresh_token(self, token: str) -> None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        entry = _refresh_store.get(token_hash)
        if entry:
            entry["revoked"] = True

    async def is_refresh_token_valid(self, token: str) -> bool:
        _cleanup_refresh_store()
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        entry = _refresh_store.get(token_hash)
        if entry is None or entry["revoked"]:
            return False
        if entry["expires"] < datetime.now(timezone.utc):
            del _refresh_store[token_hash]
            return False
        return True

    # ------------------------------------------------------------------
    # Unified OTP Send
    # ------------------------------------------------------------------
    async def send_otp(self, phone: str, purpose: str, role: str) -> dict:
        """Send OTP for register/login (client/partner)."""
        if role not in ("client", "partner"):
            raise ValidationException("OTP only available for client or partner roles")

        if purpose not in ("register", "login"):
            raise ValidationException("Purpose must be 'register' or 'login'")

        if purpose == "register":
            await self.get_or_create_user(phone)
        else:
            result = await self._db.execute(select(User).where(User.phone_number == phone))
            if not result.scalar_one_or_none():
                raise NotFoundException("User not found. Please register first.")

        code = OTPService.generate_code()
        await OTPService.store(phone, purpose, role, code)

        return {
            "phone": phone,
            "purpose": purpose,
            "role": role,
            "expires_in": OTPService.TTL_SECONDS,
            "code": code if settings.environment == "development" else None,
        }

    # ------------------------------------------------------------------
    # Unified OTP Verify
    # ------------------------------------------------------------------
    async def verify_otp(
        self,
        phone: str,
        code: str,
        purpose: str,
        role: str,
        first_name: str = "",
        last_name: str = "",
        username: str = "",
    ) -> VerifyResponse:
        """Verify OTP and return tokens + user profile."""
        if not await OTPService.verify(phone, purpose, role, code):
            raise ValidationException("Invalid or expired OTP code")

        user = await self.get_or_create_user(phone)
        user_id = str(user.id)

        if role == "client":
            await self.assign_role(user_id, UserRole.CLIENT)
            client = await self.get_or_create_client(user_id, first_name, last_name)
            profile = UserProfile(
                guid=user_id,
                phone_number=user.phone_number,
                first_name=client.first_name,
                last_name=client.last_name,
                role="client",
            )
        elif role == "partner":
            await self.assign_role(user_id, UserRole.PARTNER)
            partner = await self.get_or_create_partner(user_id, first_name, last_name, username)
            profile = UserProfile(
                guid=user_id,
                phone_number=user.phone_number,
                first_name=partner.first_name,
                last_name=partner.last_name,
                username=partner.username,
                role="partner",
            )
        else:
            raise ValidationException("Role must be 'client' or 'partner'")

        tokens = await self.generate_token_pair(user_id)
        await self.store_refresh_token(tokens.refresh, user_id)

        return VerifyResponse(
            access=tokens.access,
            refresh=tokens.refresh,
            user=profile,
        )

    # ------------------------------------------------------------------
    # Admin Login (plain password from config)
    # ------------------------------------------------------------------
    async def admin_login(self, email: str, password: str) -> TokenResponse:
        """Admin login with email and password (compared against config)."""
        result = await self._db.execute(
            select(User).where(User.email == email, User.role == "admin")
        )
        admin: Optional[User] = result.scalar_one_or_none()
        if not admin:
            raise AuthenticationException("Invalid credentials")

        if password != settings.admin_default_password:
            raise AuthenticationException("Invalid credentials")

        user_id = str(admin.id)
        tokens = await self.generate_token_pair(user_id)
        await self.store_refresh_token(tokens.refresh, user_id)
        return tokens

    # ------------------------------------------------------------------
    # Shared
    # ------------------------------------------------------------------
    async def refresh_tokens(self, refresh_token: Optional[str]) -> TokenResponse:
        if not refresh_token or not await self.is_refresh_token_valid(refresh_token):
            raise AuthenticationException("Invalid or expired refresh token")

        payload = decode_token(refresh_token)
        if not payload:
            raise AuthenticationException("Invalid token payload")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationException("Missing subject in token")

        await self.revoke_refresh_token(refresh_token)
        new_tokens = await self.generate_token_pair(user_id)
        await self.store_refresh_token(new_tokens.refresh, user_id)
        return new_tokens

    async def logout(self, refresh_token: str) -> None:
        await self.revoke_refresh_token(refresh_token)

    async def delete_account(self, refresh_token: str) -> None:
        payload = decode_token(refresh_token)
        if not payload:
            raise AuthenticationException("Invalid token")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationException("Missing subject")

        await self.revoke_refresh_token(refresh_token)
        await self.soft_delete_user(user_id)
