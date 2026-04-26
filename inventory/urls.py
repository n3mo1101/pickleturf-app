from django.urls import path
from django.views.generic import TemplateView

app_name = 'inventory'

urlpatterns = [
    path('shop/', TemplateView.as_view(template_name='coming_soon.html'), name='shop'),
]