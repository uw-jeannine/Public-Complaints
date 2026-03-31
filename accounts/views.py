from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .forms import UserSignUpForm, UserLoginForm, UserProfileUpdateForm
from .models import Province
from django.http import JsonResponse
from .models import District, Sector, Village
from utils.user_redirect import get_user_redirect_url
from django.contrib.auth.decorators import login_required

def sign_up(request):
    if request.method == 'POST':
        form = UserSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # --- Link past guest complaints to this user ---
            from citizen.models import Complaint
            Complaint.objects.filter(email=user.email, citizen=None).update(citizen=user)
            # -----------------------------------------------
            
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect(get_user_redirect_url(user))
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = UserSignUpForm()
    
    provinces = Province.objects.all()
    return render(request, 'sign-up.html', {
        'form': form,
        'provinces': provinces
    })

def sign_in(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect(get_user_redirect_url(user))
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = UserLoginForm()
    return render(request, 'sign-in.html', {'form': form})

@login_required
def sign_out(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('sign-in')



def get_locations(request):
    parent_type = request.GET.get('type')
    parent_id = request.GET.get('parent_id')
    
    data = []
    if parent_type == 'province':
        data = list(District.objects.filter(province_id=parent_id).values('id', 'name'))
    elif parent_type == 'district':
        data = list(Sector.objects.filter(district_id=parent_id).values('id', 'name'))
    elif parent_type == 'sector':
        data = list(Village.objects.filter(sector_id=parent_id).values('id', 'name'))
        
    return JsonResponse(data, safe=False)


@login_required
def account_settings(request):
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('account-settings')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = UserProfileUpdateForm(instance=request.user)
    
    provinces = Province.objects.all()
    return render(request, 'account-setting.html', {
        'form': form,
        'provinces': provinces
    })


@login_required
def change_password(request):
    from django.contrib.auth import update_session_auth_hash
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(current_password):
            messages.error(request, "Your current password is incorrect.")
        elif new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
        elif len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)  # keep user logged in
            messages.success(request, "Password changed successfully!")
            return redirect('change-password')
    return render(request, 'change-password.html')
