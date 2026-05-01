# inventory/urls.py

from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Customer
    path('shop/',  views.shop_view, name='shop'),

    # Admin — Items
    path('admin/',                       views.admin_item_list_view,   name='admin_list'),
    path('admin/new/',                   views.admin_item_create_view, name='admin_create'),
    path('admin/<int:pk>/',              views.admin_item_detail_view, name='admin_detail'),
    path('admin/<int:pk>/edit/',         views.admin_item_edit_view,   name='admin_edit'),
    path('admin/<int:pk>/delete/',       views.admin_item_delete_view, name='admin_delete'),
    path('admin/<int:pk>/stock/',        views.admin_stock_adjust_view,name='admin_stock'),

    # Admin — Rentals
    path('admin/rentals/',               views.admin_rental_list_view,   name='admin_rental_list'),
    path('admin/<int:pk>/rent/',         views.admin_rental_create_view, name='admin_rent'),
    path('admin/rentals/<int:pk>/return/', views.admin_rental_return_view, name='admin_return'),

    # Admin — Sales
    path('admin/<int:pk>/sell/',         views.admin_sale_create_view,   name='admin_sell'),

    # Admin — Categories
    path('admin/categories/',            views.admin_category_list_view,   name='admin_categories'),
    path('admin/categories/new/',        views.admin_category_create_view, name='admin_category_create'),
    path('admin/categories/<int:pk>/edit/', views.admin_category_edit_view, name='admin_category_edit'),
]