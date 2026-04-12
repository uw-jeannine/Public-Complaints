from accounts.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from accounts.decorators import administrator_required
from .models import Office, ComplaintCategory
from citizen.models import Complaint
from .utils import send_intouch_sms

@login_required
@administrator_required
def admin_dashboard(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Complaints metrics
    total_complaints = Complaint.objects.count()
    pending_complaints = Complaint.objects.filter(status='pending').count()
    in_progress_complaints = Complaint.objects.filter(status='in_progress').count()
    resolved_complaints = Complaint.objects.filter(status='resolved').count()
    rejected_complaints = Complaint.objects.filter(status='rejected').count()
    
    # User metrics
    total_citizens = User.objects.filter(user_type='citizen').count()
    total_office_staff = User.objects.filter(user_type='office').count()
    
    # Office metrics
    total_offices = Office.objects.count()
    active_offices = Office.objects.filter(is_active=True).count()
    
    # Recent complaints for the table
    recent_complaints = Complaint.objects.select_related('category', 'citizen').order_by('-created_at')[:10]
    
    # Data for charts    # Complaints by Category (Donut Chart)
    categories = ComplaintCategory.objects.annotate(complaint_count=models.Count('complaints'))
    category_data = [
        {'name': cat.name, 'count': cat.complaint_count}
        for cat in categories if cat.complaint_count > 0
    ]

    # Trends for the last 7 days (Small sparkline charts)
    from django.db.models.functions import TruncDate
    from datetime import timedelta
    seven_days_ago = timezone.now().date() - timedelta(days=6)
    daily_stats = Complaint.objects.filter(
        created_at__date__gte=seven_days_ago
    ).annotate(date=TruncDate('created_at')).values('date').annotate(count=models.Count('id')).order_by('date')
    
    # Fill in zeros for days with no complaints
    stats_dict = {stat['date']: stat['count'] for stat in daily_stats}
    complaint_trend = []
    for i in range(7):
        date = seven_days_ago + timedelta(days=i)
        complaint_trend.append(stats_dict.get(date, 0))

    return render(request, 'admin_dashboard.html', {
        'total_complaints': total_complaints,
        'pending_complaints': pending_complaints,
        'in_progress_complaints': in_progress_complaints,
        'resolved_complaints': resolved_complaints,
        'rejected_complaints': rejected_complaints,
        'total_citizens': total_citizens,
        'total_office_staff': total_office_staff,
        'total_offices': total_offices,
        'active_offices': active_offices,
        'recent_complaints': recent_complaints,
        'category_data': category_data,
        'complaint_trend': complaint_trend,
    })


@login_required
@administrator_required
def office_list(request):
    from django.core.paginator import Paginator
    q = request.GET.get('q', '').strip()
    offices_qs = Office.objects.all()
    if q:
        offices_qs = offices_qs.filter(name__icontains=q) | offices_qs.filter(location__icontains=q)
    paginator = Paginator(offices_qs, 10)
    page = request.GET.get('page', 1)
    offices = paginator.get_page(page)
    return render(request, 'offices/office_list.html', {'offices': offices})


@login_required
@administrator_required
def office_create(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if request.method == 'POST':
        # Office fields
        name        = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        location    = request.POST.get('location', '').strip()
        email       = request.POST.get('email', '').strip()
        phone       = request.POST.get('phone', '').strip()
        is_active   = request.POST.get('is_active') == 'on'
        # User credential fields
        username    = request.POST.get('username', '').strip()
        full_name   = request.POST.get('full_name', '').strip()
        user_phone  = request.POST.get('user_phone', '').strip()
        password    = request.POST.get('password', '')
        password2   = request.POST.get('password2', '')

        errors = []
        if not name:      errors.append('Office name is required.')
        if not username:  errors.append('Login username is required.')
        if not user_phone: errors.append('Staff phone number is required.')
        if not password:  errors.append('Password is required.')
        if password != password2: errors.append('Passwords do not match.')
        if len(password) < 8: errors.append('Password must be at least 8 characters.')
        if User.objects.filter(username=username).exists():
            errors.append(f'Username "{username}" is already taken.')
        if User.objects.filter(phone_number=user_phone).exists():
            errors.append(f'Phone number "{user_phone}" is already in use.')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            office = Office.objects.create(
                name=name, description=description, location=location,
                email=email, phone=phone, is_active=is_active
            )
            User.objects.create_user(
                username=username,
                password=password,
                full_name=full_name or name,
                email=email,
                phone_number=user_phone,
                user_type='office',
                office=office,
            )
            messages.success(request, f'Office "{name}" and its user account created successfully.')
            return redirect('office_list')

    return render(request, 'offices/office_form.html', {'action': 'Add'})


@login_required
@administrator_required
def office_update(request, pk):
    office = get_object_or_404(Office, pk=pk)
    if request.method == 'POST':
        office.name = request.POST.get('name', '').strip()
        office.description = request.POST.get('description', '').strip()
        office.location = request.POST.get('location', '').strip()
        office.email = request.POST.get('email', '').strip()
        office.phone = request.POST.get('phone', '').strip()
        office.is_active = request.POST.get('is_active') == 'on'

        if not office.name:
            messages.error(request, 'Office name is required.')
        else:
            office.save()
            messages.success(request, f'Office "{office.name}" updated successfully.')
            return redirect('office_list')
    return render(request, 'offices/office_form.html', {'office': office, 'action': 'Update'})


@login_required
@administrator_required
def office_delete(request, pk):
    office = get_object_or_404(Office, pk=pk)
    if request.method == 'POST':
        name = office.name
        office.delete()
        messages.success(request, f'Office "{name}" deleted.')
        return redirect('office_list')
    return render(request, 'offices/office_confirm_delete.html', {'office': office})

@login_required
@administrator_required
def admin_user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    
    # Safety check: Prevent deleting self
    if user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('admin_user_detail', pk=pk)
        
    if request.method == 'POST':
        name = user.full_name or user.username
        user.delete()
        messages.success(request, f'User "{name}" deleted successfully.')
        return redirect('office_user_list')
    return render(request, 'users/office_user_confirm_delete.html', {'user': user})

@login_required
@administrator_required
def office_user_list(request):
    from django.core.paginator import Paginator
    from django.contrib.auth import get_user_model
    User = get_user_model()
    q         = request.GET.get('q', '').strip()
    user_type = request.GET.get('type', '')   # '' = all, 'citizen', 'office'

    users_qs = User.objects.select_related('office').order_by('-date_joined')
    if user_type in ('citizen', 'office', 'administrator'):
        users_qs = users_qs.filter(user_type=user_type)
    if q:
        users_qs = (users_qs.filter(username__icontains=q)
                    | users_qs.filter(full_name__icontains=q)
                    | users_qs.filter(phone_number__icontains=q))

    paginator = Paginator(users_qs.distinct(), 10)
    users     = paginator.get_page(request.GET.get('page', 1))
    # counts for tab badges
    counts = {
        'all':           User.objects.count(),
        'citizen':       User.objects.filter(user_type='citizen').count(),
        'office':        User.objects.filter(user_type='office').count(),
        'administrator': User.objects.filter(user_type='administrator').count(),
    }
    return render(request, 'users/office_user_list.html', {
        'users': users, 'counts': counts,
        'current_type': user_type, 'q': q,
    })


@login_required
@administrator_required
def office_user_create(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    offices = Office.objects.filter(is_active=True)

    if request.method == 'POST':
        full_name   = request.POST.get('full_name', '').strip()
        username    = request.POST.get('username', '').strip()
        email       = request.POST.get('email', '').strip()
        phone       = request.POST.get('phone', '').strip()
        password    = request.POST.get('password', '')
        password2   = request.POST.get('password2', '')
        office_id   = request.POST.get('office')

        errors = []
        if not full_name:  errors.append('Full name is required.')
        if not username:   errors.append('Username is required.')
        if not phone:      errors.append('Phone number is required.')
        if not password:   errors.append('Password is required.')
        if password != password2: errors.append('Passwords do not match.')
        if len(password) < 8:     errors.append('Password must be at least 8 characters.')
        if User.objects.filter(username=username).exists():
            errors.append(f'Username "{username}" is already taken.')
        if User.objects.filter(phone_number=phone).exists():
            errors.append(f'Phone number "{phone}" is already in use.')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                full_name=full_name,
                email=email,
                phone_number=phone,
                user_type='office',
            )
            if office_id:
                user.office = get_object_or_404(Office, pk=office_id)
                user.save()
            
            # Send SMS with credentials
            sms_msg = f"Hello {full_name}, your account on Jeanine System is created. Username: {username}, Password: {password}"
            send_intouch_sms(phone, sms_msg)
            
            messages.success(request, f'User account for "{full_name}" created successfully.')
            return redirect('office_user_list')

    return render(request, 'users/office_user_form.html', {'offices': offices, 'action': 'Create'})



@login_required
@administrator_required
def admin_user_detail(request, pk):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    target_user = get_object_or_404(User, pk=pk)
    
    # Get user's activity
    if target_user.user_type == 'citizen':
        complaint_count = Complaint.objects.filter(citizen=target_user).count()
        recent_complaints = Complaint.objects.filter(citizen=target_user).order_by('-created_at')[:5]
    else:
        complaint_count = Complaint.objects.filter(assigned_to=target_user).count()
        recent_complaints = Complaint.objects.filter(assigned_to=target_user).order_by('-created_at')[:5]
        
    return render(request, 'users/user_detail.html', {
        'target_user': target_user,
        'complaint_count': complaint_count,
        'recent_complaints': recent_complaints,
    })


@login_required
@administrator_required
def admin_user_update(request, pk):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    target_user = get_object_or_404(User, pk=pk)
    offices = Office.objects.filter(is_active=True)

    if request.method == 'POST':
        target_user.full_name = request.POST.get('full_name', '').strip()
        target_user.email = request.POST.get('email', '').strip()
        target_user.phone_number = request.POST.get('phone', '').strip()
        office_id = request.POST.get('office')
        
        if office_id:
            target_user.office = get_object_or_404(Office, pk=office_id)
        else:
            target_user.office = None
            
        target_user.save()
        messages.success(request, f'User "{target_user.full_name or target_user.username}" updated successfully.')
        return redirect('office_user_list')

    return render(request, 'users/user_form.html', {
        'target_user': target_user,
        'offices': offices,
        'action': 'Update'
    })


@login_required
@administrator_required
def admin_user_password_reset(request, pk):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    target_user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if not password or password != password_confirm:
            messages.error(request, "Passwords do not match or are empty.")
        elif len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
        else:
            target_user.set_password(password)
            target_user.save()
            
            # Send SMS with new password
            sms_msg = f"Hello {target_user.full_name or target_user.username}, your password has been reset. Your new password is: {password}"
            if target_user.phone_number:
                send_intouch_sms(target_user.phone_number, sms_msg)
                
            messages.success(request, f"Password for {target_user.username} has been reset successfully.")
            return redirect('admin_user_detail', pk=pk)

    return render(request, 'users/user_password_reset.html', {
        'target_user': target_user
    })


# \u2500\u2500 Complaint Category Management \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

@login_required
@administrator_required
def category_list(request):
    from django.core.paginator import Paginator
    q = request.GET.get('q', '').strip()
    categories_qs = ComplaintCategory.objects.all()
    if q:
        categories_qs = categories_qs.filter(name__icontains=q)
    paginator = Paginator(categories_qs, 10)
    page = request.GET.get('page', 1)
    categories = paginator.get_page(page)
    return render(request, 'categories/category_list.html', {'categories': categories})


@login_required
@administrator_required
def category_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        if not name:
            messages.error(request, 'Category name is required.')
        elif ComplaintCategory.objects.filter(name=name).exists():
            messages.error(request, f'Category "{name}" already exists.')
        else:
            ComplaintCategory.objects.create(
                name=name, description=description, is_active=is_active
            )
            messages.success(request, f'Category "{name}" created successfully.')
            return redirect('category_list')
    return render(request, 'categories/category_form.html', {'action': 'Add'})


@login_required
@administrator_required
def category_update(request, pk):
    category = get_object_or_404(ComplaintCategory, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category.description = request.POST.get('description', '').strip()
        category.is_active = request.POST.get('is_active') == 'on'

        if not name:
            messages.error(request, 'Category name is required.')
        else:
            category.name = name
            category.save()
            messages.success(request, f'Category "{name}" updated successfully.')
            return redirect('category_list')
    return render(request, 'categories/category_form.html', {'category': category, 'action': 'Update'})


@login_required
@administrator_required
def category_delete(request, pk):
    category = get_object_or_404(ComplaintCategory, pk=pk)
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f'Category "{name}" deleted.')
        return redirect('category_list')
    return render(request, 'categories/category_confirm_delete.html', {'category': category})

@login_required
@administrator_required
def admin_complaints_list(request):
    from django.core.paginator import Paginator
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')

    complaints_qs = Complaint.objects.select_related('category', 'citizen').order_by('-created_at')

    if status_filter:
        complaints_qs = complaints_qs.filter(status=status_filter)

    if q:
        complaints_qs = complaints_qs.filter(
            models.Q(tracking_number__icontains=q) |
            models.Q(full_name__icontains=q) |
            models.Q(national_id__icontains=q)
        )

    paginator = Paginator(complaints_qs.distinct(), 15)
    page = request.GET.get('page', 1)
    complaints = paginator.get_page(page)

    # Predict risk for complaints on current page
    from complaint.ml_service import escalation_predictor
    for c in complaints:
        try:
            c.risk_score = escalation_predictor.predict_risk(c)
            c.risk_percentage = int(c.risk_score * 100)
        except:
            c.risk_score = 0.0
            c.risk_percentage = 0

    stats = {
        'total': Complaint.objects.count(),
        'pending': Complaint.objects.filter(status='pending').count(),
        'resolved': Complaint.objects.filter(status='resolved').count(),
    }

    return render(request, 'complaints/complaint_list.html', {
        'complaints': complaints,
        'stats': stats,
        'q': q,
        'current_status': status_filter
    })

@login_required
@administrator_required
def admin_complaint_detail(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    from .models import Office
    from citizen.models import ComplaintAssignment, ComplaintReport
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    from complaint.ml_service import escalation_predictor
    try:
        complaint.risk_score = escalation_predictor.predict_risk(complaint)
        complaint.risk_percentage = int(complaint.risk_score * 100)
    except:
        complaint.risk_score = 0.0
        complaint.risk_percentage = 0
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_status':
            new_status = request.POST.get('status')
            if new_status in dict(Complaint.STATUS_CHOICES):
                complaint.status = new_status
                complaint.save()
                messages.success(request, f"Status for tracking number {complaint.tracking_number} updated to {complaint.get_status_display()}.")

        elif action == 'assign_office':
            office_id = request.POST.get('office_id')
            if office_id:
                office = get_object_or_404(Office, pk=office_id)
                complaint.assigned_office = office
                complaint.save()
                
                # Log assignment
                ComplaintAssignment.objects.create(
                    complaint=complaint,
                    office=office,
                    assigned_by=request.user,
                    notes=request.POST.get('notes', '')
                )
                messages.success(request, f"Complaint assigned to {office.name}.")
            else:
                complaint.assigned_office = None
                complaint.save()
                messages.info(request, "Office assignment cleared.")

        elif action == 'assign_user':
            user_id = request.POST.get('user_id')
            if user_id:
                user = get_user_model().objects.get(pk=user_id)
                complaint.assigned_to = user
                complaint.assigned_at = timezone.now()
                complaint.save()
                
                # Log assignment
                ComplaintAssignment.objects.create(
                    complaint=complaint,
                    user=user,
                    assigned_by=request.user,
                    notes=request.POST.get('notes', '')
                )
                messages.success(request, f"Complaint assigned to {user.full_name}.")
            else:
                complaint.assigned_to = None
                complaint.assigned_at = None
                complaint.save()
                messages.info(request, "User assignment cleared.")

        return redirect('admin_complaint_detail', pk=pk)
    
    offices = Office.objects.filter(is_active=True)
    staff_users = User.objects.filter(user_type__in=['administrator', 'office'], is_active=True)
    assignments = complaint.assignment_history.all()
    reports = complaint.reports.all()
    
    return render(request, 'complaints/complaint_detail.html', {
        'complaint': complaint,
        'offices': offices,
        'staff_users': staff_users,
        'assignments': assignments,
        'reports': reports
    })

@login_required
@administrator_required
def admin_reports(request):
    from django.db.models import Count, Q
    from django.contrib.auth import get_user_model
    from accounts.models import Province, District
    User = get_user_model()

    # 1. Location-based reports (Residence)
    resilience_provinces = Province.objects.annotate(
        total_complaints=Count('complainant_residences'),
        pending=Count('complainant_residences', filter=Q(complainant_residences__status='pending')),
        resolved=Count('complainant_residences', filter=Q(complainant_residences__status='resolved'))
    ).order_by('-total_complaints')

    districts_qs = District.objects.select_related('province').annotate(
        total_complaints=Count('complainant_residences'),
        pending=Count('complainant_residences', filter=Q(complainant_residences__status='pending')),
        resolved=Count('complainant_residences', filter=Q(complainant_residences__status='resolved'))
    ).order_by('-total_complaints')

    from django.core.paginator import Paginator
    paginator = Paginator(districts_qs, 10)
    page_number = request.GET.get('page')
    resilience_districts = paginator.get_page(page_number)

    # 2. Category-based reports
    category_stats = ComplaintCategory.objects.annotate(
        total=Count('complaints'),
        pending=Count('complaints', filter=Q(complaints__status='pending')),
        resolved=Count('complaints', filter=Q(complaints__status='resolved'))
    ).order_by('-total')

    # 3. Trend Data (Last 30 days)
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models.functions import TruncDate
    
    thirty_days_ago = timezone.now().date() - timedelta(days=29)
    daily_stats = Complaint.objects.filter(
        created_at__date__gte=thirty_days_ago
    ).annotate(date=TruncDate('created_at')).values('date').annotate(count=Count('id')).order_by('date')
    
    # Fill gaps for trend chart
    stats_map = {s['date']: s['count'] for s in daily_stats}
    trend_labels = []
    trend_values = []
    for i in range(30):
        day = thirty_days_ago + timedelta(days=i)
        trend_labels.append(day.strftime('%b %d'))
        trend_values.append(stats_map.get(day, 0))

    # Serialized data for JS
    province_chart_data = [
        {'name': p.name, 'count': p.total_complaints} for p in resilience_provinces
    ]
    category_chart_data = [
        {'name': c.name, 'count': c.total} for c in category_stats
    ]

    # 4. User reports
    user_stats = {
        'total_users': User.objects.count(),
        'citizens': User.objects.filter(user_type='citizen').count(),
        'officers': User.objects.filter(user_type='office').count(),
        'admins': User.objects.filter(user_type='administrator').count(),
    }

    # 5. System activity (Recent Reports/Assignments)
    from citizen.models import ComplaintReport, ComplaintAssignment
    recent_reports = ComplaintReport.objects.select_related('complaint', 'author', 'office').order_by('-created_at')[:10]
    recent_assignments = ComplaintAssignment.objects.select_related('complaint', 'office', 'user', 'assigned_by').order_by('-assigned_at')[:10]

    return render(request, 'reports/admin_reports.html', {
        'resilience_provinces': resilience_provinces,
        'resilience_districts': resilience_districts,
        'category_stats': category_stats,
        'user_stats': user_stats,
        'recent_reports': recent_reports,
        'recent_assignments': recent_assignments,
        'trend_labels': trend_labels,
        'trend_values': trend_values,
        'province_chart_data': province_chart_data,
        'category_chart_data': category_chart_data,
    })