from accounts.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from accounts.decorators import administrator_required
from .models import Office, ComplaintCategory
from citizen.models import Complaint, ComplaintTransferRequest
from .utils import send_intouch_sms
from utils.send_email import send_welcome_email, send_assignment_email, send_complainant_assignment_notification, send_status_update_email, send_password_reset_email

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
    
    three_days_ago = timezone.now() - timedelta(days=3)
    for c in recent_complaints:
        c.is_new = c.created_at >= three_days_ago
        c.deadline = c.created_at + timedelta(days=3)
        c.is_overdue = timezone.now() > c.deadline and c.status not in ['resolved', 'rejected']
        
    # Pending transfer requests
    pending_transfers = ComplaintTransferRequest.objects.filter(status='pending').select_related('complaint', 'requested_by', 'target_office')
    
    # Data for charts    # Complaints by Category (Donut Chart)
    categories = ComplaintCategory.objects.annotate(complaint_count=models.Count('complaints'))
    category_data = [
        {'name': cat.name, 'count': cat.complaint_count}
        for cat in categories if cat.complaint_count > 0
    ]

    # Trends for the last 7 days (Small sparkline charts)
    from django.db.models.functions import TruncDate
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
        'pending_transfers': pending_transfers,
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
    available_users = User.objects.filter(user_type='office', office__isnull=True)

    if request.method == 'POST':
        # Office fields
        name        = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        location    = request.POST.get('location', '').strip()
        email       = request.POST.get('email', '').strip()
        phone       = request.POST.get('phone', '').strip()
        is_active   = request.POST.get('is_active') == 'on'
        
        # Staff assignment fields
        existing_user_id = request.POST.get('existing_user_id')

        if not name:
            messages.error(request, 'Office name is required.')
        else:
            office = Office.objects.create(
                name=name, description=description, location=location,
                email=email, phone=phone, is_active=is_active
            )
            
            if existing_user_id:
                existing_user = get_object_or_404(User, pk=existing_user_id)
                existing_user.office = office
                existing_user.save()
                messages.success(request, f'Office "{name}" created and user "{existing_user.username}" assigned.')
            else:
                messages.success(request, f'Office "{name}" created successfully. You can assign staff later.')
            
            return redirect('office_list')

    return render(request, 'offices/office_form.html', {
        'action': 'Add',
        'available_users': available_users
    })


