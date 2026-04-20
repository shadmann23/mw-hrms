from django.contrib import admin
from apps.attendance.models import AttendanceRecord

@admin.register(AttendanceRecord)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'check_in', 'check_out', 'working_hours', 'status']
    list_filter = ['status', 'date']
    search_fields = ['employee__username', 'employee__first_name']
    date_hierarchy = 'date'
