from django.contrib import admin
from apps.leaves.models import LeaveType, LeaveRequest, LeaveApproval

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'max_days_per_year', 'is_paid', 'is_active']

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'total_days', 'status']
    list_filter = ['status', 'leave_type']
    search_fields = ['employee__username']
    date_hierarchy = 'applied_at'

@admin.register(LeaveApproval)
class LeaveApprovalAdmin(admin.ModelAdmin):
    list_display = ['leave_request', 'approver', 'level', 'action', 'acted_at']
