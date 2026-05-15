# pyrefly: ignore [missing-import]
from .models import Notification, Complaint
from django.utils import timezone
from datetime import timedelta

def notification_context(request):
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        # Also get the 5 most recent unread notifications for the dropdown
        recent_notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:5]
        
        context = {
            'unread_notifications_count': unread_count,
            'recent_notifications': recent_notifications
        }
        
        if request.user.user_type == 'administrator':
            # Count of complaints that are pending review
            context['pending_complaints_count'] = Complaint.objects.filter(status='pending').count()
            # Count of complaints created within the last 3 days
            three_days_ago = timezone.now() - timedelta(days=3)
            context['new_complaints_count'] = Complaint.objects.filter(created_at__gte=three_days_ago).count()
        elif request.user.user_type == 'office':
            # Count of complaints assigned to this staff that are still pending
            context['my_pending_cases_count'] = Complaint.objects.filter(assigned_to=request.user, status='pending').count()
            
        return context
    return {
        'unread_notifications_count': 0,
        'recent_notifications': []
    }
