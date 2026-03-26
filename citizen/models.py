from django.db import models
from django.conf import settings
import uuid

class Complaint(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    )

    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )

    # Complainant Details (Part 1)
    full_name = models.CharField(max_length=255)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    national_id = models.CharField(max_length=20, verbose_name="ID or Passport Number")
    
    # Complainant Residence
    residence_province = models.ForeignKey('accounts.Province', on_delete=models.SET_NULL, null=True, related_name='complainant_residences')
    residence_district = models.ForeignKey('accounts.District', on_delete=models.SET_NULL, null=True, related_name='complainant_residences')
    residence_sector = models.CharField(max_length=100)
    residence_cell = models.CharField(max_length=100)
    residence_village = models.CharField(max_length=100)

    # Information on concerned land (Part 2)
    land_province = models.ForeignKey('accounts.Province', on_delete=models.SET_NULL, null=True, related_name='disputed_lands')
    land_district = models.ForeignKey('accounts.District', on_delete=models.SET_NULL, null=True, related_name='disputed_lands')
    land_sector = models.CharField(max_length=100)
    land_cell = models.CharField(max_length=100)
    upi = models.CharField(max_length=50, verbose_name="Parcel Identification (UPI)")

    # Complaint Details (Part 3)
    category = models.ForeignKey('administrator.ComplaintCategory', on_delete=models.CASCADE, related_name='complaints')
    description = models.TextField(max_length=5000)
    
    # Previous Institutional Contact
    has_approached_other_institution = models.BooleanField(default=False)
    other_institution_name = models.CharField(max_length=255, blank=True, null=True)
    previous_resolution_details = models.TextField(blank=True, null=True)
    
    attachment = models.FileField(upload_to='complaint_attachments/', blank=True, null=True)
    
    # Management fields
    tracking_number = models.CharField(max_length=20, unique=True, editable=False)
    citizen = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='my_complaints')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ML Prediction fields
    is_escalated = models.BooleanField(default=False, help_text="True if this complaint has been escalated to higher authorities.")
    escalation_risk = models.FloatField(default=0.0, help_text="Predicted probability (0-1) of escalation.")

    # Workflow tracking fields
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_complaints', help_text="The staff member handling this case.")
    assigned_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    is_appeal = models.BooleanField(default=False, help_text="True if this is an appeal of a previous resolution.")
    resolution_details = models.TextField(blank=True, null=True, help_text="Final outcome details.")

    # Office assignment
    assigned_office = models.ForeignKey('administrator.Office', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_complaints_dept', help_text="The department/office handling this case.")

    def save(self, *args, **kwargs):
        if not self.tracking_number:
            # Generate a unique tracking number: LC-YYYY-Random
            import random
            import datetime
            year = datetime.datetime.now().year
            rand_part = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            self.tracking_number = f"LC-{year}-{rand_part}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tracking_number} - {self.full_name}"

    class Meta:
        ordering = ['-created_at']

class ComplaintReport(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='reports')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='submitted_reports')
    office = models.ForeignKey('administrator.Office', on_delete=models.SET_NULL, null=True, related_name='office_reports')
    
    action_taken = models.TextField(help_text="Describe what has been done.")
    document = models.FileField(upload_to='report_documents/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report for {self.complaint.tracking_number} by {self.office.name if self.office else 'Unknown'}"

    class Meta:
        ordering = ['-created_at']

class ComplaintAssignment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='assignment_history')
    office = models.ForeignKey('administrator.Office', on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='assignments_made')
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        to = self.office.name if self.office else (self.user.username if self.user else "Unknown")
        return f"Assignment of {self.complaint.tracking_number} to {to}"

    class Meta:
        ordering = ['-assigned_at']
