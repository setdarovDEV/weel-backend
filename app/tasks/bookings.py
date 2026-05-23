from app.tasks.celery_app import celery_app


@celery_app.task
def auto_cancel_pending_bookings():
    """Auto-cancel bookings that have been pending for > 24 hours."""
    # TODO: Implement auto-cancel logic
    return {"cancelled_count": 0}


@celery_app.task
def send_booking_reminders():
    """Send booking reminders 24h before check-in."""
    # TODO: Implement reminder logic
    return {"reminders_sent": 0}
