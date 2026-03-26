from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.office_dashboard, name='office_dashboard'),
    path('complaint/<int:pk>/', views.office_complaint_detail, name='office_complaint_detail'),
]
