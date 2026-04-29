from datetime import date, time, datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from courts.models import Court
from .models import Booking


# ── Slot Generation ────────────────────────────────────────────────────────────

def get_time_slots():
    """Return list of time slot tuples (time obj, display string)."""
    slots = []
    hour = settings.BOOKING_OPENING_HOUR
    while hour < settings.BOOKING_CLOSING_HOUR:
        t = time(hour, 0)
        end = time(hour + 1, 0)
        label = f'{t.strftime("%I:%M %p")} – {end.strftime("%I:%M %p")}'
        slots.append((t, label))
        hour += 1
    return slots


# ── Availability ───────────────────────────────────────────────────────────────

def get_availability(selected_date):
    """
    Returns a dict: { time_slot: { court_id: 'available'|'booked' } }
    Used to render the booking grid.
    """
    courts = Court.objects.filter(is_active=True)
    slots  = get_time_slots()

    # Fetch all active bookings for this date in one query
    bookings = Booking.objects.filter(
        date=selected_date,
        status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED]
    ).values('court_id', 'start_time')

    booked_set = {(b['court_id'], b['start_time']) for b in bookings}

    grid = {}
    for slot_time, slot_label in slots:
        grid[slot_label] = {}
        for court in courts:
            is_booked = (court.id, slot_time) in booked_set
            grid[slot_label][court] = 'booked' if is_booked else 'available'

    return grid


def is_slot_available(court, selected_date, start_time):
    """Check if a specific court/date/time is free."""
    return not Booking.objects.filter(
        court=court,
        date=selected_date,
        start_time=start_time,
        status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED]
    ).exists()


def is_past_slot(selected_date, start_time):
    """Return True if the slot is in the past."""
    slot_dt = datetime.combine(selected_date, start_time)
    slot_dt = timezone.make_aware(slot_dt)
    return slot_dt <= timezone.now()


# ── Booking Creation ───────────────────────────────────────────────────────────

def create_booking(user, court, selected_date, start_time, created_by=None, notes=''):
    """
    Create a booking after validating availability.
    Raises ValidationError on conflict.
    """
    if is_past_slot(selected_date, start_time):
        raise ValidationError('Cannot book a slot in the past.')

    if not is_slot_available(court, selected_date, start_time):
        raise ValidationError(
            f'{court.name} is already booked on '
            f'{selected_date.strftime("%b %d")} at {start_time.strftime("%I:%M %p")}.'
        )

    booking = Booking.objects.create(
        user=user,
        court=court,
        date=selected_date,
        start_time=start_time,
        price=settings.BOOKING_PRICE,
        created_by=created_by or user,
        notes=notes,
    )

    # Create corresponding transaction record
    _create_booking_transaction(booking)

    return booking


def _create_booking_transaction(booking):
    """Auto-create a pending transaction when a booking is made."""
    from transactions.models import Transaction
    Transaction.objects.create(
        user=booking.user,
        tx_type=Transaction.TxType.BOOKING,
        amount=booking.price,
        booking=booking,
        description=f'Court booking – {booking.court} on {booking.date} at {booking.start_time}',
        created_by=booking.created_by,
    )


# ── Cancellation ───────────────────────────────────────────────────────────────

def cancel_booking(booking, cancelled_by=None):
    """
    Cancel a booking if it's still cancellable.
    Raises ValidationError if not allowed.
    """
    if not booking.is_cancellable:
        raise ValidationError('This booking cannot be cancelled.')

    booking.cancel()

    # Mark linked transaction as refunded
    if hasattr(booking, 'transaction'):
        booking.transaction.payment_status = 'refunded'
        booking.transaction.save(update_fields=['payment_status'])

    return booking


# ── Court Availability ───────────────────────────────────────────────────────────────

def get_available_slots_for_court(court, selected_date):
    """
    Returns list of (value, label) tuples for slots that are
    still available for a specific court on a specific date.
    Excludes past slots.
    """
    all_slots = get_time_slots()

    booked_times = set(
        Booking.objects.filter(
            court=court,
            date=selected_date,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED]
        ).values_list('start_time', flat=True)
    )

    available = []
    for slot_time, label in all_slots:
        if slot_time in booked_times:
            continue
        if is_past_slot(selected_date, slot_time):
            continue
        available.append((slot_time.strftime('%H:%M:%S'), label))

    return available