from app.tasks.celery_app import celery_app


@celery_app.task
def send_otp_sms(phone: str, code: str):
    """Send OTP via Eskiz SMS."""
    # TODO: Implement Eskiz API integration
    return {"phone": phone, "code": code, "status": "sent"}
