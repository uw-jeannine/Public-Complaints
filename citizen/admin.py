from django.contrib import admin
from .models import Complaint, ComplaintReport, ComplaintAssignment

@admin.register(ComplaintReport)
class ComplaintReportAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'office', 'author', 'created_at')
    list_filter = ('office', 'created_at')
    search_fields = ('complaint__tracking_number', 'action_taken')

@admin.register(ComplaintAssignment)
class ComplaintAssignmentAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'office', 'user', 'assigned_by', 'assigned_at')
    list_filter = ('office', 'assigned_at')
    search_fields = ('complaint__tracking_number', 'notes')
