from datetime import date
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages

from accounts.decorators import admin_or_staff_required
from bookings.models import Booking
from .models import Transaction


@admin_or_staff_required
def transaction_list_view(request):
    """
    Admin transaction history with:
    - Date range filter
    - Type and status filters
    - Running total of filtered results
    - Pagination (20 per page)
    """
    transactions = Transaction.objects.select_related(
        'user', 'created_by'
    ).order_by('-created_at')

    # ── Filters ────────────────────────────────────────────────────
    type_filter   = request.GET.get('type', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_from     = request.GET.get('date_from', '').strip()
    date_to       = request.GET.get('date_to', '').strip()

    if type_filter:
        transactions = transactions.filter(tx_type=type_filter)
    if status_filter:
        transactions = transactions.filter(payment_status=status_filter)
    if date_from:
        try:
            transactions = transactions.filter(
                created_at__date__gte=date_from
            )
        except ValueError:
            pass
    if date_to:
        try:
            transactions = transactions.filter(
                created_at__date__lte=date_to
            )
        except ValueError:
            pass

    # ── Running Total of Filtered Results ─────────────────────────
    filtered_total = transactions.aggregate(
        total=Sum('amount'),
        count=Count('id'),
    )
    total_amount = filtered_total['total'] or 0
    total_count  = filtered_total['count'] or 0

    # ── Pagination ─────────────────────────────────────────────────
    paginator    = Paginator(transactions, 20)
    page         = request.GET.get('page', 1)
    transactions = paginator.get_page(page)

    # Build query string for pagination links (preserve filters)
    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = query_params.urlencode()

    return render(request, 'transactions/list.html', {
        'transactions':   transactions,
        'type_choices':   Transaction.TxType.choices,
        'status_choices': Transaction.PaymentStatus.choices,
        'type_filter':    type_filter,
        'status_filter':  status_filter,
        'date_from':      date_from,
        'date_to':        date_to,
        'total_amount':   total_amount,
        'total_count':    total_count,
        'query_string':   query_string,
    })


@admin_or_staff_required
def mark_paid_view(request, pk):
    """
    Mark a transaction as Paid.
    If linked to a booking, also marks booking as Completed.
    """
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == 'POST':
        transaction.payment_status = Transaction.PaymentStatus.PAID
        transaction.save(update_fields=['payment_status'])

        # If linked to a booking, mark it completed
        if transaction.booking:
            transaction.booking.status = Booking.Status.COMPLETED
            transaction.booking.save(update_fields=['status'])
            messages.success(
                request,
                f'Transaction #{pk} marked as paid. '
                f'Booking #{transaction.booking.pk} marked as completed.'
            )
        else:
            messages.success(
                request,
                f'Transaction #{pk} marked as paid.'
            )

    # Preserve filters when redirecting back
    redirect_url = request.POST.get('next', 'transactions:list')
    return redirect('transactions:list')