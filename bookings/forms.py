from django import forms
from django.conf import settings
from datetime import date
from courts.models import Court
from .services import get_time_slots


class BookingForm(forms.Form):
    """Used by customers to make a booking."""
    court = forms.ModelChoiceField(
        queryset=Court.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='Select a court',
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': date.today().isoformat(),
        }),
    )
    start_time = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate time slot choices dynamically
        slots = get_time_slots()
        self.fields['start_time'].choices = [
            (t.strftime('%H:%M:%S'), label) for t, label in slots
        ]

    def clean_date(self):
        selected = self.cleaned_data['date']
        if selected < date.today():
            raise forms.ValidationError('Please select a future date.')
        return selected


class AdminBookingForm(forms.Form):
    """Extended form for admin/staff — can book for any user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = forms.ModelChoiceField(
        queryset=None,  # set in __init__
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Customer',
    )
    court = forms.ModelChoiceField(
        queryset=Court.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': date.today().isoformat(),
        }),
    )
    start_time = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )

    def __init__(self, *args, **kwargs):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(is_active=True).order_by('email')
        slots = get_time_slots()
        self.fields['start_time'].choices = [
            (t.strftime('%H:%M:%S'), label) for t, label in slots
        ]