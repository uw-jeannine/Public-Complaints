from django.urls import path
from . import views 

urlpatterns = [
    path('administrator/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('administrator/offices/', views.office_list, name='office_list'),
    path('administrator/offices/add/', views.office_create, name='office_create'),
    path('administrator/offices/<int:pk>/edit/', views.office_update, name='office_update'),
    path('administrator/offices/<int:pk>/delete/', views.office_delete, name='office_delete'),
    # Office User accounts
    path('administrator/users/', views.office_user_list, name='office_user_list'),
    path('administrator/users/create/', views.office_user_create, name='office_user_create'),
    path('administrator/users/<int:pk>/', views.admin_user_detail, name='admin_user_detail'),
    path('administrator/users/<int:pk>/edit/', views.admin_user_update, name='admin_user_update'),
    path('administrator/users/<int:pk>/password-reset/', views.admin_user_password_reset, name='admin_user_password_reset'),
    path('administrator/users/<int:pk>/delete/', views.admin_user_delete, name='admin_user_delete'),
    # Complaint Category management
    path('administrator/categories/', views.category_list, name='category_list'),
    path('administrator/categories/add/', views.category_create, name='category_create'),
    path('administrator/categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('administrator/categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    # Complaints review
    path('administrator/complaints/', views.admin_complaints_list, name='admin_complaints_list'),
    path('administrator/complaints/<int:pk>/', views.admin_complaint_detail, name='admin_complaint_detail'),
    path('administrator/reports/', views.admin_reports, name='admin_reports'),
]