import csv
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import admin_or_staff_required
from bookings.models import Booking
from inventory.models import InventoryItem, RentalRecord
from openplay.models import OpenPlayParticipant, OpenPlaySession
from transactions.models import Transaction


# ── Helpers ────────────────────────────────────────────────────────────────────

def _revenue_queryset():
    """Base queryset — only paid or pending (on-site) transactions count."""
    return Transaction.objects.filter(
        payment_status__in=[
            Transaction.PaymentStatus.PENDING,
            Transaction.PaymentStatus.PAID,
        ]
    )


def _daily_revenue_last_30():
    """
    Returns list of (date_str, total) for last 30 days.
    Fills in 0 for days with no transactions.
    """
    today   = date.today()
    start   = today - timedelta(days=29)

    rows = (
        _revenue_queryset()
        .filter(created_at__date__gte=start)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )

    # Build a lookup dict
    lookup = {r['day']: float(r['total']) for r in rows}

    labels, data = [], []
    for i in range(30):
        d = start + timedelta(days=i)
        labels.append(d.strftime('%b %d'))
        data.append(lookup.get(d, 0))

    return labels, data


def _monthly_revenue_this_year():
    """Returns list of 12 monthly totals for the current year."""
    year = date.today().year

    rows = (
        _revenue_queryset()
        .filter(created_at__year=year)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )

    lookup = {r['month'].month: float(r['total']) for r in rows}

    months = ['Jan','Feb','Mar','Apr','May','Jun',
              'Jul','Aug','Sep','Oct','Nov','Dec']
    data   = [lookup.get(m, 0) for m in range(1, 13)]

    return months, data


def _revenue_by_type():
    """Returns revenue broken down by transaction type."""
    rows = (
        _revenue_queryset()
        .values('tx_type')
        .annotate(total=Sum('amount'))
    )

    type_map = dict(Transaction.TxType.choices)
    labels   = [type_map.get(r['tx_type'], r['tx_type']) for r in rows]
    data     = [float(r['total']) for r in rows]

    return labels, data


def _court_utilization():
    """Returns booking counts per court for the current month."""
    today = date.today()

    from courts.models import Court
    courts = Court.objects.filter(is_active=True).order_by('name')

    rows = (
        Booking.objects
        .filter(
            date__year=today.year,
            date__month=today.month,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED]
        )
        .values('court__name')
        .annotate(count=Count('id'))
    )

    lookup = {r['court__name']: r['count'] for r in rows}

    labels = [c.name for c in courts]
    data   = [lookup.get(c.name, 0) for c in courts]

    return labels, data


def _bookings_by_day_of_week():
    """Returns booking counts grouped by day of week (Mon–Sun)."""
    from django.db.models.functions import ExtractWeekDay

    rows = (
        Booking.objects
        .filter(status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED])
        .annotate(weekday=ExtractWeekDay('date'))
        .values('weekday')
        .annotate(count=Count('id'))
        .order_by('weekday')
    )

    # Django: 1=Sunday … 7=Saturday
    day_map = {1:'Sun', 2:'Mon', 3:'Tue', 4:'Wed', 5:'Thu', 6:'Fri', 7:'Sat'}
    lookup  = {r['weekday']: r['count'] for r in rows}

    labels = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    data   = [
        lookup.get(2, 0),  # Mon
        lookup.get(3, 0),
        lookup.get(4, 0),
        lookup.get(5, 0),
        lookup.get(6, 0),
        lookup.get(7, 0),
        lookup.get(1, 0),  # Sun
    ]

    return labels, data


# ── Main Dashboard View ────────────────────────────────────────────────────────

