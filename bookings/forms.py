from django import forms
from datetime import date
from courts.models import Court
from .services import get_time_slots, get_availability


class BookingForm(forms.Form):
    """
    Step 1: court + date selection.
    Step 2: available slot checkboxes appear.
    """
    court = forms.ModelChoiceField(
        queryset=Court.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_court',
        }),
        empty_label='— Select a Court —',
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': date.today().isoformat(),
            'id': 'id_date',
        }),
    )
    time_slots = forms.MultipleChoiceField(
        required=False,   # validated manually in view
        widget=forms.CheckboxSelectMultiple(),
        choices=[],       # populated dynamically
        label='Available Time Slots',
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )

    def __init__(self, *args, available_slots=None, **kwargs):
        super().__init__(*args, **kwargs)
        if available_slots:
            self.fields['time_slots'].choices = available_slots
        else:
            # Hide slot field until court+date are chosen
            self.fields['time_slots'].widget = forms.HiddenInput()

    def clean_date(self):
        selected = self.cleaned_data['date']
        if selected < date.today():
            raise forms.ValidationError('Please select today or a future date.')
        return selected


class AdminBookingForm(forms.Form):
    """Admin version — can assign booking to any user."""

    user = forms.ModelChoiceField(
        queryset=None,
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
    time_slots = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        choices=[],
        label='Available Time Slots',
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )

    def __init__(self, *args, available_slots=None, **kwargs):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = (
            User.objects.filter(is_active=True).order_by('email')
        )
        if available_slots:
            self.fields['time_slots'].choices = available_slots
        else:
            self.fields['time_slots'].widget = forms.HiddenInput()

    def clean_date(self):
        selected = self.cleaned_data['date']
        if selected < __import__('datetime').date.today():
            raise forms.ValidationError('Please select today or a future date.')
        return selected