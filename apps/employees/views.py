"""employees/views.py"""
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.views.generic import ListView, DetailView, UpdateView
from django.views import View
from django.urls import reverse_lazy
from django.db import transaction
from django.utils import timezone

from apps.employees.models import Employee, Department, Position, EmployeeDocument
from apps.employees.forms import EmployeeCreateForm, EmployeeUpdateForm, SelfProfileUpdateForm
from apps.accounts.decorators import AdminRequiredMixin
from apps.accounts.models import Role
from apps.notifications.models import Notification

User = get_user_model()

ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
ALLOWED_DOC_TYPES   = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'image/jpeg', 'image/png',
]
MAX_AVATAR_SIZE = 2 * 1024 * 1024   # 2 MB
MAX_DOC_SIZE    = 10 * 1024 * 1024  # 10 MB


def _get_visible_employee_ids(user):
    """
    Returns a queryset of Employee PKs the given user is allowed to see.
    - Admin / superuser: all employees
    - Supervisor: all active employees in the company (they need full visibility to manage)
    - Employee: everyone (basic info only — template hides sensitive fields)
    """
    # Everyone sees all employees; sensitive info is hidden at template level
    return Employee.objects.values_list('pk', flat=True)


class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = 'employees/list.html'
    context_object_name = 'employees'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        visible_pks = _get_visible_employee_ids(user)

        # Default: only show active employees (exclude terminated/fired/suspended)
        # unless the admin explicitly filters by status
        status_filter = self.request.GET.get('status')

        qs = Employee.objects.filter(
            pk__in=visible_pks
        ).select_related('user', 'department', 'position').order_by('employee_id')

        if status_filter:
            qs = qs.filter(status=status_filter)
        else:
            # Default: hide terminated/fired employees
            qs = qs.filter(status__in=['active', 'on_leave', 'suspended'])

        dept = self.request.GET.get('department')
        q    = self.request.GET.get('q')

        if dept:
            qs = qs.filter(department__id=dept)
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) |
                Q(employee_id__icontains=q)      | Q(user__email__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['departments'] = Department.objects.filter(is_active=True)
        return ctx


class EmployeeDetailView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = 'employees/detail.html'
    context_object_name = 'employee'

    # All authenticated users can view any employee profile.
    # Sensitive sections are hidden via template flags.

    def get_context_data(self, **kwargs):
        ctx      = super().get_context_data(**kwargs)
        employee = self.get_object()
        viewer   = self.request.user
        is_own   = employee.user == viewer
        is_admin = viewer.is_admin or viewer.is_superuser

        # Check if viewer is a team-mate of the employee
        from apps.teams.models import TeamMembership
        shared_team = TeamMembership.objects.filter(
            team__memberships__member=viewer,
            member=employee.user,
            is_active=True,
        ).exists()

        # Supervisor can see their subordinates' details
        is_subordinate = Employee.objects.filter(
            pk=employee.pk, supervisor=viewer
        ).exists()

        can_see_sensitive = is_admin or is_own or is_subordinate

        # Documents: admin or self only
        can_see_docs  = is_admin or is_own
        ctx['documents']         = employee.documents.all() if can_see_docs else None
        ctx['can_manage_docs']   = is_admin
        ctx['doc_types']         = EmployeeDocument.DOC_TYPE_CHOICES
        ctx['is_own_profile']    = is_own
        ctx['can_see_sensitive'] = can_see_sensitive
        return ctx


class EmployeeProfileView(LoginRequiredMixin, View):
    template_name = 'employees/profile.html'

    def get(self, request):
        try:
            employee = Employee.objects.select_related(
                'department', 'position', 'supervisor'
            ).get(user=request.user)
        except Employee.DoesNotExist:
            employee = None
        documents = employee.documents.all() if employee else []
        return render(request, self.template_name, {
            'employee':  employee,
            'documents': documents,
            'doc_types': EmployeeDocument.DOC_TYPE_CHOICES,
        })


class EmployeeProfileEditView(LoginRequiredMixin, View):
    template_name = 'employees/profile_edit.html'

    def get(self, request):
        try:
            employee = Employee.objects.get(user=request.user)
            form = SelfProfileUpdateForm(instance=employee)
        except Employee.DoesNotExist:
            messages.warning(request, "Your employee profile hasn't been set up yet. Contact HR.")
            return redirect('employees:my_profile')
        return render(request, self.template_name, {'form': form, 'employee': employee})

    def post(self, request):
        try:
            employee = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            return redirect('employees:my_profile')
        form = SelfProfileUpdateForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            user = request.user
            user.first_name = form.cleaned_data.get('first_name', user.first_name)
            user.last_name  = form.cleaned_data.get('last_name',  user.last_name)
            user.email      = form.cleaned_data.get('email',      user.email)
            user.save(update_fields=['first_name', 'last_name', 'email'])
            messages.success(request, "Profile updated successfully.")
            return redirect('employees:my_profile')
        return render(request, self.template_name, {'form': form, 'employee': employee})


# ── Avatar Upload ──────────────────────────────────────────────

class AvatarUploadView(LoginRequiredMixin, View):
    def post(self, request):
        avatar = request.FILES.get('avatar')
        if not avatar:
            messages.error(request, "No file selected.")
            return redirect('employees:my_profile')
        if avatar.content_type not in ALLOWED_IMAGE_TYPES:
            messages.error(request, "Invalid file type. Please upload a JPEG, PNG, WebP, or GIF.")
            return redirect('employees:my_profile')
        if avatar.size > MAX_AVATAR_SIZE:
            messages.error(request, "Image too large. Maximum size is 2 MB.")
            return redirect('employees:my_profile')
        try:
            employee = request.user.employee_profile
        except Employee.DoesNotExist:
            messages.error(request, "No employee profile found.")
            return redirect('employees:my_profile')
        if employee.avatar:
            employee.avatar.delete(save=False)
        employee.avatar = avatar
        employee.save(update_fields=['avatar'])
        messages.success(request, "Profile picture updated.")
        return redirect('employees:my_profile')


# ── Document Upload / Delete ───────────────────────────────────

class DocumentUploadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        if not request.user.is_admin and employee.user != request.user:
            messages.error(request, "Access denied.")
            return redirect('employees:detail', pk=pk)
        uploaded_file = request.FILES.get('document')
        title    = request.POST.get('title', '').strip()
        doc_type = request.POST.get('document_type', 'other')
        notes    = request.POST.get('notes', '').strip()
        if not uploaded_file:
            messages.error(request, "No file selected.")
            return redirect('employees:detail', pk=pk)
        if not title:
            messages.error(request, "Please provide a document title.")
            return redirect('employees:detail', pk=pk)
        if uploaded_file.content_type not in ALLOWED_DOC_TYPES:
            messages.error(request, "Invalid file type. Allowed: PDF, Word, Excel, JPEG, PNG.")
            return redirect('employees:detail', pk=pk)
        if uploaded_file.size > MAX_DOC_SIZE:
            messages.error(request, "File too large. Maximum size is 10 MB.")
            return redirect('employees:detail', pk=pk)
        EmployeeDocument.objects.create(
            employee=employee, title=title, document_type=doc_type,
            file=uploaded_file, notes=notes, uploaded_by=request.user,
        )
        messages.success(request, f"Document '{title}' uploaded successfully.")
        if employee.user == request.user:
            return redirect('employees:my_profile')
        return redirect('employees:detail', pk=pk)


class DocumentDeleteView(LoginRequiredMixin, View):
    def post(self, request, doc_pk):
        doc = get_object_or_404(EmployeeDocument, pk=doc_pk)
        if not request.user.is_admin and doc.employee.user != request.user:
            messages.error(request, "Access denied.")
            return redirect('employees:my_profile')
        employee_pk = doc.employee.pk
        is_own      = doc.employee.user == request.user
        title       = doc.title
        doc.file.delete(save=False)
        doc.delete()
        messages.success(request, f"Document '{title}' deleted.")
        if is_own:
            return redirect('employees:my_profile')
        return redirect('employees:detail', pk=employee_pk)


# ── Admin CRUD ─────────────────────────────────────────────────

class EmployeeCreateView(AdminRequiredMixin, View):
    template_name = 'employees/create.html'

    def get(self, request):
        return render(request, self.template_name, {'form': EmployeeCreateForm()})

    def post(self, request):
        form = EmployeeCreateForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        role=Role.objects.get(name=Role.EMPLOYEE),
                    )
                    employee = form.save(commit=False)
                    employee.user       = user
                    employee.created_by = request.user
                    employee.save()
                messages.success(request, f"Employee {employee.employee_id} created successfully.")
                return redirect('employees:list')
            except Exception as e:
                messages.error(request, f"Error creating employee: {e}")
        return render(request, self.template_name, {'form': form})


