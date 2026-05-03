from datetime import date, datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.db import models
from courts.models import Court
from accounts.decorators import admin_or_staff_required
from .forms import BookingForm, AdminBookingForm
from .models import Booking
from . import services


# ── Customer Views ─────────────────────────────────────────────────────────────

@login_required
def availability_view(request):
    """Show court availability grid for a selected date."""
    selected_date_str = request.GET.get('date', date.today().isoformat())
    try:
        selected_date = date.fromisoformat(selected_date_str)
    except ValueError:
        selected_date = date.today()

    grid = services.get_availability(selected_date)

    return render(request, 'bookings/availability.html', {
        'grid':          grid,
        'selected_date': selected_date,
        'today':         date.today().isoformat(),
        'slots':         services.get_time_slots(),
    })


@login_required
def booking_create_view(request):
    """
    Two-phase booking:
    Phase 1 (GET)  — user picks court + date → page reloads showing available slots.
    Phase 2 (POST) — user submits selected slots → bookings created.
    """
    from django.conf import settings as django_settings
    from datetime import datetime

    court_id      = request.GET.get('court') or request.POST.get('court')
    selected_date = request.GET.get('date')  or request.POST.get('date')

    court          = None
    available_slots = None
    parsed_date    = None

    # Resolve court and date to show slot checkboxes
    if court_id and selected_date:
        try:
            court       = Court.objects.get(pk=court_id, is_active=True)
            parsed_date = date.fromisoformat(selected_date)
            available_slots = services.get_available_slots_for_court(court, parsed_date)
        except (Court.DoesNotExist, ValueError):
            court = None

    if request.method == 'POST':
        form = BookingForm(request.POST, available_slots=available_slots)

        if not form.is_valid():
            pass  # fall through to render with errors

        elif not form.cleaned_data.get('time_slots'):
            form.add_error('time_slots', 'Please select at least one time slot.')

        else:
            data       = form.cleaned_data
            slots      = data['time_slots']        # list of 'HH:MM:SS' strings
            created    = []
            errors     = []

            for slot_str in slots:
                try:
                    t = datetime.strptime(slot_str, '%H:%M:%S').time()
                    booking = services.create_booking(
                        user=request.user,
                        court=data['court'],
                        selected_date=data['date'],
                        start_time=t,
                        notes=data.get('notes', ''),
                    )
                    created.append(booking)
                except ValidationError as e:
                    errors.append(str(e.message))

            if created:
                total_hrs   = len(created)
                total_price = sum(b.price for b in created)
                messages.success(
                    request,
                    f'✅ {total_hrs} slot(s) booked on {parsed_date.strftime("%b %d, %Y")} '
                    f'for {data["court"]}. '
                    f'Total: ₱{total_price} — pay on-site.'
                )
            for err in errors:
                messages.warning(request, f'⚠️ Skipped one slot: {err}')

            if created:
                return redirect('bookings:my_bookings')

    else:
        # Pre-fill court/date from query params (e.g. clicking grid)
        initial = {'court': court_id, 'date': selected_date}
        form = BookingForm(initial=initial, available_slots=available_slots)

    return render(request, 'bookings/booking_form.html', {
        'form':           form,
        'title':          'Book a Court',
        'price_per_hour': django_settings.BOOKING_PRICE,
        'court':          court,
        'selected_date':  parsed_date,
        'slots_available': available_slots,
    })


@login_required
def my_bookings_view(request):
    """Show logged-in user's booking history with summary and pagination."""
    services.auto_update_booking_statuses()  # Ensure statuses are up-to-date before fetching

    from django.core.paginator import Paginator
    from django.db.models import Sum, Count

    all_bookings = (
        Booking.objects
        .filter(user=request.user)
        .select_related('court')
        .order_by('-date', '-start_time')
    )

    # ── Summary ────────────────────────────────────────────────────
    summary = all_bookings.aggregate(
        total_bookings=Count('id'),
        total_spent=Sum(
            'price',
            filter=models.Q(
                status__in=[
                    Booking.Status.CONFIRMED,
                    Booking.Status.COMPLETED,
                ]
            )
        )
    )

    # ── Pagination ─────────────────────────────────────────────────
    paginator = Paginator(all_bookings, 10)
    page      = request.GET.get('page', 1)
    bookings  = paginator.get_page(page)

    return render(request, 'bookings/my_bookings.html', {
        'bookings':       bookings,
        'total_bookings': summary['total_bookings'] or 0,
        'total_spent':    summary['total_spent']    or 0,
    })


@login_required
def booking_cancel_view(request, pk):
    """Customer cancels their own booking."""
    booking = get_object_or_404(Booking, pk=pk, user=request.user)

    if request.method == 'POST':
        try:
            services.cancel_booking(booking, cancelled_by=request.user)
            messages.success(request, 'Booking cancelled successfully.')
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('bookings:my_bookings')

    return render(request, 'bookings/booking_cancel_confirm.html', {'booking': booking})


# ── Admin/Staff Views ──────────────────────────────────────────────────────────

