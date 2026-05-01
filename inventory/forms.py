from django import forms
from .models import Category, InventoryItem, RentalRecord


class CategoryForm(forms.ModelForm):
    class Meta:
        model  = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Paddles, Balls, Shoes',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
            }),
        }


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model  = InventoryItem
        fields = [
            'name', 'category', 'description',
            'item_type', 'sale_price', 'rent_price',
            'stock', 'image', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Item name',
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
            }),
            'item_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_item_type',
            }),
            'sale_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0, 'step': '0.01',
                'placeholder': '0.00',
            }),
            'rent_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0, 'step': '0.01',
                'placeholder': '0.00 per hour',
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0,
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean(self):
        cleaned   = super().clean()
        item_type = cleaned.get('item_type')
        sale_price = cleaned.get('sale_price')
        rent_price = cleaned.get('rent_price')

        if item_type in (
            InventoryItem.ItemType.SALE,
            InventoryItem.ItemType.BOTH
        ) and not sale_price:
            self.add_error('sale_price', 'Sale price is required.')

        if item_type in (
            InventoryItem.ItemType.RENT,
            InventoryItem.ItemType.BOTH
        ) and not rent_price:
            self.add_error('rent_price', 'Rent price is required.')

        return cleaned


class StockAdjustForm(forms.Form):
    """Admin manually adjusts stock level."""
    ACTION_CHOICES = [
        ('add',    'Add Stock'),
        ('deduct', 'Deduct Stock'),
    ]
    action   = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'min': 1,
        }),
    )
    reason = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Reason for adjustment (optional)',
        }),
    )


class RentalCreateForm(forms.Form):
    """Admin records a new rental transaction."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Customer',
    )
    hours = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'min': 1,
        }),
        label='Rental Duration (hours)',
    )

    def __init__(self, *args, **kwargs):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = (
            User.objects.filter(is_active=True).order_by('email')
        )


class SaleCreateForm(forms.Form):
    """Admin records a sale transaction."""
    from django.contrib.auth import get_user_model

    user = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Customer',
        required=False,
        help_text='Leave blank for walk-in customers.',
    )
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'min': 1,
        }),
    )

    def __init__(self, *args, **kwargs):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = (
            User.objects.filter(is_active=True).order_by('email')
        )