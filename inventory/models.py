from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Category(models.Model):
    name        = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class InventoryItem(models.Model):

    class ItemType(models.TextChoices):
        SALE = 'sale', 'For Sale'
        RENT = 'rent', 'For Rent'
        BOTH = 'both', 'Sale & Rent'

    category     = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='items'
    )
    name         = models.CharField(max_length=100)
    description  = models.TextField(blank=True)
    item_type    = models.CharField(
        max_length=10, choices=ItemType.choices, default=ItemType.SALE
    )
    sale_price   = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    rent_price   = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text='Price per hour'
    )
    stock        = models.PositiveIntegerField(default=0)
    image        = models.ImageField(upload_to='inventory/', blank=True, null=True)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        indexes  = [
            models.Index(fields=['item_type', 'is_active']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_item_type_display()})'

    def clean(self):
        if self.item_type in (self.ItemType.SALE, self.ItemType.BOTH):
            if self.sale_price is None:
                raise ValidationError('Sale price is required for sale items.')
        if self.item_type in (self.ItemType.RENT, self.ItemType.BOTH):
            if self.rent_price is None:
                raise ValidationError('Rent price is required for rent items.')

    @property
    def in_stock(self):
        return self.stock > 0

    def deduct_stock(self, qty=1):
        if self.stock < qty:
            raise ValidationError(f'Insufficient stock for {self.name}.')
        self.stock -= qty
        self.save(update_fields=['stock'])

    def add_stock(self, qty=1):
        self.stock += qty
        self.save(update_fields=['stock'])


class RentalRecord(models.Model):

    class Status(models.TextChoices):
        ACTIVE   = 'active',   'Active'
        RETURNED = 'returned', 'Returned'
        OVERDUE  = 'overdue',  'Overdue'

    item        = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='rentals'
    )
    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='rentals'
    )
    rented_at   = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    hours       = models.PositiveIntegerField(default=1)
    total_cost  = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status      = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    handled_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rentals_handled'
    )

    class Meta:
        ordering = ['-rented_at']
        indexes  = [models.Index(fields=['status', 'rented_at'])]

    def __str__(self):
        return f'{self.item} rented by {self.user} [{self.status}]'

    def save(self, *args, **kwargs):
        # Auto-calculate cost
        if self.item.rent_price and self.hours:
            self.total_cost = self.item.rent_price * self.hours
        super().save(*args, **kwargs)