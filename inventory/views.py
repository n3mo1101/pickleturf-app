# inventory/views.py

import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import admin_or_staff_required
from .forms import (
    CategoryForm, InventoryItemForm,
    RentalCreateForm, StockAdjustForm,
)
from .models import Category, InventoryItem, RentalRecord, Sale
from . import services


# ── Customer Shop ──────────────────────────────────────────────────────────────

@login_required
def shop_view(request):
    items = InventoryItem.objects.filter(
        is_active=True
    ).select_related('category').order_by('category__name', 'name')

    category_filter = request.GET.get('category')
    type_filter     = request.GET.get('type')
    search_query    = request.GET.get('q', '').strip()

    if category_filter:
        items = items.filter(category_id=category_filter)
    if type_filter:
        items = items.filter(item_type=type_filter)
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    return render(request, 'inventory/shop.html', {
        'items':           items,
        'categories':      Category.objects.all().order_by('name'),
        'category_filter': category_filter,
        'type_filter':     type_filter,
        'search_query':    search_query,
        'type_choices':    InventoryItem.ItemType.choices,
    })


# ── Admin: POS ─────────────────────────────────────────────────────────────────

@admin_or_staff_required
def admin_pos_view(request):
    """
    POS terminal for recording sales.
    Shows all saleable items; admin enters quantities and checks out.
    """
    items = InventoryItem.objects.filter(
        is_active=True,
        item_type__in=[InventoryItem.ItemType.SALE, InventoryItem.ItemType.BOTH],
    ).select_related('category').order_by('category__name', 'name')

    category_filter = request.GET.get('category')
    search_query    = request.GET.get('q', '').strip()

    if category_filter:
        items = items.filter(category_id=category_filter)
    if search_query:
        items = items.filter(name__icontains=search_query)

    if request.method == 'POST':
        notes     = request.POST.get('notes', '')
        cart_items = []
        errors    = []

        # Collect non-zero quantities from POST
        for item in InventoryItem.objects.filter(
            is_active=True,
            item_type__in=[InventoryItem.ItemType.SALE, InventoryItem.ItemType.BOTH]
        ):
            qty_str = request.POST.get(f'qty_{item.pk}', '').strip()
            if not qty_str:
                continue
            try:
                qty = int(qty_str)
                if qty <= 0:
                    continue
                cart_items.append({'item': item, 'quantity': qty})
            except ValueError:
                errors.append(f'Invalid quantity for {item.name}.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect('inventory:admin_pos')

        if not cart_items:
            messages.warning(request, 'No items selected. Enter at least one quantity.')
            return redirect('inventory:admin_pos')

        try:
            sale = services.process_sale(
                cart_items=cart_items,
                created_by=request.user,
                notes=notes,
            )
            messages.success(
                request,
                f'✅ Sale #{sale.pk} processed. '
                f'Total: ₱{sale.total}. '
                f'{len(cart_items)} item type(s) sold.'
            )
            return redirect('inventory:admin_sale_detail', pk=sale.pk)
        except ValidationError as e:
            messages.error(request, e.message)

    return render(request, 'inventory/admin_pos.html', {
        'items':           items,
        'categories':      Category.objects.all().order_by('name'),
        'category_filter': category_filter,
        'search_query':    search_query,
    })


@admin_or_staff_required
def admin_sale_list_view(request):
    """Admin views all past sales."""
    sales = Sale.objects.prefetch_related(
        'items__item'
    ).select_related('created_by').order_by('-created_at')

    return render(request, 'inventory/admin_sale_list.html', {'sales': sales})


@admin_or_staff_required
def admin_sale_detail_view(request, pk):
    """Admin views details of a single sale."""
    sale = get_object_or_404(
        Sale.objects.prefetch_related('items__item').select_related('created_by'),
        pk=pk
    )
    return render(request, 'inventory/admin_sale_detail.html', {'sale': sale})


# ── Admin: Item CRUD ───────────────────────────────────────────────────────────

@admin_or_staff_required
def admin_item_list_view(request):
    items = InventoryItem.objects.select_related('category').order_by(
        'category__name', 'name'
    )

    category_filter = request.GET.get('category')
    type_filter     = request.GET.get('type')
    stock_filter    = request.GET.get('stock')
    search_query    = request.GET.get('q', '').strip()

    if category_filter:
        items = items.filter(category_id=category_filter)
    if type_filter:
        items = items.filter(item_type=type_filter)
    if stock_filter == 'low':
        items = items.filter(stock__lte=5)
    if stock_filter == 'out':
        items = items.filter(stock=0)
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    return render(request, 'inventory/admin_item_list.html', {
        'items':           items,
        'categories':      Category.objects.all(),
        'category_filter': category_filter,
        'type_filter':     type_filter,
        'stock_filter':    stock_filter,
        'search_query':    search_query,
        'type_choices':    InventoryItem.ItemType.choices,
        'low_stock_count': InventoryItem.objects.filter(
            stock__lte=5, is_active=True
        ).count(),
    })


@admin_or_staff_required
def admin_item_create_view(request):
    form = InventoryItemForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        messages.success(request, f'Item "{item.name}" created.')
        return redirect('inventory:admin_list')
    return render(request, 'inventory/item_form.html', {
        'form': form, 'title': 'Add Inventory Item',
    })


@admin_or_staff_required
def admin_item_edit_view(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    form = InventoryItemForm(
        request.POST or None, request.FILES or None, instance=item
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Item "{item.name}" updated.')
        return redirect('inventory:admin_list')
    return render(request, 'inventory/item_form.html', {
        'form': form, 'title': f'Edit – {item.name}', 'item': item,
    })


@admin_or_staff_required
def admin_item_delete_view(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        name = item.name
        item.delete()
        messages.success(request, f'Item "{name}" deleted.')
        return redirect('inventory:admin_list')
    return render(request, 'inventory/item_delete_confirm.html', {'item': item})


@admin_or_staff_required
def admin_item_detail_view(request, pk):
    item           = get_object_or_404(InventoryItem, pk=pk)
    active_rentals = RentalRecord.objects.filter(
        item=item, status=RentalRecord.Status.ACTIVE
    )
    recent_rentals = RentalRecord.objects.filter(
        item=item
    ).order_by('-rented_at')[:10]

    return render(request, 'inventory/admin_item_detail.html', {
        'item':           item,
        'active_rentals': active_rentals,
        'recent_rentals': recent_rentals,
    })


@admin_or_staff_required
def admin_stock_adjust_view(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    form = StockAdjustForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        try:
            services.adjust_stock(item, data['quantity'], data['action'])
            messages.success(
                request,
                f'Stock updated. New stock: {item.stock} unit(s).'
            )
        except ValidationError as e:
            messages.error(request, e.message)
        return redirect('inventory:admin_detail', pk=pk)

    return render(request, 'inventory/stock_adjust.html', {
        'form': form, 'item': item,
    })


# ── Admin: Rentals ─────────────────────────────────────────────────────────────

@admin_or_staff_required
def admin_rental_list_view(request):
    rentals = RentalRecord.objects.select_related(
        'item'
    ).order_by('-rented_at')

    status_filter = request.GET.get('status')
    search_query  = request.GET.get('q', '').strip()

    if status_filter:
        rentals = rentals.filter(status=status_filter)
    if search_query:
        rentals = rentals.filter(
            Q(renter_name__icontains=search_query) |
            Q(item__name__icontains=search_query) |
            Q(renter_contact__icontains=search_query)
        )

    return render(request, 'inventory/admin_rental_list.html', {
        'rentals':        rentals,
        'status_choices': RentalRecord.Status.choices,
        'status_filter':  status_filter,
        'search_query':   search_query,
    })


@admin_or_staff_required
def admin_rental_create_view(request, pk):
    """Record a new rental for a specific item."""
    item = get_object_or_404(InventoryItem, pk=pk)
    form = RentalCreateForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        try:
            rental = services.create_rental(
                item=item,
                renter_name=data['renter_name'],
                renter_contact=data.get('renter_contact', ''),
                hours=data['hours'],
                handled_by=request.user,
            )
            messages.success(
                request,
                f'Rental created for {rental.renter_name}. '
                f'Total: ₱{rental.total_cost}.'
            )
            return redirect('inventory:admin_rental_list')
        except ValidationError as e:
            messages.error(request, e.message)

    return render(request, 'inventory/rental_form.html', {
        'form': form, 'item': item,
    })


@admin_or_staff_required
def admin_rental_return_view(request, pk):
    rental = get_object_or_404(RentalRecord, pk=pk)

    if request.method == 'POST':
        try:
            services.return_rental(rental, handled_by=request.user)
            messages.success(
                request,
                f'"{rental.item.name}" returned by {rental.renter_name}. '
                f'Stock restored.'
            )
        except ValidationError as e:
            messages.error(request, e.message)
        return redirect('inventory:admin_rental_list')

    return render(request, 'inventory/rental_return_confirm.html', {
        'rental': rental,
    })


# ── Admin: Categories ──────────────────────────────────────────────────────────

@admin_or_staff_required
def admin_category_list_view(request):
    return render(request, 'inventory/admin_category_list.html', {
        'categories': Category.objects.all().order_by('name'),
    })


@admin_or_staff_required
def admin_category_create_view(request):
    form = CategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cat = form.save()
        messages.success(request, f'Category "{cat.name}" created.')
        return redirect('inventory:admin_categories')
    return render(request, 'inventory/category_form.html', {
        'form': form, 'title': 'Add Category',
    })


@admin_or_staff_required
def admin_category_edit_view(request, pk):
    cat  = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=cat)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Category "{cat.name}" updated.')
        return redirect('inventory:admin_categories')
    return render(request, 'inventory/category_form.html', {
        'form': form, 'title': f'Edit – {cat.name}',
    })