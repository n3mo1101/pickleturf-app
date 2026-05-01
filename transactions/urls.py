from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('',              views.transaction_list_view, name='list'),
    path('<int:pk>/pay/', views.mark_paid_view,        name='mark_paid'),
]