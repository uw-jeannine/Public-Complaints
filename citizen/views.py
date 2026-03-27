from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Complaint, Notification

@login_required
def mark_notifications_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', 'landing_page'))

from administrator.models import ComplaintCategory
from accounts.models import Province, District

def landing_page(request):
    return render(request, 'citizen/landing.html')

def complaint_guidelines(request):
    return render(request, 'citizen/complaint_guidelines.html')

def help_center(request):
    return render(request, 'citizen/help_center.html')

def complaint_create(request):
    categories = ComplaintCategory.objects.filter(is_active=True)
    provinces = Province.objects.all()
    
    if request.method == 'POST':
        # 1. Complainant Details
        full_name = request.POST.get('full_name')
        gender = request.POST.get('gender')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('email')
        national_id = request.POST.get('national_id')
        
        # Complainant Residence
        res_province_id = request.POST.get('res_province')
        res_district_id = request.POST.get('res_district')
        res_sector = request.POST.get('res_sector')
        res_cell = request.POST.get('res_cell')
        res_village = request.POST.get('res_village')
        
        # 2. Land Information
        land_province_id = request.POST.get('land_province')
        land_district_id = request.POST.get('land_district')
        land_sector = request.POST.get('land_sector')
        land_cell = request.POST.get('land_cell')
        upi = request.POST.get('upi')
        
        # 3. Complaint Details
        category_id = request.POST.get('category')
        description = request.POST.get('description')
        approached_other = request.POST.get('approached_other') == 'yes'
        other_inst_name = request.POST.get('other_inst_name')
        prev_resolution = request.POST.get('prev_resolution')
        attachment = request.FILES.get('attachment')
        
        try:
            category = ComplaintCategory.objects.get(id=category_id)
            res_province = Province.objects.get(id=res_province_id) if res_province_id else None
            res_district = District.objects.get(id=res_district_id) if res_district_id else None
            land_province = Province.objects.get(id=land_province_id) if land_province_id else None
            land_district = District.objects.get(id=land_district_id) if land_district_id else None
            
            complaint = Complaint.objects.create(
                full_name=full_name,
                gender=gender,
                phone_number=phone_number,
                email=email,
                national_id=national_id,
                residence_province=res_province,
                residence_district=res_district,
                residence_sector=res_sector,
                residence_cell=res_cell,
                residence_village=res_village,
                land_province=land_province,
                land_district=land_district,
                land_sector=land_sector,
                land_cell=land_cell,
                upi=upi,
                category=category,
                description=description,
                has_approached_other_institution=approached_other,
                other_institution_name=other_inst_name,
                previous_resolution_details=prev_resolution,
                attachment=attachment,
                citizen=request.user if request.user.is_authenticated else None
            )
            
            messages.success(request, f"Your complaint has been submitted successfully! Tracking Number: {complaint.tracking_number}")
            return redirect('complaint_track_success', tracking_number=complaint.tracking_number)
            
        except Exception as e:
            messages.error(request, f"An error occurred while submitting your complaint: {str(e)}")

    return render(request, 'citizen/complaint_form.html', {
        'categories': categories,
        'provinces': provinces,
        'base_template': 'base.html' if request.user.is_authenticated else 'base_public.html',
    })

def complaint_track_success(request, tracking_number):
    complaint = get_object_or_404(Complaint, tracking_number=tracking_number)
    return render(request, 'citizen/complaint_success.html', {
        'complaint': complaint,
        'base_template': 'base.html' if request.user.is_authenticated else 'base_public.html',
    })

def complaint_track(request):
    tracking_number = request.GET.get('tracking_number', '').strip()
    complaint = None
    if tracking_number:
        complaint = Complaint.objects.filter(tracking_number=tracking_number).first()
        if not complaint:
            messages.error(request, f"No complaint found with tracking number {tracking_number}")
    
    return render(request, 'citizen/complaint_track.html', {
        'complaint': complaint,
        'base_template': 'base.html' if request.user.is_authenticated else 'base_public.html',
    })

@login_required
def citizen_dashboard(request):
    if request.user.user_type != 'citizen':
        return redirect('admin_dashboard')
    
    my_complaints = Complaint.objects.filter(citizen=request.user)[:5] # Show only 5 on dashboard
    return render(request, 'citizen/dashboard.html', {'complaints': my_complaints})

@login_required
def complaint_detail(request, pk):
    from django.shortcuts import get_object_or_404
    complaint = get_object_or_404(Complaint, pk=pk, citizen=request.user)
    reports = complaint.reports.all().order_by('created_at')
    return render(request, 'citizen/complaint_detail.html', {
        'complaint': complaint,
        'reports': reports
    })

@login_required
def citizen_complaints_list(request):
    if request.user.user_type != 'citizen':
        return redirect('admin_dashboard')
    
    my_complaints = Complaint.objects.filter(citizen=request.user)
    return render(request, 'citizen/citizen_complaints.html', {'complaints': my_complaints})