class EmployeeUpdateView(AdminRequiredMixin, UpdateView):
    model         = Employee
    form_class    = EmployeeUpdateForm
    template_name = 'employees/update.html'

    def get_success_url(self):
        return reverse_lazy('employees:detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Employee record updated.")
        return super().form_valid(form)


class EmployeeTerminateView(AdminRequiredMixin, View):
    template_name = 'employees/terminate.html'

    def get(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        if employee.status in ('terminated', 'fired'):
            messages.warning(request, f"{employee.full_name} is already terminated.")
            return redirect('employees:detail', pk=pk)
        return render(request, self.template_name, {'employee': employee})

    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        action   = request.POST.get('action')
        reason   = request.POST.get('termination_reason', 'other')
        notes    = request.POST.get('termination_notes', '')
        if action not in ('fire', 'terminate'):
            messages.error(request, "Invalid action.")
            return redirect('employees:detail', pk=pk)
        with transaction.atomic():
            employee.status             = 'fired' if action == 'fire' else 'terminated'
            employee.termination_date   = timezone.localdate()
            employee.termination_reason = 'fired' if action == 'fire' else reason
            employee.termination_notes  = notes
            employee.save(update_fields=['status','termination_date','termination_reason','termination_notes'])
            employee.user.is_active = False
            employee.user.save(update_fields=['is_active'])
            from apps.leaves.models import LeaveRequest
            cancelled = LeaveRequest.objects.filter(
                employee=employee.user, status__in=['pending','approved_l1']
            ).update(status='cancelled')
            label = 'fired' if action == 'fire' else 'terminated'
            msg   = f"{employee.full_name} has been {label}. Login disabled."
            if cancelled:
                msg += f" {cancelled} pending leave request(s) cancelled."
            messages.success(request, msg)
        return redirect('employees:list')


class EmployeeDeleteView(AdminRequiredMixin, View):
    template_name = 'employees/delete.html'

    def get(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        return render(request, self.template_name, {'employee': employee})

    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        confirm  = request.POST.get('confirm_delete')
        if confirm != employee.employee_id:
            messages.error(request, f"Confirmation failed. Type the Employee ID: {employee.employee_id}")
            return render(request, self.template_name, {'employee': employee})
        full_name = employee.full_name
        emp_id    = employee.employee_id
        with transaction.atomic():
            user = employee.user
            employee.delete()
            user.delete()
        messages.success(request, f"Employee {emp_id} ({full_name}) permanently deleted.")
        return redirect('employees:list')


class EmployeeDeactivateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        employee.user.is_active = False
        employee.user.save(update_fields=['is_active'])
        employee.status = 'suspended'
        employee.save(update_fields=['status'])
        messages.success(request, f"{employee.full_name} has been suspended.")
        return redirect('employees:detail', pk=pk)


class EmployeeReactivateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        employee.user.is_active = True
        employee.user.save(update_fields=['is_active'])
        employee.status             = 'active'
        employee.termination_date   = None
        employee.termination_reason = ''
        employee.termination_notes  = ''
        employee.save(update_fields=['status','termination_date','termination_reason','termination_notes'])
        Notification.send(
            recipient=employee.user,
            notification_type='system',
            title='Account Reactivated',
            message='Your employee account has been reactivated. You can now log in.',
        )
        messages.success(request, f"{employee.full_name} has been reactivated.")
        return redirect('employees:detail', pk=pk)
