"""accounts/views.py"""
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.views import View
from django.views.generic import TemplateView, ListView
from django.utils import timezone

from apps.accounts.forms import LoginForm, RegisterForm, AdminCreateUserForm, AdminEditUserForm
from apps.accounts.models import Role
from apps.accounts.decorators import AdminRequiredMixin
from apps.leaves.models import LeaveRequest
from apps.attendance.models import AttendanceRecord
from apps.notices.models import Notice
from apps.notifications.models import Notification
from apps.support.models import SupportTicket

User = get_user_model()


def _get_active_employee_count():
    from apps.employees.models import Employee
    return Employee.objects.filter(status__in=['active', 'on_leave']).count()


def _auto_create_employee(user):
    """
    Creates a minimal Employee profile for a user if one doesn't exist yet.
    Called when an admin approves a self-registered account.
    Returns (employee, created).
    """
    from apps.employees.models import Employee
    import uuid

    if hasattr(user, 'employee_profile'):
        return user.employee_profile, False

    # Generate a unique employee ID
    base = f"EMP-{user.pk:04d}"
    emp_id = base
    counter = 1
    while Employee.objects.filter(employee_id=emp_id).exists():
        emp_id = f"{base}-{counter}"
        counter += 1

    employee = Employee.objects.create(
        user=user,
        employee_id=emp_id,
        hire_date=timezone.localdate(),
    )
    return employee, True


class DashboardRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect(request.user.get_dashboard_url())


