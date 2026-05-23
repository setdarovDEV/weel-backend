"""Application-wide custom exceptions following Clean Architecture.

Domain exceptions are agnostic of the framework (FastAPI).
They are mapped to HTTP responses in the presentation layer.
"""


class DomainException(Exception):
    """Base domain exception."""

    def __init__(self, message: str = "Domain error", code: str = "DOMAIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundException(DomainException):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, code="NOT_FOUND")


class ConflictException(DomainException):
    """Resource conflict / duplicate."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, code="CONFLICT")


class ValidationException(DomainException):
    """Input validation failed at domain level."""

    def __init__(self, message: str = "Validation error"):
        super().__init__(message, code="VALIDATION_ERROR")


class AuthenticationException(DomainException):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="AUTHENTICATION_ERROR")


class AuthorizationException(DomainException):
    """Authorization / permission denied."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, code="AUTHORIZATION_ERROR")


class PaymentException(DomainException):
    """Payment processing error."""

    def __init__(self, message: str = "Payment error"):
        super().__init__(message, code="PAYMENT_ERROR")


class ExternalServiceException(DomainException):
    """External service (SMS, Firebase, MinIO) error."""

    def __init__(self, message: str = "External service error"):
        super().__init__(message, code="EXTERNAL_SERVICE_ERROR")
