from django.contrib import admin
from .models import Category, InventoryItem, RentalRecord

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('name',)
    search_fields = ('name',)

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display  = ('name', 'category', 'item_type', 'sale_price', 'rent_price', 'stock', 'is_active')
    list_filter   = ('item_type', 'is_active', 'category')
    search_fields = ('name',)

@admin.register(RentalRecord)
class RentalRecordAdmin(admin.ModelAdmin):
    list_display  = ('item', 'user', 'rented_at', 'hours', 'total_cost', 'status')
    list_filter   = ('status',)
    search_fields = ('user__email', 'item__name')