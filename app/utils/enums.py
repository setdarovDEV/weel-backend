import enum


class UserRole(str, enum.Enum):
    CLIENT = "client"
    PARTNER = "partner"
    ADMIN = "admin"


class VerificationStatus(str, enum.Enum):
    WAITING = "waiting"
    VERIFIED = "verified"
    ACCEPTED = "accepted"
    CANCELLED = "cancelled"


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class CalendarStatus(str, enum.Enum):
    AVAILABLE = "available"
    BOOKED = "booked"
    BLOCKED = "blocked"
    HELD = "held"


class CardType(str, enum.Enum):
    UZCARD = "uzcard"
    HUMO = "humo"


class Currency(str, enum.Enum):
    USD = "USD"
    UZS = "UZS"


class NotificationType(str, enum.Enum):
    BOOKING_CREATED = "booking_created"
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"
    BOOKING_COMPLETED = "booking_completed"
    NEW_MESSAGE = "new_message"
    PROPERTY_VERIFIED = "property_verified"


class MediaType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"


class DeviceType(str, enum.Enum):
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"


class SenderType(str, enum.Enum):
    CLIENT = "client"
    PARTNER = "partner"
    ADMIN = "admin"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class PropertyTypeSlug(str, enum.Enum):
    COTTAGE = "cottage"
    APARTMENT = "apartment"
    HOTEL = "hotel"
    DACHA = "dacha"
    VILLA = "villa"
