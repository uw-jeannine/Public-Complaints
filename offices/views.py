from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from citizen.models import Complaint, ComplaintReport, ComplaintAssignment, REFERRAL_LEVEL_CHOICES, ComplaintTransferRequest
from administrator.models import Office
from django.utils import timezone

def office_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.user_type == 'office' or request.user.user_type == 'administrator') and request.user.office:
            return view_func(request, *args, **kwargs)
        messages.error(request, "Access denied. You must be assigned to an office.")
        return redirect('landing')
    return wrapper

@login_required
@office_required
def office_dashboard(request):
    office = request.user.office
    complaints = Complaint.objects.filter(assigned_office=office).order_by('-created_at')
    
    stats = {
        'total': complaints.count(),
        'pending': complaints.filter(status='pending').count(),
        'in_progress': complaints.filter(status='in_progress').count(),
        'resolved': complaints.filter(status='resolved').count(),
    }
    
    return render(request, 'offices/dashboard.html', {
        'office': office,
        'complaints': complaints,
        'stats': stats
    })

@login_required
@office_required
def office_complaint_detail(request, pk):
    office = request.user.office
    complaint = get_object_or_404(Complaint, pk=pk, assigned_office=office)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'submit_report':
            action_taken = request.POST.get('action_taken')
            document = request.FILES.get('document')
            
            if action_taken:
                ComplaintReport.objects.create(
                    complaint=complaint,
                    author=request.user,
                    office=office,
                    action_taken=action_taken,
                    document=document
                )
                
                # Automatically update status to in_progress if it was pending
                if complaint.status == 'pending':
                    complaint.status = 'in_progress'
                    complaint.save()
                    
                messages.success(request, "Report submitted successfully.")
                return redirect('office_complaint_detail', pk=pk)
            else:
                messages.error(request, "Action taken description is required.")
        
        elif action == 'finalize_resolution':
            status = request.POST.get('status')
            resolution_details = request.POST.get('resolution_details')
            
            if status in ['resolved', 'rejected'] and resolution_details:
                complaint.status = status
                complaint.resolution_details = resolution_details
                complaint.resolved_at = timezone.now()
                complaint.save()
                
                # Create a final report entry for the resolution
                ComplaintReport.objects.create(
                    complaint=complaint,
                    author=request.user,
                    office=office,
                    action_taken=f"FINAL RESOLUTION ({status.upper()}): {resolution_details}"
                )
                
                messages.success(request, f"Complaint has been {status} successfully.")
                return redirect('office_complaint_detail', pk=pk)
            else:
                messages.error(request, "Please provide both status and resolution details.")
                
        elif action == 'transfer_case':
            if complaint.transfer_requests.filter(status='pending').exists():
                messages.error(request, "A transfer request is already pending approval.")
                return redirect('office_complaint_detail', pk=pk)

            referral_level = request.POST.get('referral_level')
            target_office_id = request.POST.get('office_id')
            notes = request.POST.get('notes', '')
            
            target_office = None
            if target_office_id:
                target_office = get_object_or_404(Office, pk=target_office_id)
                
            ComplaintTransferRequest.objects.create(
                complaint=complaint,
                requested_by=request.user,
                target_office=target_office,
                target_referral_level=referral_level or 'none',
                notes=notes,
                status='pending'
            )
            
            messages.success(request, "Transfer request submitted successfully. Awaiting administrator approval.")
            return redirect('office_complaint_detail', pk=pk)
                
    reports = complaint.reports.all().order_by('-created_at')
    offices = Office.objects.filter(is_active=True).exclude(pk=office.pk)
    pending_transfer = complaint.transfer_requests.filter(status='pending').first()
    
    return render(request, 'offices/complaint_detail.html', {
        'complaint': complaint,
        'reports': reports,
        'offices': offices,
        'referral_levels': REFERRAL_LEVEL_CHOICES,
        'pending_transfer': pending_transfer,
    })
