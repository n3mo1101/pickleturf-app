from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('',                    views.index,                  name='index'),
    path('export/transactions/', views.export_transactions_csv, name='export_transactions'),
    path('export/bookings/',     views.export_bookings_csv,    name='export_bookings'),
    path('export/rentals/',      views.export_rentals_csv,     name='export_rentals'),
]