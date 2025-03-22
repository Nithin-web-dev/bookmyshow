from django.utils.timezone import now
from datetime import timedelta
from .models import Seat

def release_expired_seats():
    """Release seats that were reserved more than 5 minutes ago"""
    timeout = now() - timedelta(minutes=5)
    expired_seats = Seat.objects.filter(
        reserved_at__lt=timeout,
        is_booked=False
    )
    for seat in expired_seats:
        seat.release() 