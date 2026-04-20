"""accounts/sysadmin_urls.py — System Admin Panel URLs"""
from django.urls import path
from apps.accounts import sysadmin_views as views

app_name = 'sysadmin'

urlpatterns = [
    path('', views.SysAdminDashboardView.as_view(), name='dashboard'),
    path('roles/', views.RoleManagementView.as_view(), name='roles'),
    path('departments/', views.DepartmentManagementView.as_view(), name='departments'),
    path('departments/create/', views.DepartmentCreateView.as_view(), name='dept_create'),
    path('departments/<int:pk>/edit/', views.DepartmentEditView.as_view(), name='dept_edit'),
    path('departments/<int:pk>/toggle/', views.DepartmentToggleView.as_view(), name='dept_toggle'),
    path('leave-types/', views.LeaveTypeManagementView.as_view(), name='leave_types'),
    path('leave-types/create/', views.LeaveTypeCreateView.as_view(), name='leave_type_create'),
    path('leave-types/<int:pk>/edit/', views.LeaveTypeEditView.as_view(), name='leave_type_edit'),
    path('leave-types/<int:pk>/toggle/', views.LeaveTypeToggleView.as_view(), name='leave_type_toggle'),
    path('shift-templates/', views.ShiftTemplateManagementView.as_view(), name='shift_templates'),
    path('shift-templates/create/', views.ShiftTemplateCreateView.as_view(), name='shift_create'),
    path('shift-templates/<int:pk>/edit/', views.ShiftTemplateEditView.as_view(), name='shift_edit'),
    path('shift-templates/<int:pk>/delete/', views.ShiftTemplateDeleteView.as_view(), name='shift_delete'),
    path('support-categories/', views.SupportCategoryView.as_view(), name='support_cats'),
    path('system-info/', views.SystemInfoView.as_view(), name='system_info'),
    path('bulk-actions/', views.BulkActionsView.as_view(), name='bulk_actions'),
]