@admin_or_staff_required
def admin_booking_list_view(request):
    """Admin view of all bookings with filters."""
    services.auto_update_booking_statuses()  # Keep statuses current on admin page load
    bookings = Booking.objects.select_related('court', 'user').order_by('-date', '-start_time')

    # Filters
    status_filter = request.GET.get('status')
    date_filter   = request.GET.get('date')
    court_filter  = request.GET.get('court')

    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if date_filter:
        bookings = bookings.filter(date=date_filter)
    if court_filter:
        bookings = bookings.filter(court_id=court_filter)

    return render(request, 'bookings/admin_booking_list.html', {
        'bookings':       bookings,
        'courts':         Court.objects.filter(is_active=True),
        'status_choices': Booking.Status.choices,
        'status_filter':  status_filter,
        'date_filter':    date_filter,
        'court_filter':   court_filter,
    })


@admin_or_staff_required
def admin_booking_create_view(request):
    """Admin creates multi-slot booking for any user."""
    from django.conf import settings as django_settings
    from datetime import datetime

    court_id      = request.GET.get('court') or request.POST.get('court')
    selected_date = request.GET.get('date')  or request.POST.get('date')

    court           = None
    available_slots = None
    parsed_date     = None

    if court_id and selected_date:
        try:
            court           = Court.objects.get(pk=court_id, is_active=True)
            parsed_date     = date.fromisoformat(selected_date)
            available_slots = services.get_available_slots_for_court(court, parsed_date)
        except (Court.DoesNotExist, ValueError):
            court = None

    if request.method == 'POST':
        form = AdminBookingForm(request.POST, available_slots=available_slots)

        if not form.is_valid():
            pass

        elif not form.cleaned_data.get('time_slots'):
            form.add_error('time_slots', 'Please select at least one time slot.')

        else:
            data    = form.cleaned_data
            slots   = data['time_slots']
            created = []
            errors  = []

            for slot_str in slots:
                try:
                    t = datetime.strptime(slot_str, '%H:%M:%S').time()
                    booking = services.create_booking(
                        user=data['user'],
                        court=data['court'],
                        selected_date=data['date'],
                        start_time=t,
                        created_by=request.user,
                        notes=data.get('notes', ''),
                    )
                    created.append(booking)
                except ValidationError as e:
                    errors.append(str(e.message))

            if created:
                messages.success(
                    request,
                    f'{len(created)} booking(s) created for {data["user"].full_name}.'
                )
            for err in errors:
                messages.warning(request, f'Skipped: {err}')

            if created:
                return redirect('bookings:admin_list')

    else:
        initial = {'court': court_id, 'date': selected_date}
        form = AdminBookingForm(initial=initial, available_slots=available_slots)

    return render(request, 'bookings/booking_form.html', {
        'form':           form,
        'title':          'Create Booking (Admin)',
        'price_per_hour': django_settings.BOOKING_PRICE,
        'court':          court,
        'selected_date':  parsed_date,
        'slots_available': available_slots,
        'is_admin':       True,
    })


@admin_or_staff_required
def admin_booking_cancel_view(request, pk):
    """Admin cancels any booking."""
    booking = get_object_or_404(Booking, pk=pk)

    if request.method == 'POST':
        try:
            services.cancel_booking(booking, cancelled_by=request.user)
            messages.success(request, f'Booking #{pk} cancelled.')
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('bookings:admin_list')

    return render(request, 'bookings/booking_cancel_confirm.html', {
        'booking':   booking,
        'is_admin': True,
    })


@admin_or_staff_required
def admin_booking_status_view(request, pk):
    """Admin updates booking status and syncs the linked transaction."""
    from transactions.models import Transaction

    booking = get_object_or_404(Booking, pk=pk)

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if new_status not in dict(Booking.Status.choices):
            messages.error(request, 'Invalid status.')
            return redirect('bookings:admin_list')

        booking.status = new_status
        if new_status == Booking.Status.CANCELLED:
            booking.cancelled_at = timezone.now()
        booking.save(update_fields=['status', 'cancelled_at'])

        # ── Sync linked transaction payment status ─────────────────
        try:
            tx = booking.transaction
            if new_status == Booking.Status.CONFIRMED:
                tx.payment_status = Transaction.PaymentStatus.PENDING
            elif new_status == Booking.Status.COMPLETED:
                tx.payment_status = Transaction.PaymentStatus.PAID
            elif new_status == Booking.Status.CANCELLED:
                tx.payment_status = Transaction.PaymentStatus.REFUNDED
            else:
                tx.payment_status = Transaction.PaymentStatus.WAIVED
            tx.save(update_fields=['payment_status'])
        except Exception:
            pass   # no transaction linked — safe to ignore

        messages.success(
            request,
            f'Booking #{pk} status updated to '
            f'{booking.get_status_display()}.'
        )
        return redirect('bookings:admin_list')

    return render(request, 'bookings/admin_booking_status.html', {
        'booking':        booking,
        'status_choices': Booking.Status.choices,
    })