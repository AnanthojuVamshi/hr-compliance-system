from django.contrib import admin
from .models import User, Policy, ComplianceRecord

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'department')
    list_filter = ('role', 'department')

@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'created_by', 'deadline')
    list_filter = ('department',)

@admin.register(ComplianceRecord)
class ComplianceRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'policy', 'status', 'acknowledged_at')
    list_filter = ('status',)