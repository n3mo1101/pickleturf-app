from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import InventoryItem, RentalRecord


# ── Stock Management ───────────────────────────────────────────────────────────

def adjust_stock(item, quantity, action='deduct'):
    """
    Adjust stock for an item.
    action: 'deduct' or 'add'
    """
    if action == 'deduct':
        if item.stock < quantity:
            raise ValidationError(
                f'Insufficient stock. Only {item.stock} unit(s) of '
                f'"{item.name}" available.'
            )
        item.stock -= quantity
    elif action == 'add':
        item.stock += quantity
    else:
        raise ValueError('action must be "deduct" or "add"')

    item.save(update_fields=['stock'])
    return item


# ── Rental Management ──────────────────────────────────────────────────────────

def create_rental(item, user, hours, handled_by=None):
    """
    Create a rental record and deduct stock.
    Raises ValidationError if item is not rentable or out of stock.
    """
    from inventory.models import InventoryItem

    if item.item_type not in (
        InventoryItem.ItemType.RENT,
        InventoryItem.ItemType.BOTH
    ):
        raise ValidationError(f'"{item.name}" is not available for rent.')

    if item.stock < 1:
        raise ValidationError(f'"{item.name}" is out of stock.')

    if not item.rent_price:
        raise ValidationError(f'"{item.name}" has no rental price set.')

    # Deduct stock
    adjust_stock(item, 1, action='deduct')

    rental = RentalRecord.objects.create(
        item=item,
        user=user,
        hours=hours,
        handled_by=handled_by,
        total_cost=item.rent_price * hours,
    )

    # Create transaction
    _create_rental_transaction(rental)
    return rental


def return_rental(rental, handled_by=None):
    """
    Mark rental as returned and restore stock.
    """
    if rental.status == RentalRecord.Status.RETURNED:
        raise ValidationError('This item has already been returned.')

    rental.status      = RentalRecord.Status.RETURNED
    rental.returned_at = timezone.now()
    if handled_by:
        rental.handled_by = handled_by
    rental.save(update_fields=['status', 'returned_at', 'handled_by'])

    # Restore stock
    adjust_stock(rental.item, 1, action='add')
    return rental


def record_sale(item, quantity, user, handled_by=None):
    """
    Record a sale and deduct stock.
    Raises ValidationError if item is not for sale or out of stock.
    """
    from inventory.models import InventoryItem

    if item.item_type not in (
        InventoryItem.ItemType.SALE,
        InventoryItem.ItemType.BOTH
    ):
        raise ValidationError(f'"{item.name}" is not available for sale.')

    if item.stock < quantity:
        raise ValidationError(
            f'Insufficient stock. Only {item.stock} unit(s) available.'
        )

    adjust_stock(item, quantity, action='deduct')
    _create_sale_transaction(item, quantity, user, handled_by)


def _create_rental_transaction(rental):
    """Create a pending transaction for a rental."""
    from transactions.models import Transaction
    Transaction.objects.create(
        user=rental.user,
        tx_type=Transaction.TxType.RENTAL,
        amount=rental.total_cost,
        rental=rental,
        description=(
            f'Rental – {rental.item.name} x {rental.hours} hour(s)'
        ),
        created_by=rental.handled_by,
    )


def _create_sale_transaction(item, quantity, user, handled_by=None):
    """Create a transaction for a sale."""
    from transactions.models import Transaction
    total = item.sale_price * quantity
    Transaction.objects.create(
        user=user,
        tx_type=Transaction.TxType.SALE,
        amount=total,
        description=f'Sale – {item.name} x {quantity}',
        created_by=handled_by,
    )