@admin_or_staff_required
def index(request):
    today = date.today()
    now   = timezone.now()

    # ── Summary Cards ──────────────────────────────────────────────
    today_revenue = (
        _revenue_queryset()
        .filter(created_at__date=today)
        .aggregate(total=Sum('amount'))['total'] or 0
    )

    month_revenue = (
        _revenue_queryset()
        .filter(
            created_at__year=today.year,
            created_at__month=today.month
        )
        .aggregate(total=Sum('amount'))['total'] or 0
    )

    bookings_today = Booking.objects.filter(
        date=today,
        status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED]
    ).count()

    active_rentals = RentalRecord.objects.filter(
        status=RentalRecord.Status.ACTIVE
    ).count()

    low_stock_items = InventoryItem.objects.filter(
        stock__lte=5, is_active=True
    ).count()

    pending_openplay = OpenPlayParticipant.objects.filter(
        status=OpenPlayParticipant.Status.PENDING
    ).count()

    # ── Chart Data ─────────────────────────────────────────────────
    daily_labels,   daily_data   = _daily_revenue_last_30()
    monthly_labels, monthly_data = _monthly_revenue_this_year()
    type_labels,    type_data    = _revenue_by_type()
    court_labels,   court_data   = _court_utilization()
    dow_labels,     dow_data     = _bookings_by_day_of_week()

    # ── Recent Activity ────────────────────────────────────────────
    recent_transactions = (
        Transaction.objects
        .select_related('user')
        .order_by('-created_at')[:10]
    )

    todays_bookings = (
        Booking.objects
        .filter(
            date=today,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED]
        )
        .select_related('court', 'user')
        .order_by('start_time')
    )

    upcoming_sessions = (
        OpenPlaySession.objects
        .filter(
            date__gte=today,
            status__in=[
                OpenPlaySession.Status.OPEN,
                OpenPlaySession.Status.FULL,
            ]
        )
        .order_by('date', 'start_time')[:3]
    )

    context = {
        # Cards
        'today_revenue':    today_revenue,
        'month_revenue':    month_revenue,
        'bookings_today':   bookings_today,
        'active_rentals':   active_rentals,
        'low_stock_items':  low_stock_items,
        'pending_openplay': pending_openplay,

        # Charts (passed as Python lists — serialized in template)
        'daily_labels':   daily_labels,
        'daily_data':     daily_data,
        'monthly_labels': monthly_labels,
        'monthly_data':   monthly_data,
        'type_labels':    type_labels,
        'type_data':      type_data,
        'court_labels':   court_labels,
        'court_data':     court_data,
        'dow_labels':     dow_labels,
        'dow_data':       dow_data,

        # Tables
        'recent_transactions': recent_transactions,
        'todays_bookings':     todays_bookings,
        'upcoming_sessions':   upcoming_sessions,

        # Meta
        'today': today,
    }

    return render(request, 'dashboard/index.html', context)


# ── CSV Exports ────────────────────────────────────────────────────────────────

@admin_or_staff_required
def export_transactions_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="transactions_{date.today()}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Date', 'Type', 'Amount',
        'Payment Status', 'Description', 'Created By',
    ])

    for tx in Transaction.objects.select_related('user', 'created_by').order_by('-created_at'):
        writer.writerow([
            tx.pk,
            tx.created_at.strftime('%Y-%m-%d %H:%M'),
            tx.get_tx_type_display(),
            tx.amount,
            tx.get_payment_status_display(),
            tx.description,
            tx.created_by.email if tx.created_by else '—',
        ])

    return response


@admin_or_staff_required
def export_bookings_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="bookings_{date.today()}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Customer', 'Email', 'Court',
        'Date', 'Start Time', 'End Time',
        'Price', 'Status', 'Booked At',
    ])

    for b in Booking.objects.select_related('court', 'user').order_by('-date', '-start_time'):
        writer.writerow([
            b.pk,
            b.user.full_name,
            b.user.email,
            b.court.name,
            b.date.strftime('%Y-%m-%d'),
            b.start_time.strftime('%H:%M'),
            b.end_time.strftime('%H:%M'),
            b.price,
            b.get_status_display(),
            b.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response


@admin_or_staff_required
def export_rentals_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="rentals_{date.today()}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Item', 'Renter Name', 'Contact',
        'Hours', 'Total Cost', 'Status',
        'Rented At', 'Returned At',
    ])

    for r in RentalRecord.objects.select_related('item').order_by('-rented_at'):
        writer.writerow([
            r.pk,
            r.item.name,
            r.renter_name,
            r.renter_contact or '—',
            r.hours,
            r.total_cost,
            r.get_status_display(),
            r.rented_at.strftime('%Y-%m-%d %H:%M'),
            r.returned_at.strftime('%Y-%m-%d %H:%M') if r.returned_at else '—',
        ])

    return response