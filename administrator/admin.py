from django.contrib import admin
from .models import Office, ComplaintCategory
from citizen.models import Complaint


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display  = ('name', 'location', 'email', 'phone', 'staff_count', 'is_active', 'created_at')
    list_filter   = ('is_active',)
    search_fields = ('name', 'location', 'email')
    list_editable = ('is_active',)
    ordering      = ('name',)

    @admin.display(description='Staff Users')
    def staff_count(self, obj):
        return obj.staff_users.count()


@admin.register(ComplaintCategory)
class ComplaintCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('is_active',)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('tracking_number', 'full_name', 'category', 'status', 'is_appeal', 'assigned_to', 'created_at', 'escalation_risk')
    list_filter = ('status', 'category', 'is_escalated', 'is_appeal', 'created_at')
    search_fields = ('tracking_number', 'description', 'full_name', 'phone_number', 'national_id')
    ordering = ('-created_at',)
    readonly_fields = ('tracking_number', 'created_at', 'updated_at', 'escalation_risk')
    
    fieldsets = (
        ('Complaint Information', {
            'fields': ('tracking_number', 'category', 'description', 'upi', 'attachment', 'status', 'is_appeal')
        }),
        ('Complainant Information', {
            'fields': ('full_name', 'gender', 'phone_number', 'email', 'national_id')
        }),
        ('Residence Information', {
            'fields': ('residence_province', 'residence_district', 'residence_sector', 'residence_cell', 'residence_village')
        }),
        ('Land Information', {
            'fields': ('land_province', 'land_district', 'land_sector', 'land_cell')
        }),
        ('Assignment & Resolution', {
            'fields': ('assigned_to', 'assigned_at', 'resolved_at', 'resolution_details')
        }),
        ('ML Analysis', {
            'fields': ('is_escalated', 'escalation_risk')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        return True
