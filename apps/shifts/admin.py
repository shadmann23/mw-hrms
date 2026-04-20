from django.contrib import admin
from apps.shifts.models import ShiftTemplate, ShiftAssignment

@admin.register(ShiftTemplate)
class ShiftTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_time', 'end_time', 'color']

@admin.register(ShiftAssignment)
class ShiftAssignmentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'shift', 'date']
    list_filter = ['shift', 'date']
