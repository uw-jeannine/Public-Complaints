from django.urls import path
from . import views

urlpatterns = [
    path('sign-up/', views.sign_up, name='sign-up'),
    path('sign-in/', views.sign_in, name='sign-in'),
    path('logout/', views.sign_out, name='logout'),
    path('ajax/get-locations/', views.get_locations, name='get_locations'),
    path('account-settings/', views.account_settings, name='account-settings'),
    path('change-password/', views.change_password, name='change-password'),
]