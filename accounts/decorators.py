from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def citizen_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type == 'citizen':
            return view_func(request, *args, **kwargs)
        messages.error(request, "Access denied. Citizens only.")
        return redirect('sign-in')
    return _wrapped_view

def office_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type == 'office':
            return view_func(request, *args, **kwargs)
        messages.error(request, "Access denied. Office users only.")
        return redirect('sign-in')
    return _wrapped_view

def administrator_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.user_type == 'administrator' or request.user.is_superuser):
            return view_func(request, *args, **kwargs)
        messages.error(request, "Access denied. Administrators only.")
        return redirect('sign-in')
    return _wrapped_view
