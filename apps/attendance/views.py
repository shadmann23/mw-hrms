"""attendance/views.py"""
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.attendance.models import AttendanceRecord

User = get_user_model()


def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')


class AttendanceCheckInView(LoginRequiredMixin, View):
    def post(self, request):
        today = timezone.localdate()
        record, created = AttendanceRecord.objects.get_or_create(
            employee=request.user,
            date=today,
            defaults={'ip_address': _get_ip(request)},
        )
        if not created and record.check_in:
            messages.warning(request, "You have already checked in today.")
        else:
            record.check_in  = timezone.now()
            record.ip_address = _get_ip(request)
            record.save(update_fields=['check_in', 'ip_address'])
            messages.success(request, f"Check-in recorded at {record.check_in.strftime('%H:%M')}.")
        return redirect(request.user.get_dashboard_url())


class AttendanceCheckOutView(LoginRequiredMixin, View):
    def post(self, request):
        today = timezone.localdate()
        try:
            record = AttendanceRecord.objects.get(employee=request.user, date=today)
        except AttendanceRecord.DoesNotExist:
            messages.error(request, "No check-in found for today. Please check in first.")
            return redirect(request.user.get_dashboard_url())

        if not record.check_in:
            messages.error(request, "You must check in before checking out.")
        elif record.check_out:
            messages.warning(request, "You have already checked out today.")
        else:
            record.check_out = timezone.now()
            record.save()
            hours = record.working_hours or 0
            messages.success(request, f"Check-out recorded. You worked {hours}h today.")
        return redirect(request.user.get_dashboard_url())


class AttendanceHistoryView(LoginRequiredMixin, ListView):
    model = AttendanceRecord
    template_name = 'attendance/history.html'
    context_object_name = 'records'
    paginate_by = 31

    def get_queryset(self):
        today = timezone.localdate()
        # Default to current month/year if not supplied
        month = self.request.GET.get('month') or str(today.month)
        year  = self.request.GET.get('year')  or str(today.year)
        return AttendanceRecord.objects.filter(
            employee=self.request.user,
            date__month=month,
            date__year=year,
        ).order_by('-date')

    def get_context_data(self, **kwargs):
        ctx   = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month = int(self.request.GET.get('month') or today.month)
        year  = int(self.request.GET.get('year')  or today.year)

        month_records = AttendanceRecord.objects.filter(
            employee=self.request.user,
            date__month=month,
            date__year=year,
        )
        ctx.update({
            'present_count':  month_records.filter(status__in=['present', 'late']).count(),
            'late_count':     month_records.filter(status='late').count(),
            'half_day_count': month_records.filter(status='half_day').count(),
            'today_record':   AttendanceRecord.objects.filter(
                employee=self.request.user, date=today
            ).first(),
            'current_month': month,
            'current_year':  year,
            'year_range': range(today.year - 4, today.year + 2),
            'month_choices': [
                (1,'January'),(2,'February'),(3,'March'),(4,'April'),
                (5,'May'),(6,'June'),(7,'July'),(8,'August'),
                (9,'September'),(10,'October'),(11,'November'),(12,'December'),
            ],
        })
        return ctx


class AdminAttendanceReportView(LoginRequiredMixin, TemplateView):
    template_name = 'attendance/admin_report.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        # Allow admins and supervisors; also allow superusers
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        role_name = getattr(request.user, 'role_name', None)
        if role_name not in ('admin', 'supervisor'):
            messages.error(request, "Access denied. Admins and supervisors only.")
            return redirect(request.user.get_dashboard_url())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()

        # Parse selected date
        date_str = self.request.GET.get('date')
        if date_str:
            try:
                from datetime import date as date_cls
                display_date = date_cls.fromisoformat(date_str)
            except ValueError:
                display_date = today
        else:
            display_date = today

        # Records for that date
        records = (
            AttendanceRecord.objects
            .filter(date=display_date)
            .select_related('employee', 'employee__employee_profile')
            .order_by('employee__first_name', 'employee__last_name')
        )

        # For supervisors, only show their team's records
        viewer = self.request.user
        if not viewer.is_admin and not viewer.is_superuser:
            from apps.employees.models import Employee
            team_user_ids = Employee.objects.filter(
                supervisor=viewer
            ).values_list('user_id', flat=True)
            records = records.filter(employee__in=team_user_ids)
            active_employees = User.objects.filter(
                pk__in=team_user_ids, is_active=True
            )
        else:
            # All active non-superuser employees
            active_employees = User.objects.filter(
                is_active=True, is_superuser=False
            ).exclude(role__isnull=True)

        total_active = active_employees.count()
        checked_in_ids = set(records.values_list('employee_id', flat=True))

        # Employees with NO record for this date = absent
        absent_employees = active_employees.exclude(pk__in=checked_in_ids)

        present_count = records.filter(status__in=['present', 'late', 'half_day']).count()
        late_count    = records.filter(status='late').count()
        absent_count  = absent_employees.count()

        ctx.update({
            'today_records':    records,
            'absent_employees': absent_employees.select_related('employee_profile'),
            'display_date':     display_date,
            'selected_date':    display_date.isoformat(),
            'present_count':    present_count,
            'late_count':       late_count,
            'absent_count':     absent_count,
            'total_active':     total_active,
            'is_today':         display_date == today,
        })
        return ctx
