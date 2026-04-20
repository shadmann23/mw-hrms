from django.contrib import admin
from apps.employees.models import Employee, Department, Position

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'head', 'is_active']
    search_fields = ['name', 'code']

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'level', 'is_active']
    list_filter = ['department']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'full_name', 'department', 'position', 'status', 'hire_date']
    list_filter = ['status', 'department', 'employment_type']
    search_fields = ['employee_id', 'user__first_name', 'user__last_name', 'user__email']
    raw_id_fields = ['user', 'supervisor']
