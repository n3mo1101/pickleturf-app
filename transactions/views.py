from django.shortcuts import render
from accounts.decorators import admin_or_staff_required
from .models import Transaction


@admin_or_staff_required
def transaction_list_view(request):
    transactions = Transaction.objects.select_related(
        'user', 'created_by'
    ).order_by('-created_at')

    type_filter   = request.GET.get('type')
    status_filter = request.GET.get('status')

    if type_filter:
        transactions = transactions.filter(tx_type=type_filter)
    if status_filter:
        transactions = transactions.filter(payment_status=status_filter)

    return render(request, 'transactions/list.html', {
        'transactions':   transactions,
        'type_choices':   Transaction.TxType.choices,
        'status_choices': Transaction.PaymentStatus.choices,
        'type_filter':    type_filter,
        'status_filter':  status_filter,
    })