from datetime import date, datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
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
    """Customer creates a new booking."""
    # Pre-fill from query params (e.g. clicking a slot on the grid)
    initial = {
        'court':      request.GET.get('court'),
        'date':       request.GET.get('date', date.today().isoformat()),
        'start_time': request.GET.get('time'),
    }

    form = BookingForm(request.POST or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        data  = form.cleaned_data
        court = data['court']

        # Parse start_time string back to time object
        from datetime import time as dtime
        try:
            t = datetime.strptime(data['start_time'], '%H:%M:%S').time()
        except ValueError:
            t = datetime.strptime(data['start_time'], '%H:%M').time()

        try:
            booking = services.create_booking(
                user=request.user,
                court=court,
                selected_date=data['date'],
                start_time=t,
                notes=data.get('notes', ''),
            )
            messages.success(
                request,
                f'✅ Booking confirmed! {court} on {booking.date} at '
                f'{booking.start_time.strftime("%I:%M %p")}. '
                f'Please pay ₱{booking.price} on-site.'
            )
            return redirect('bookings:my_bookings')
        except ValidationError as e:
            messages.error(request, str(e))

    return render(request, 'bookings/booking_form.html', {
        'form':  form,
        'title': 'Book a Court',
        'price': __import__('django.conf', fromlist=['settings']).settings.BOOKING_PRICE,
    })


@login_required
def my_bookings_view(request):
    """Show logged-in user's booking history."""
    bookings = (
        Booking.objects
        .filter(user=request.user)
        .select_related('court')
        .order_by('-date', '-start_time')
    )
    return render(request, 'bookings/my_bookings.html', {'bookings': bookings})


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
    """Admin manually creates a booking for any user."""
    form = AdminBookingForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        data  = form.cleaned_data
        from datetime import time as dtime
        try:
            t = datetime.strptime(data['start_time'], '%H:%M:%S').time()
        except ValueError:
            t = datetime.strptime(data['start_time'], '%H:%M').time()

        try:
            booking = services.create_booking(
                user=data['user'],
                court=data['court'],
                selected_date=data['date'],
                start_time=t,
                created_by=request.user,
                notes=data.get('notes', ''),
            )
            messages.success(request, f'Booking created for {booking.user.full_name}.')
            return redirect('bookings:admin_list')
        except ValidationError as e:
            messages.error(request, str(e))

    return render(request, 'bookings/booking_form.html', {
        'form':  form,
        'title': 'Create Booking (Admin)',
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
    """Admin updates booking status (e.g. mark as completed/paid)."""
    booking = get_object_or_404(Booking, pk=pk)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Booking.Status.choices):
            booking.status = new_status
            booking.save(update_fields=['status'])
            messages.success(request, f'Booking status updated to {new_status}.')
        else:
            messages.error(request, 'Invalid status.')
        return redirect('bookings:admin_list')

    return render(request, 'bookings/admin_booking_status.html', {
        'booking':        booking,
        'status_choices': Booking.Status.choices,
    })