class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(request.user.get_dashboard_url())
        return render(request, self.template_name, {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = authenticate(request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'])
            if user and user.is_active:
                login(request, user)
                xff = request.META.get('HTTP_X_FORWARDED_FOR')
                user.last_login_ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
                user.save(update_fields=['last_login_ip'])
                messages.success(request, f"Welcome back, {user.first_name}!")
                return redirect(request.GET.get('next', user.get_dashboard_url()))
            elif user and not user.is_active:
                messages.error(request, "Your account is pending approval by an HR Administrator.")
            else:
                messages.error(request, "Invalid username or password.")
        return render(request, self.template_name, {'form': form})


class LogoutView(LoginRequiredMixin, View):
    def post(self, request):
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect('accounts:login')

    def get(self, request):
        logout(request)
        return redirect('accounts:login')


class RegisterView(View):
    template_name = 'accounts/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(request.user.get_dashboard_url())
        return render(request, self.template_name, {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            admins = User.objects.filter(role__name=Role.ADMIN, is_active=True)
            Notification.send_bulk(
                recipients=admins,
                notification_type='system',
                title='New Account Registration',
                message=f"{user.get_full_name()} ({user.username}) has registered and is awaiting approval.",
                link='/accounts/users/',
            )
            messages.success(request, "Account created! Awaiting HR Administrator approval before you can log in.")
            return redirect('accounts:login')
        return render(request, self.template_name, {'form': form})


# ── User Management ─────────────────────────────────────────────

class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.select_related('role').order_by('-date_joined')
        q      = self.request.GET.get('q')
        role   = self.request.GET.get('role')
        status = self.request.GET.get('status')
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                Q(username__icontains=q)   | Q(email__icontains=q)
            )
        if role:
            qs = qs.filter(role__name=role)
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['roles'] = Role.objects.all()
        ctx['pending_count'] = User.objects.filter(is_active=False).count()
        # Pass set of user PKs that already have an employee profile
        from apps.employees.models import Employee
        ctx['has_employee_profile'] = set(
            Employee.objects.values_list('user_id', flat=True)
        )
        return ctx


class UserCreateView(AdminRequiredMixin, View):
    """
    Redirects to the full Employee create form which creates both
    a User account AND an Employee profile in one step.
    """
    def get(self, request):
        messages.info(request, "Use the form below to create a full employee account.")
        return redirect('employees:create')


class UserEditView(AdminRequiredMixin, View):
    template_name = 'accounts/user_edit.html'

    def get(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        return render(request, self.template_name, {
            'form': AdminEditUserForm(instance=target),
            'target_user': target,
        })

    def post(self, request, pk):
        target   = get_object_or_404(User, pk=pk)
        old_role = target.role
        form     = AdminEditUserForm(request.POST, instance=target)
        if form.is_valid():
            updated = form.save()
            if old_role != updated.role:
                Notification.send(
                    recipient=updated,
                    notification_type='role_changed',
                    title='Your role has been updated',
                    message=f"Your system role has been changed to: {updated.role}",
                )
            messages.success(request, f"{updated.get_full_name()}'s account updated.")
            return redirect('accounts:user_list')
        return render(request, self.template_name, {'form': form, 'target_user': target})


class UserApproveView(AdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.is_active = True
        user.save(update_fields=['is_active'])

        # Auto-create a minimal Employee profile so the user
        # appears in the employees section immediately.
        employee, created = _auto_create_employee(user)

        Notification.send(
            recipient=user,
            notification_type='system',
            title='Account Approved',
            message='Your account has been approved. You can now log in.',
        )

        msg = f"{user.get_full_name()}'s account approved."
        if created:
            msg += f" Employee profile created (ID: {employee.employee_id}). Complete their details in the Employees section."
        messages.success(request, msg)
        return redirect('accounts:user_list')


class UserMakeEmployeeView(AdminRequiredMixin, View):
    """
    Manually creates an Employee profile for a user who already has
    a User account but no employee profile (edge case).
    Redirects to the employee update form to fill in the details.
    """
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        employee, created = _auto_create_employee(user)
        if created:
            messages.success(request, f"Employee profile created for {user.get_full_name()}. Please fill in their details.")
            return redirect('employees:update', pk=employee.pk)
        else:
            messages.info(request, f"{user.get_full_name()} already has an employee profile.")
            return redirect('employees:detail', pk=employee.pk)


class UserDeactivateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, "You cannot deactivate your own account.")
            return redirect('accounts:user_list')
        user.is_active = False
        user.save(update_fields=['is_active'])
        messages.success(request, f"{user.get_full_name()} deactivated.")
        return redirect('accounts:user_list')


# ── Dashboards ───────────────────────────────────────────────────

class AdminDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/dashboard_admin.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin and not request.user.is_superuser:
            return redirect(request.user.get_dashboard_url())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        user = self.request.user
        today_att = AttendanceRecord.objects.filter(employee=user, date=today).first()
        ctx.update({
            'total_employees': _get_active_employee_count(),
            'pending_leaves': LeaveRequest.objects.filter(status__in=['pending', 'approved_l1']).count(),
            'open_tickets': SupportTicket.objects.filter(status='open').count(),
            'present_today': AttendanceRecord.objects.filter(date=today).count(),
            'pending_registrations': User.objects.filter(is_active=False).count(),
            'recent_leaves': LeaveRequest.objects.filter(
                status__in=['pending', 'approved_l1']
            ).select_related('employee', 'leave_type').order_by('-applied_at')[:5],
            'recent_notices': Notice.objects.filter(is_active=True).order_by('-created_at')[:5],
            'today_attendance': today_att,
        })
        return ctx


class SupervisorDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/dashboard_supervisor.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_role('admin', 'supervisor') and not request.user.is_superuser:
            return redirect(request.user.get_dashboard_url())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        user  = self.request.user
        from apps.employees.models import Employee
        from apps.teams.models import TeamMembership
        # Direct subordinates
        sub_user_ids = set(Employee.objects.filter(supervisor=user).values_list('user_id', flat=True))
        # Team members
        team_member_ids = set(TeamMembership.objects.filter(
            team__supervisor=user, is_active=True
        ).values_list('member_id', flat=True))
        all_team_user_ids = list(sub_user_ids | team_member_ids)
        today_att = AttendanceRecord.objects.filter(employee=user, date=today).first()
        ctx.update({
            'team_count': len(all_team_user_ids),
            'pending_leave_approvals': LeaveRequest.objects.filter(
                status='pending', employee__in=all_team_user_ids).count(),
            'team_present_today': AttendanceRecord.objects.filter(
                date=today, employee__in=all_team_user_ids).count(),
            'recent_leave_requests': LeaveRequest.objects.filter(
                status='pending', employee__in=all_team_user_ids
            ).select_related('employee', 'leave_type').order_by('-applied_at')[:5],
            'notices': Notice.objects.filter(
                is_active=True, visibility__in=['all', 'supervisors']
            ).order_by('-publish_date')[:5],
            'today_attendance': today_att,
        })
        return ctx


class EmployeeDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/dashboard_employee.html'

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)
        today = timezone.localdate()
        user  = self.request.user
        today_att = AttendanceRecord.objects.filter(employee=user, date=today).first()
        ctx.update({
            'today_attendance': today_att,
            'pending_leaves': LeaveRequest.objects.filter(employee=user, status='pending').count(),
            'approved_leaves': LeaveRequest.objects.filter(employee=user, status='approved').count(),
            'recent_leaves': LeaveRequest.objects.filter(employee=user).order_by('-applied_at')[:5],
            'notices': Notice.objects.filter(
                is_active=True, visibility__in=['all', 'employees']
            ).order_by('-publish_date')[:5],
            'my_tickets': SupportTicket.objects.filter(requester=user).order_by('-created_at')[:5],
            'employee_profile': getattr(user, 'employee_profile', None),
        })
        return ctx
