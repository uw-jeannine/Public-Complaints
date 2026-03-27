from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Complaint, Notification
from accounts.models import User

@receiver(post_save, sender=Complaint)
def create_complaint_notifications(sender, instance, created, **kwargs):
    if created:
        # 1. Notify all Administrators
        admins = User.objects.filter(user_type=User.ADMINISTRATOR)
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                title="New Complaint Submitted",
                message=f"A new complaint {instance.tracking_number} has been submitted by {instance.full_name}.",
                complaint=instance
            )
    else:
        # 2. Notify Office users if assigned_office changed
        if instance.assigned_office:
            from accounts.models import User
            staff = User.objects.filter(office=instance.assigned_office)
            for member in staff:
                # Check if notification already exists to avoid duplicates on every save
                # For now, we'll just create it (simplified)
                Notification.objects.get_or_create(
                    recipient=member,
                    title="Complaint Assigned to Your Office",
                    message=f"Complaint {instance.tracking_number} has been assigned to your department ({instance.assigned_office.name}).",
                    complaint=instance,
                    is_read=False
                )

@receiver(post_save, sender=Complaint)
def status_update_notification(sender, instance, created, **kwargs):
    if not created:
        # Notify the Citizen about status update
        if instance.citizen:
            Notification.objects.create(
                recipient=instance.citizen,
                title="Complaint Status Updated",
                message=f"The status of your complaint {instance.tracking_number} has been updated to {instance.get_status_display()}.",
                complaint=instance
            )

        # Notify assigned_to user if it's a new assignment
        if instance.assigned_to:
            # This is a bit tricky to detect 'just assigned' without a tracker, 
            # but we can at least notify whenever it's saved with an assigned_to
            Notification.objects.create(
                recipient=instance.assigned_to,
                title="Complaint Assigned to You",
                message=f"Complaint {instance.tracking_number} has been assigned to you for handling.",
                complaint=instance
            )
