"""Application constants."""

from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class UserRole(str, Enum):
    CLIENT = "client"
    PARTNER = "partner"
    ADMIN = "admin"


class VerificationStatus(str, Enum):
    WAITING = "waiting"
    VERIFIED = "verified"
    REJECTED = "rejected"


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class CalendarStatus(str, Enum):
    AVAILABLE = "available"
    BOOKED = "booked"
    BLOCKED = "blocked"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class CardType(str, Enum):
    UZCARD = "uzcard"
    HUMO = "humo"


class Currency(str, Enum):
    UZS = "UZS"
    USD = "USD"
