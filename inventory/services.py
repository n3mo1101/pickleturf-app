from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import InventoryItem, RentalRecord, Sale, SaleItem


# ── Stock Adjustment ───────────────────────────────────────────────────────────

def adjust_stock(item, quantity, action='deduct'):
    """Manually adjust stock. action: 'add' or 'deduct'."""
    if action == 'deduct':
        if item.stock < quantity:
            raise ValidationError(
                f'Insufficient stock. Only {item.stock} '
                f'unit(s) of "{item.name}" available.'
            )
        item.stock -= quantity
    elif action == 'add':
        item.stock += quantity
    else:
        raise ValueError('action must be "add" or "deduct"')

    item.save(update_fields=['stock'])
    return item


# ── POS Sale ───────────────────────────────────────────────────────────────────

def process_sale(cart_items, created_by=None, notes=''):
    """
    Process a POS sale from a list of cart items.

    cart_items: list of dicts → [{'item': InventoryItem, 'quantity': int}, ...]

    Steps:
      1. Validate all stock levels before touching anything
      2. Create Sale header
      3. Create SaleItem line items + deduct stock
      4. Compute total
      5. Create one Transaction record
    """
    if not cart_items:
        raise ValidationError('Cart is empty.')

    # ── Step 1: Validate everything first ─────────────────────────
    for entry in cart_items:
        item = entry['item']
        qty  = entry['quantity']

        if item.item_type not in (
            InventoryItem.ItemType.SALE,
            InventoryItem.ItemType.BOTH
        ):
            raise ValidationError(f'"{item.name}" is not available for sale.')

        if not item.sale_price:
            raise ValidationError(f'"{item.name}" has no sale price set.')

        if item.stock < qty:
            raise ValidationError(
                f'Insufficient stock for "{item.name}". '
                f'Available: {item.stock}, requested: {qty}.'
            )

    # ── Step 2: Create Sale header ─────────────────────────────────
    sale = Sale.objects.create(created_by=created_by, notes=notes)

    # ── Step 3: Create line items + deduct stock ───────────────────
    for entry in cart_items:
        item = entry['item']
        qty  = entry['quantity']

        SaleItem.objects.create(
            sale=sale,
            item=item,
            quantity=qty,
            unit_price=item.sale_price,
        )
        item.deduct_stock(qty)

    # ── Step 4: Compute total ──────────────────────────────────────
    sale.compute_total()

    # ── Step 5: Create transaction ─────────────────────────────────
    _create_sale_transaction(sale, created_by)

    return sale


def _create_sale_transaction(sale, created_by=None):
    """Log one Transaction record for the entire sale."""
    from transactions.models import Transaction

    item_summary = ', '.join(
        f'{si.item.name} x{si.quantity}'
        for si in sale.items.select_related('item')
    )
    Transaction.objects.create(
        user=None,                         # no user linked for walk-in sales
        tx_type=Transaction.TxType.SALE,
        amount=sale.total,
        sale=sale,
        payment_status=Transaction.PaymentStatus.PAID,
        description=f'POS Sale – {item_summary}',
        created_by=created_by,
    )


# ── Rentals ────────────────────────────────────────────────────────────────────

def create_rental(item, renter_name, hours, renter_contact='', handled_by=None):
    """
    Create a rental record and deduct stock.
    No user account needed — just name + optional contact.
    """
    if item.item_type not in (
        InventoryItem.ItemType.RENT,
        InventoryItem.ItemType.BOTH
    ):
        raise ValidationError(f'"{item.name}" is not available for rent.')

    if item.stock < 1:
        raise ValidationError(f'"{item.name}" is out of stock.')

    if not item.rent_price:
        raise ValidationError(f'"{item.name}" has no rental price set.')

    item.deduct_stock(1)

    rental = RentalRecord.objects.create(
        item=item,
        renter_name=renter_name.strip(),
        renter_contact=renter_contact.strip(),
        hours=hours,
        handled_by=handled_by,
    )

    _create_rental_transaction(rental, handled_by)
    return rental


def return_rental(rental, handled_by=None):
    """Mark rental returned and restore stock."""
    if rental.status == RentalRecord.Status.RETURNED:
        raise ValidationError('This item has already been returned.')

    rental.status      = RentalRecord.Status.RETURNED
    rental.returned_at = timezone.now()
    if handled_by:
        rental.handled_by = handled_by
    rental.save(update_fields=['status', 'returned_at', 'handled_by'])

    rental.item.add_stock(1)
    return rental


def _create_rental_transaction(rental, created_by=None):
    """Log a Transaction for a rental."""
    from transactions.models import Transaction
    Transaction.objects.create(
        user=None,
        tx_type=Transaction.TxType.RENTAL,
        amount=rental.total_cost,
        rental=rental,
        payment_status=Transaction.PaymentStatus.PAID,
        description=(
            f'Rental – {rental.item.name} x {rental.hours}h '
            f'({rental.renter_name})'
        ),
        created_by=created_by,
    )