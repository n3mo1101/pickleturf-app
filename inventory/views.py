from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import admin_or_staff_required
from .forms import (
    CategoryForm, InventoryItemForm,
    RentalCreateForm, SaleCreateForm, StockAdjustForm,
)
from .models import Category, InventoryItem, RentalRecord
from . import services


# ── Customer Shop View ─────────────────────────────────────────────────────────

@login_required
def shop_view(request):
    """Public shop — customers browse items (no purchasing)."""
    items = InventoryItem.objects.filter(
        is_active=True
    ).select_related('category').order_by('category__name', 'name')

    # Filters
    category_filter  = request.GET.get('category')
    type_filter      = request.GET.get('type')
    search_query     = request.GET.get('q', '').strip()

    if category_filter:
        items = items.filter(category_id=category_filter)
    if type_filter:
        items = items.filter(item_type=type_filter)
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    categories = Category.objects.all().order_by('name')

    return render(request, 'inventory/shop.html', {
        'items':           items,
        'categories':      categories,
        'category_filter': category_filter,
        'type_filter':     type_filter,
        'search_query':    search_query,
        'type_choices':    InventoryItem.ItemType.choices,
    })


# ── Admin: Item CRUD ───────────────────────────────────────────────────────────

@admin_or_staff_required
def admin_item_list_view(request):
    """Admin sees all inventory items with filters."""
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
    """Admin creates a new inventory item."""
    form = InventoryItemForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        item = form.save()
        messages.success(request, f'Item "{item.name}" created.')
        return redirect('inventory:admin_list')

    return render(request, 'inventory/item_form.html', {
        'form':  form,
        'title': 'Add Inventory Item',
    })


@admin_or_staff_required
def admin_item_edit_view(request, pk):
    """Admin edits an existing inventory item."""
    item = get_object_or_404(InventoryItem, pk=pk)
    form = InventoryItemForm(
        request.POST or None,
        request.FILES or None,
        instance=item
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Item "{item.name}" updated.')
        return redirect('inventory:admin_list')

    return render(request, 'inventory/item_form.html', {
        'form':  form,
        'title': f'Edit – {item.name}',
        'item':  item,
    })


@admin_or_staff_required
def admin_item_delete_view(request, pk):
    """Admin deletes an inventory item."""
    item = get_object_or_404(InventoryItem, pk=pk)

    if request.method == 'POST':
        name = item.name
        item.delete()
        messages.success(request, f'Item "{name}" deleted.')
        return redirect('inventory:admin_list')

    return render(request, 'inventory/item_delete_confirm.html', {'item': item})


@admin_or_staff_required
def admin_item_detail_view(request, pk):
    """Admin views item details, stock history, and active rentals."""
    item           = get_object_or_404(InventoryItem, pk=pk)
    active_rentals = RentalRecord.objects.filter(
        item=item,
        status=RentalRecord.Status.ACTIVE
    ).select_related('user')
    recent_rentals = RentalRecord.objects.filter(
        item=item
    ).select_related('user').order_by('-rented_at')[:10]

    return render(request, 'inventory/admin_item_detail.html', {
        'item':           item,
        'active_rentals': active_rentals,
        'recent_rentals': recent_rentals,
    })


# ── Admin: Stock Adjustment ────────────────────────────────────────────────────

@admin_or_staff_required
def admin_stock_adjust_view(request, pk):
    """Admin manually adjusts item stock."""
    item = get_object_or_404(InventoryItem, pk=pk)
    form = StockAdjustForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        try:
            services.adjust_stock(item, data['quantity'], data['action'])
            messages.success(
                request,
                f'Stock {"added" if data["action"] == "add" else "deducted"}: '
                f'{data["quantity"]} unit(s). '
                f'New stock: {item.stock}.'
            )
        except ValidationError as e:
            messages.error(request, e.message)
        return redirect('inventory:admin_detail', pk=pk)

    return render(request, 'inventory/stock_adjust.html', {
        'form': form,
        'item': item,
    })


# ── Admin: Rental Management ───────────────────────────────────────────────────

@admin_or_staff_required
def admin_rental_list_view(request):
    """Admin views all rental records."""
    rentals = RentalRecord.objects.select_related(
        'item', 'user'
    ).order_by('-rented_at')

    status_filter = request.GET.get('status')
    if status_filter:
        rentals = rentals.filter(status=status_filter)

    return render(request, 'inventory/admin_rental_list.html', {
        'rentals':        rentals,
        'status_choices': RentalRecord.Status.choices,
        'status_filter':  status_filter,
    })


@admin_or_staff_required
def admin_rental_create_view(request, pk):
    """Admin records a new rental for an item."""
    item = get_object_or_404(InventoryItem, pk=pk)
    form = RentalCreateForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        try:
            rental = services.create_rental(
                item=item,
                user=data['user'],
                hours=data['hours'],
                handled_by=request.user,
            )
            messages.success(
                request,
                f'Rental created for {data["user"].full_name}. '
                f'Total: ₱{rental.total_cost}.'
            )
            return redirect('inventory:admin_rental_list')
        except ValidationError as e:
            messages.error(request, e.message)

    return render(request, 'inventory/rental_form.html', {
        'form': form,
        'item': item,
    })


@admin_or_staff_required
def admin_rental_return_view(request, pk):
    """Admin marks a rental as returned."""
    rental = get_object_or_404(RentalRecord, pk=pk)

    if request.method == 'POST':
        try:
            services.return_rental(rental, handled_by=request.user)
            messages.success(
                request,
                f'"{rental.item.name}" returned by {rental.user.full_name}. '
                f'Stock restored.'
            )
        except ValidationError as e:
            messages.error(request, e.message)
        return redirect('inventory:admin_rental_list')

    return render(request, 'inventory/rental_return_confirm.html', {
        'rental': rental,
    })


# ── Admin: Sales ───────────────────────────────────────────────────────────────

@admin_or_staff_required
def admin_sale_create_view(request, pk):
    """Admin records a sale for an item."""
    item = get_object_or_404(InventoryItem, pk=pk)
    form = SaleCreateForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        try:
            services.record_sale(
                item=item,
                quantity=data['quantity'],
                user=data.get('user'),
                handled_by=request.user,
            )
            messages.success(
                request,
                f'Sale recorded: {data["quantity"]} x "{item.name}". '
                f'Total: ₱{item.sale_price * data["quantity"]}.'
            )
            return redirect('inventory:admin_detail', pk=pk)
        except ValidationError as e:
            messages.error(request, e.message)

    return render(request, 'inventory/sale_form.html', {
        'form': form,
        'item': item,
    })


# ── Admin: Category CRUD ───────────────────────────────────────────────────────

@admin_or_staff_required
def admin_category_list_view(request):
    categories = Category.objects.all().order_by('name')
    return render(request, 'inventory/admin_category_list.html', {
        'categories': categories,
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