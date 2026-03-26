from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('guidelines/', views.complaint_guidelines, name='complaint_guidelines'),
    path('help/', views.help_center, name='help_center'),
    path('complaint/file/', views.complaint_create, name='complaint_file'),
    path('complaint/track/success/<str:tracking_number>/', views.complaint_track_success, name='complaint_track_success'),
    path('complaint/track/', views.complaint_track, name='complaint_track'),
    path('complaints/', views.citizen_complaints_list, name='citizen_complaints_list'),
    path('complaint-detail/<int:pk>/', views.complaint_detail, name='complaint_detail'),
    path('citizen/dashboard/', views.citizen_dashboard, name='citizen_dashboard'),
]
