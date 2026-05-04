from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_custom_email(subject, message, recipient_list):
    """
    Utility function to send emails using smtplib directly with unverified SSL context.
    """
    import ssl
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    try:
        # Create unverified SSL context
        context = ssl._create_unverified_context()
        
        # Build the email
        msg = MIMEMultipart()
        msg['From'] = settings.DEFAULT_FROM_EMAIL
        msg['To'] = ", ".join(recipient_list)
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))
        
        # Connect to Zoho SMTP
        # Note: Port 465 is for SSL, 587 is for TLS
        if settings.EMAIL_PORT == 465:
            server = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT, context=context)
        else:
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            server.starttls(context=context)
            
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email sent successfully to {recipient_list}")
        return True
    except Exception as e:
        logger.error(f"Error sending email to {recipient_list}: {str(e)}")
        return False

def send_assignment_email(complaint, user):
    """
    Sends an email to a staff member when a complaint is assigned to them.
    """
    if not user.email:
        return False
        
    subject = f"New Complaint Assigned: #{complaint.tracking_number}"
    message = f"""
    Hello {user.full_name or user.username},

    A new complaint has been assigned to you.

    Complaint Details:
    - Tracking Number: #{complaint.tracking_number}
    - Category: {complaint.category.name if complaint.category else 'N/A'}
    - Description: {complaint.description[:100]}...

    Please log in to the system to review and take action.

    Regards,
    Public Complaints System
    """
    return send_custom_email(subject, message, [user.email])

def send_welcome_email(user, plain_password):
    """
    Sends a welcome email to a new staff member with their credentials.
    """
    if not user.email:
        return False
        
    subject = "Welcome to Public Complaints System - Staff Account Created"
    message = f"""
    Hello {user.full_name or user.username},

    An administrative account has been created for you.

    Your Login Credentials:
    - Username: {user.username}
    - Password: {plain_password}

    Please log in at your earliest convenience and change your password for security.

    Regards,
    Public Complaints System
    """
    return send_custom_email(subject, message, [user.email])

def send_complainant_assignment_notification(complaint):
    """
    Sends an email to the complainant when their complaint is assigned to an office or staff.
    """
    if not complaint.email:
        return False
        
    subject = f"Update on Your Complaint: #{complaint.tracking_number}"
    message = f"""
    Hello {complaint.full_name},

    We would like to inform you that your complaint (Tracking Number: #{complaint.tracking_number}) has been assigned for review.

    Current Assignment:
    - Office: {complaint.assigned_office.name if complaint.assigned_office else 'General Review'}
    - Staff: {complaint.assigned_to.full_name if complaint.assigned_to else 'Assigned to Office Team'}

    Our team is now working on your case. You will receive further updates as we progress.

    Regards,
    Public Complaints System
    """
    return send_custom_email(subject, message, [complaint.email])

def send_status_update_email(complaint):
    """
    Sends an email to the complainant when the status of their complaint changes.
    """
    if not complaint.email:
        return False
        
    subject = f"Status Update: Complaint #{complaint.tracking_number}"
    status_display = complaint.get_status_display()
    
    # Custom message based on status
    if complaint.status == 'resolved':
        msg_detail = "Your complaint has been marked as RESOLVED. Thank you for your patience."
    elif complaint.status == 'rejected':
        msg_detail = "Your complaint has been REJECTED. Please contact us for more information."
    elif complaint.status == 'in_progress':
        msg_detail = "Your complaint is now IN PROGRESS. Our team is actively working on it."
    else:
        msg_detail = f"The status of your complaint has been updated to: {status_display}."

    message = f"""
    Hello {complaint.full_name},

    This is an automated update regarding your complaint (Tracking Number: #{complaint.tracking_number}).

    New Status: {status_display}
    
    {msg_detail}

    You can log in to your account or use your tracking number to see more details.

    Regards,
    Public Complaints System
    """
    return send_custom_email(subject, message, [complaint.email])

def send_password_reset_email(user, new_password):
    """
    Sends an email to a user when their password has been reset.
    """
    if not user.email:
        return False
        
    subject = "Password Reset Notification - Public Complaints System"
    message = f"""
    Hello {user.full_name or user.username},

    Your account password has been reset by an administrator.

    Your New Credentials:
    - Username: {user.username}
    - Password: {new_password}

    For security reasons, we recommend that you log in and change this password immediately.

    Regards,
    Public Complaints System
    """
    return send_custom_email(subject, message, [user.email])
