"""accounts/sysadmin_views.py — System Administration Panel"""
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.views import View
from django.utils import timezone
from django.db.models import Count

from apps.accounts.decorators import AdminRequiredMixin
from apps.accounts.models import Role
from apps.employees.models import Employee, Department, Position
from apps.leaves.models import LeaveType, LeaveRequest
from apps.attendance.models import AttendanceRecord
from apps.shifts.models import ShiftTemplate, ShiftAssignment
from apps.support.models import SupportTicket, SupportCategory
from apps.notifications.models import Notification

User = get_user_model()


class SysAdminDashboardView(AdminRequiredMixin, View):
    template_name = 'sysadmin/dashboard.html'

    def get(self, request):
        today = timezone.localdate()

        # System-wide statistics
        stats = {
            # Users
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'pending_users': User.objects.filter(is_active=False).count(),
            'users_by_role': list(
                User.objects.values('role__name').annotate(count=Count('id')).order_by('role__name')
            ),

            # Employees
            'total_employees': Employee.objects.count(),
            'active_employees': Employee.objects.filter(status='active').count(),
            'terminated_employees': Employee.objects.filter(status__in=['terminated', 'fired']).count(),
            'suspended_employees': Employee.objects.filter(status='suspended').count(),
            'employees_by_dept': list(
                Employee.objects.filter(status='active')
                .values('department__name').annotate(count=Count('id')).order_by('-count')
            ),

            # Attendance
            'checked_in_today': AttendanceRecord.objects.filter(date=today).count(),
            'late_today': AttendanceRecord.objects.filter(date=today, status='late').count(),

            # Leaves
            'pending_leaves': LeaveRequest.objects.filter(status='pending').count(),
            'approved_leaves_this_month': LeaveRequest.objects.filter(
                status='approved',
                applied_at__month=today.month,
                applied_at__year=today.year
            ).count(),

            # Support
            'open_tickets': SupportTicket.objects.filter(status='open').count(),
            'in_progress_tickets': SupportTicket.objects.filter(status='in_progress').count(),

            # Configuration
            'departments': Department.objects.count(),
            'active_departments': Department.objects.filter(is_active=True).count(),
            'leave_types': LeaveType.objects.count(),
            'shift_templates': ShiftTemplate.objects.count(),
        }

        recent_events = []

        # Recent terminations
        for emp in Employee.objects.filter(
            status__in=['terminated', 'fired'],
            termination_date__isnull=False
        ).order_by('-termination_date')[:5]:
            recent_events.append({
                'type': 'termination',
                'label': f"{emp.full_name} ({emp.get_status_display()})",
                'date': emp.termination_date,
                'icon': 'user-x',
                'color': 'var(--danger)',
            })

        # Recent registrations
        for u in User.objects.filter(is_active=False).order_by('-date_joined')[:3]:
            recent_events.append({
                'type': 'registration',
                'label': f"{u.get_full_name()} pending approval",
                'date': u.date_joined.date(),
                'icon': 'user-plus',
                'color': 'var(--warning)',
            })

        ctx = {
            'stats': stats,
            'recent_events': sorted(recent_events, key=lambda x: x['date'], reverse=True)[:8],
            'departments': Department.objects.annotate(emp_count=Count('employees')).order_by('name'),
            'leave_types': LeaveType.objects.all(),
            'shift_templates': ShiftTemplate.objects.all(),
        }
        return render(request, self.template_name, ctx)


class RoleManagementView(AdminRequiredMixin, View):
    template_name = 'sysadmin/roles.html'

    def get(self, request):
        roles = Role.objects.annotate(user_count=Count('users')).order_by('name')
        users_by_role = {}
        for role in roles:
            users_by_role[role.name] = User.objects.filter(role=role).order_by('first_name')[:10]
        return render(request, self.template_name, {'roles': roles, 'users_by_role': users_by_role})

    def post(self, request):
        user_pk = request.POST.get('user_pk')
        new_role_name = request.POST.get('role')
        try:
            user = User.objects.get(pk=user_pk)
            old_role = user.role
            new_role = Role.objects.get(name=new_role_name)
            user.role = new_role
            user.save(update_fields=['role'])
            Notification.send(
                recipient=user,
                notification_type='role_changed',
                title='Your role has been updated',
                message=f"Your system role changed from {old_role} to {new_role}.",
            )
            messages.success(request, f"{user.get_full_name()}'s role changed to {new_role}.")
        except (User.DoesNotExist, Role.DoesNotExist) as e:
            messages.error(request, f"Error: {e}")
        return redirect('sysadmin:roles')


