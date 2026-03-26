from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Province, District, Sector, Village

class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'full_name', 'phone_number', 'user_type', 'office', 'is_staff')
    list_filter = ('user_type', 'is_staff', 'is_superuser', 'office')
    search_fields = ('username', 'full_name', 'phone_number', 'email')
    ordering = ('username',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('full_name', 'phone_number', 'national_id', 'user_type', 'gender', 'office', 'province', 'district', 'sector', 'village', 'local_address')}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Fields', {
            'classes': ('wide',),
            'fields': ('full_name', 'phone_number', 'national_id', 'user_type', 'gender', 'office', 'province', 'district', 'sector', 'village', 'local_address'),
        }),
    )

admin.site.register(User, UserAdmin)
admin.site.register(Province)
admin.site.register(District)
admin.site.register(Sector)
admin.site.register(Village)