@login_required
@administrator_required
def office_update(request, pk):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    office = get_object_or_404(Office, pk=pk)
    
    if request.method == 'POST':
        # Office fields
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
            
            # Handle existing staff assignment
            existing_user_id = request.POST.get('existing_user_id')
            if existing_user_id and request.POST.get('assign_existing'):
                existing_user = get_object_or_404(User, pk=existing_user_id, user_type='office')
                existing_user.office = office
                existing_user.save()
                messages.success(request, f'User "{existing_user.full_name or existing_user.username}" assigned to "{office.name}".')

            messages.success(request, f'Office "{office.name}" updated successfully.')
            return redirect('office_list')

    staff_users = office.staff_users.all()
    # Users who could be assigned (office type but no office assigned)
    available_users = User.objects.filter(user_type='office', office__isnull=True)
    
    return render(request, 'offices/office_form.html', {
        'office': office, 
        'action': 'Update',
        'staff_users': staff_users,
        'available_users': available_users
    })


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
    office_id = request.GET.get('office_id')

    users_qs = User.objects.select_related('office').order_by('-date_joined')
    if user_type in ('citizen', 'office', 'administrator'):
        users_qs = users_qs.filter(user_type=user_type)
    if office_id:
        users_qs = users_qs.filter(office_id=office_id)
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
            
            # Send Email with credentials
            send_welcome_email(user, password)
            
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
            
            # Send Email with new password
            send_password_reset_email(target_user, password)
                
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
    status_filter = request.GET.get('status', 'pending')

    complaints_qs = Complaint.objects.select_related('category', 'citizen').order_by('-created_at')

    if status_filter:
        if status_filter == 'closed':
            complaints_qs = complaints_qs.filter(status__in=['resolved', 'rejected'])
        else:
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

    three_days_ago = timezone.now() - timedelta(days=3)
    for c in complaints:
        c.is_new = c.created_at >= three_days_ago
        c.deadline = c.created_at + timedelta(days=3)
        c.is_overdue = timezone.now() > c.deadline and c.status not in ['resolved', 'rejected']

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
            referral_level = request.POST.get('referral_level')
            
            if new_status in dict(Complaint.STATUS_CHOICES):
                complaint.status = new_status
            
            if referral_level:
                from citizen.models import REFERRAL_LEVEL_CHOICES
                if referral_level in dict(REFERRAL_LEVEL_CHOICES):
                    complaint.referral_level = referral_level
            
            complaint.save()
            
            # Send Email to complainant if email exists
            if complaint.email:
                send_status_update_email(complaint)
                
            messages.success(request, f"Status for tracking number {complaint.tracking_number} updated to {complaint.get_status_display()}.")

        elif action == 'unified_assign':
            office_id = request.POST.get('office_id')
            user_id = request.POST.get('user_id')
            notes = request.POST.get('notes', '')
            
            # Handle Office Assignment
            if office_id:
                office = get_object_or_404(Office, pk=office_id)
                if complaint.assigned_office != office:
                    complaint.assigned_office = office
                    ComplaintAssignment.objects.create(
                        complaint=complaint,
                        office=office,
                        assigned_by=request.user,
                        notes=notes
                    )
            else:
                complaint.assigned_office = None
            
            # Handle Staff Assignment
            if user_id:
                user = get_object_or_404(get_user_model(), pk=user_id)
                if complaint.assigned_to != user:
                    complaint.assigned_to = user
                    complaint.assigned_at = timezone.now()
                    ComplaintAssignment.objects.create(
                        complaint=complaint,
                        user=user,
                        assigned_by=request.user,
                        notes=notes
                    )
            else:
                complaint.assigned_to = None
                complaint.assigned_at = None
            
            complaint.save()
            
            # Send Email to staff if assigned to a user
            if user_id:
                assigned_user = get_object_or_404(get_user_model(), pk=user_id)
                send_assignment_email(complaint, assigned_user)
            
            # Send Email to complainant if email exists
            if complaint.email:
                send_complainant_assignment_notification(complaint)
                
            messages.success(request, "Assignment updated successfully.")

        elif action == 'approve_transfer':
            transfer_id = request.POST.get('transfer_id')
            transfer_req = get_object_or_404(ComplaintTransferRequest, pk=transfer_id, complaint=complaint, status='pending')
            
            # Apply changes to complaint
            if transfer_req.target_referral_level:
                complaint.referral_level = transfer_req.target_referral_level
                
            if transfer_req.target_office:
                old_office_name = complaint.assigned_office.name if complaint.assigned_office else "None"
                complaint.assigned_office = transfer_req.target_office
                complaint.assigned_to = None
                complaint.assigned_at = None
                
                # Log assignment history
                ComplaintAssignment.objects.create(
                    complaint=complaint,
                    office=transfer_req.target_office,
                    assigned_by=request.user,
                    notes=f"Approved transfer from {old_office_name} office. Notes: {transfer_req.notes}"
                )
            else:
                # If only referral level changed
                ComplaintAssignment.objects.create(
                    complaint=complaint,
                    office=complaint.assigned_office,
                    assigned_by=request.user,
                    notes=f"Approved referral level to {transfer_req.get_target_referral_level_display()}. Notes: {transfer_req.notes}"
                )
            
            complaint.save()
            
            # Mark transfer request as approved
            transfer_req.status = 'approved'
            transfer_req.actioned_by = request.user
            transfer_req.actioned_at = timezone.now()
            transfer_req.save()
            
            messages.success(request, "Transfer request approved successfully.")
            
        elif action == 'reject_transfer':
            transfer_id = request.POST.get('transfer_id')
            rejection_reason = request.POST.get('rejection_reason', '')
            transfer_req = get_object_or_404(ComplaintTransferRequest, pk=transfer_id, complaint=complaint, status='pending')
            
            transfer_req.status = 'rejected'
            transfer_req.actioned_by = request.user
            transfer_req.actioned_at = timezone.now()
            transfer_req.rejection_reason = rejection_reason
            transfer_req.save()
            
            messages.success(request, "Transfer request rejected.")

        return redirect('admin_complaint_detail', pk=pk)
    
    offices = Office.objects.filter(is_active=True)
    staff_users = User.objects.filter(user_type__in=['administrator', 'office'], is_active=True)
    assignments = complaint.assignment_history.all()
    reports = complaint.reports.all()
    pending_transfer = complaint.transfer_requests.filter(status='pending').first()
    
    return render(request, 'complaints/complaint_detail.html', {
        'complaint': complaint,
        'offices': offices,
        'staff_users': staff_users,
        'assignments': assignments,
        'reports': reports,
        'pending_transfer': pending_transfer,
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

    # 4. Top Complainants (Citizens)
    top_citizens = User.objects.filter(user_type='citizen').annotate(
        complaint_count=Count('my_complaints')
    ).order_by('-complaint_count')[:10]

    # 5. User reports

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
        'top_citizens': top_citizens,
        'recent_reports': recent_reports,
        'recent_assignments': recent_assignments,
        'trend_labels': trend_labels,
        'trend_values': trend_values,
        'province_chart_data': province_chart_data,
        'category_chart_data': category_chart_data,
    })