class DepartmentManagementView(AdminRequiredMixin, View):
    template_name = 'sysadmin/departments.html'

    def get(self, request):
        depts = Department.objects.annotate(
            emp_count=Count('employees')
        ).prefetch_related('positions').order_by('name')
        return render(request, self.template_name, {
            'departments': depts,
            'all_users': User.objects.filter(is_active=True).order_by('first_name'),
        })


class DepartmentCreateView(AdminRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        description = request.POST.get('description', '')
        head_id = request.POST.get('head')
        if not name or not code:
            messages.error(request, "Name and code are required.")
            return redirect('sysadmin:departments')
        try:
            head = User.objects.get(pk=head_id) if head_id else None
            dept = Department.objects.create(name=name, code=code, description=description, head=head)
            messages.success(request, f"Department '{dept.name}' created.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
        return redirect('sysadmin:departments')


class DepartmentEditView(AdminRequiredMixin, View):
    def post(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        dept.name = request.POST.get('name', dept.name).strip()
        dept.description = request.POST.get('description', dept.description)
        head_id = request.POST.get('head')
        dept.head = User.objects.filter(pk=head_id).first() if head_id else None
        try:
            dept.save()
            messages.success(request, f"Department '{dept.name}' updated.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
        return redirect('sysadmin:departments')


class DepartmentToggleView(AdminRequiredMixin, View):
    def post(self, request, pk):
        dept = get_object_or_404(Department, pk=pk)
        dept.is_active = not dept.is_active
        dept.save(update_fields=['is_active'])
        state = 'activated' if dept.is_active else 'deactivated'
        messages.success(request, f"Department '{dept.name}' {state}.")
        return redirect('sysadmin:departments')


class LeaveTypeManagementView(AdminRequiredMixin, View):
    template_name = 'sysadmin/leave_types.html'

    def get(self, request):
        leave_types = LeaveType.objects.annotate(requests_count=Count('requests')).order_by('name')
        return render(request, self.template_name, {'leave_types': leave_types})


class LeaveTypeCreateView(AdminRequiredMixin, View):
    def post(self, request):
        try:
            LeaveType.objects.create(
                name=request.POST.get('name', '').strip(),
                code=request.POST.get('code', '').strip().upper(),
                description=request.POST.get('description', ''),
                max_days_per_year=int(request.POST.get('max_days', 14)),
                requires_documentation=bool(request.POST.get('requires_documentation')),
                is_paid=bool(request.POST.get('is_paid')),
            )
            messages.success(request, "Leave type created.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
        return redirect('sysadmin:leave_types')


class LeaveTypeEditView(AdminRequiredMixin, View):
    def post(self, request, pk):
        lt = get_object_or_404(LeaveType, pk=pk)
        lt.name = request.POST.get('name', lt.name).strip()
        lt.description = request.POST.get('description', lt.description)
        lt.max_days_per_year = int(request.POST.get('max_days', lt.max_days_per_year))
        lt.requires_documentation = bool(request.POST.get('requires_documentation'))
        lt.is_paid = bool(request.POST.get('is_paid'))
        try:
            lt.save()
            messages.success(request, f"Leave type '{lt.name}' updated.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
        return redirect('sysadmin:leave_types')


class LeaveTypeToggleView(AdminRequiredMixin, View):
    def post(self, request, pk):
        lt = get_object_or_404(LeaveType, pk=pk)
        lt.is_active = not lt.is_active
        lt.save(update_fields=['is_active'])
        messages.success(request, f"Leave type '{lt.name}' {'enabled' if lt.is_active else 'disabled'}.")
        return redirect('sysadmin:leave_types')


class ShiftTemplateManagementView(AdminRequiredMixin, View):
    template_name = 'sysadmin/shift_templates.html'

    def get(self, request):
        templates = ShiftTemplate.objects.annotate(assign_count=Count('assignments')).order_by('start_time')
        return render(request, self.template_name, {'templates': templates})


class ShiftTemplateCreateView(AdminRequiredMixin, View):
    def post(self, request):
        try:
            ShiftTemplate.objects.create(
                name=request.POST.get('name', '').strip(),
                start_time=request.POST.get('start_time'),
                end_time=request.POST.get('end_time'),
                description=request.POST.get('description', ''),
                color=request.POST.get('color', '#3B82F6'),
            )
            messages.success(request, "Shift template created.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
        return redirect('sysadmin:shift_templates')


class ShiftTemplateEditView(AdminRequiredMixin, View):
    def post(self, request, pk):
        tmpl = get_object_or_404(ShiftTemplate, pk=pk)
        tmpl.name = request.POST.get('name', tmpl.name).strip()
        tmpl.start_time = request.POST.get('start_time', tmpl.start_time)
        tmpl.end_time = request.POST.get('end_time', tmpl.end_time)
        tmpl.description = request.POST.get('description', tmpl.description)
        tmpl.color = request.POST.get('color', tmpl.color)
        try:
            tmpl.save()
            messages.success(request, f"Shift template '{tmpl.name}' updated.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
        return redirect('sysadmin:shift_templates')


class ShiftTemplateDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        tmpl = get_object_or_404(ShiftTemplate, pk=pk)
        if tmpl.assignments.exists():
            messages.error(request, f"Cannot delete '{tmpl.name}' — it has existing shift assignments.")
        else:
            name = tmpl.name
            tmpl.delete()
            messages.success(request, f"Shift template '{name}' deleted.")
        return redirect('sysadmin:shift_templates')


class SupportCategoryView(AdminRequiredMixin, View):
    template_name = 'sysadmin/support_categories.html'

    def get(self, request):
        cats = SupportCategory.objects.annotate(ticket_count=Count('supportticket')).order_by('name')
        return render(request, self.template_name, {'categories': cats})

    def post(self, request):
        action = request.POST.get('action')
        if action == 'create':
            try:
                SupportCategory.objects.create(
                    name=request.POST.get('name', '').strip(),
                    icon=request.POST.get('icon', 'help-circle').strip(),
                )
                messages.success(request, "Category created.")
            except Exception as e:
                messages.error(request, f"Error: {e}")
        elif action == 'delete':
            pk = request.POST.get('pk')
            cat = get_object_or_404(SupportCategory, pk=pk)
            if cat.supportticket_set.exists():
                messages.error(request, f"Cannot delete '{cat.name}' — it has existing tickets.")
            else:
                cat.delete()
                messages.success(request, "Category deleted.")
        return redirect('sysadmin:support_cats')


class SystemInfoView(AdminRequiredMixin, View):
    template_name = 'sysadmin/system_info.html'

    def get(self, request):
        import sys, django
        from django.conf import settings as dj_settings

        ctx = {
            'python_version': sys.version,
            'django_version': django.__version__,
            'database_engine': dj_settings.DATABASES['default']['ENGINE'].split('.')[-1],
            'database_name': dj_settings.DATABASES['default']['NAME'],
            'debug_mode': dj_settings.DEBUG,
            'installed_apps': dj_settings.INSTALLED_APPS,
            'time_zone': dj_settings.TIME_ZONE,
            'language_code': dj_settings.LANGUAGE_CODE,
            'media_root': str(dj_settings.MEDIA_ROOT),
            'static_root': str(getattr(dj_settings, 'STATIC_ROOT', 'Not configured')),
            'allowed_hosts': dj_settings.ALLOWED_HOSTS,
        }
        return render(request, self.template_name, ctx)


class BulkActionsView(AdminRequiredMixin, View):
    template_name = 'sysadmin/bulk_actions.html'

    def get(self, request):
        return render(request, self.template_name, {
            'terminated_employees': Employee.objects.filter(
                status__in=['terminated', 'fired']
            ).select_related('user', 'department').order_by('-termination_date'),
        })

    def post(self, request):
        action = request.POST.get('bulk_action')

        if action == 'notify_all':
            title = request.POST.get('title', '').strip()
            message = request.POST.get('message', '').strip()
            if not title or not message:
                messages.error(request, "Title and message are required.")
                return redirect('sysadmin:bulk_actions')
            recipients = User.objects.filter(is_active=True)
            Notification.send_bulk(
                recipients=recipients,
                notification_type='system',
                title=title,
                message=message,
                sender=request.user,
            )
            messages.success(request, f"Notification sent to {recipients.count()} users.")

        elif action == 'reset_leave_balances':
            annual = float(request.POST.get('annual_days', 21))
            sick = float(request.POST.get('sick_days', 14))
            count = Employee.objects.filter(status='active').update(
                annual_leave_balance=annual,
                sick_leave_balance=sick,
            )
            messages.success(request, f"Leave balances reset for {count} active employees.")

        elif action == 'clear_old_notifications':
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(days=90)
            deleted, _ = Notification.objects.filter(
                created_at__lt=cutoff, is_read=True
            ).delete()
            messages.success(request, f"Deleted {deleted} old read notifications (older than 90 days).")

        return redirect('sysadmin:bulk_actions')