@administrator_required
def export_reports_pdf(request):
    import io
    from django.http import HttpResponse
    from django.utils import timezone
    from django.db.models import Count, Q
    from django.contrib.auth import get_user_model
    from accounts.models import Province, District
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch

    User = get_user_model()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1e293b')
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b')
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=10,
        spaceAfter=6
    )
    table_header = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#ffffff'),
        alignment=1
    )
    table_cell = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#334155')
    )
    table_cell_center = ParagraphStyle(
        'TableCellCenter',
        parent=table_cell,
        alignment=1
    )

    elements = []

    # 1. Header Banner
    now_str = timezone.now().strftime('%b %d, %Y %H:%M')
    header_data = [
        [
            Paragraph("<b>PUBLIC COMPLAINT SYSTEM</b><br/><font size=9 color='#64748b'>Official System Intelligence & Analytics Executive Report</font>", title_style),
            Paragraph(f"<b>Date:</b> {now_str}<br/><b>Ref:</b> REP-{timezone.now().strftime('%Y%m%d')}<br/><font color='#2563eb'><b>CONFIDENTIAL REPORT</b></font>", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[7.0*inch, 3.5*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#cbd5e1'), spaceAfter=15, spaceBefore=5))

    # 2. Key Metrics Summary Cards
    user_stats = {
        'total_users': User.objects.count(),
        'citizens': User.objects.filter(user_type='citizen').count(),
        'officers': User.objects.filter(user_type='office').count(),
        'admins': User.objects.filter(user_type='administrator').count(),
    }

    metrics_data = [
        [
            Paragraph("<b>Total System Users</b>", table_header),
            Paragraph("<b>Citizens Registered</b>", table_header),
            Paragraph("<b>Office Staff</b>", table_header),
            Paragraph("<b>Administrators</b>", table_header),
        ],
        [
            Paragraph(f"<font size=14><b>{user_stats['total_users']}</b></font>", table_cell_center),
            Paragraph(f"<font size=14><b>{user_stats['citizens']}</b></font>", table_cell_center),
            Paragraph(f"<font size=14><b>{user_stats['officers']}</b></font>", table_cell_center),
            Paragraph(f"<font size=14><b>{user_stats['admins']}</b></font>", table_cell_center),
        ]
    ]
    metrics_table = Table(metrics_data, colWidths=[2.6*inch, 2.6*inch, 2.6*inch, 2.6*inch])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2563eb')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#f8fafc')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(metrics_table)
    elements.append(Spacer(1, 15))

    # 3. Complaints by Province Table
    elements.append(Paragraph("Complaints Breakdown by Province", section_heading))
    resilience_provinces = Province.objects.annotate(
        total_complaints=Count('complainant_residences'),
        pending=Count('complainant_residences', filter=Q(complainant_residences__status='pending')),
        resolved=Count('complainant_residences', filter=Q(complainant_residences__status='resolved'))
    ).order_by('-total_complaints')

    prov_rows = [
        [
            Paragraph("<b>Province Name</b>", table_header),
            Paragraph("<b>Total Complaints</b>", table_header),
            Paragraph("<b>Pending Cases</b>", table_header),
            Paragraph("<b>Resolved Cases</b>", table_header),
            Paragraph("<b>Resolution Rate</b>", table_header),
        ]
    ]
    for p in resilience_provinces:
        rate = f"{round((p.resolved / p.total_complaints) * 100)}%" if p.total_complaints > 0 else "0%"
        prov_rows.append([
            Paragraph(p.name, table_cell),
            Paragraph(str(p.total_complaints), table_cell_center),
            Paragraph(f"<font color='#d97706'>{p.pending}</font>", table_cell_center),
            Paragraph(f"<font color='#16a34a'>{p.resolved}</font>", table_cell_center),
            Paragraph(f"<b>{rate}</b>", table_cell_center),
        ])

    prov_table = Table(prov_rows, colWidths=[3.2*inch, 1.8*inch, 1.8*inch, 1.8*inch, 1.8*inch])
    prov_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
    ]))
    elements.append(prov_table)
    elements.append(Spacer(1, 15))

    # 4. Category Stats & Top Complainants Side-by-Side
    elements.append(Paragraph("Complaint Categories & Top Complainants", section_heading))
    category_stats = ComplaintCategory.objects.annotate(
        total=Count('complaints'),
        pending=Count('complaints', filter=Q(complaints__status='pending')),
        resolved=Count('complaints', filter=Q(complaints__status='resolved'))
    ).order_by('-total')[:10]

    cat_rows = [
        [Paragraph("<b>Category Name</b>", table_header), Paragraph("<b>Total</b>", table_header), Paragraph("<b>Resolved</b>", table_header)]
    ]
    for c in category_stats:
        cat_rows.append([
            Paragraph(c.name, table_cell),
            Paragraph(str(c.total), table_cell_center),
            Paragraph(str(c.resolved), table_cell_center),
        ])
    cat_table = Table(cat_rows, colWidths=[3.0*inch, 1.0*inch, 1.0*inch])
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f766e')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
    ]))

    top_citizens = User.objects.filter(user_type='citizen').annotate(
        complaint_count=Count('my_complaints')
    ).order_by('-complaint_count')[:10]

    cit_rows = [
        [Paragraph("<b>Citizen Name / Contact</b>", table_header), Paragraph("<b>Complaints Submitted</b>", table_header)]
    ]
    for cit in top_citizens:
        name = cit.full_name or cit.username
        contact = f" ({cit.phone_number})" if cit.phone_number else ""
        cit_rows.append([
            Paragraph(f"{name}{contact}", table_cell),
            Paragraph(str(cit.complaint_count), table_cell_center),
        ])
    cit_table = Table(cit_rows, colWidths=[3.5*inch, 1.5*inch])
    cit_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4338ca')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
    ]))

    side_table = Table([[cat_table, Paragraph("", table_cell), cit_table]], colWidths=[5.0*inch, 0.4*inch, 5.0*inch])
    side_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(side_table)

    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#94a3b8'))
        canvas.drawString(36, 20, "Republic of Rwanda • Public Complaints System • Official Executive Report")
        canvas.drawRightString(A4[1] - 36, 20, f"Page {doc.page}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="System_Reports_{timezone.now().strftime("%Y-%m-%d")}.pdf"'
    return response