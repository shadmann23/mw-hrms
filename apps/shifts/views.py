"""shifts/views.py"""
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.generic import TemplateView
from django.views import View
from django.http import JsonResponse

from apps.shifts.models import ShiftAssignment, ShiftTemplate
from apps.accounts.decorators import SupervisorRequiredMixin
from apps.employees.models import Employee

User = get_user_model()


class ShiftCalendarView(LoginRequiredMixin, TemplateView):
    template_name = 'shifts/calendar.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['shifts'] = ShiftTemplate.objects.all()

        # Build employee list for assignment panel
        user = self.request.user
        if user.is_admin:
            ctx['assignable_employees'] = User.objects.filter(is_active=True).exclude(pk=user.pk).order_by('first_name')
        elif user.is_supervisor:
            # Get users who are subordinates (Employee.supervisor = this user)
            sub_user_ids = Employee.objects.filter(supervisor=user).values_list('user_id', flat=True)
            ctx['assignable_employees'] = User.objects.filter(pk__in=sub_user_ids, is_active=True).order_by('first_name')
        else:
            ctx['assignable_employees'] = User.objects.none()
        return ctx


class ShiftEventsAPIView(LoginRequiredMixin, View):
    """Returns JSON events for FullCalendar."""
    def get(self, request):
        user = request.user
        start = request.GET.get('start', '')
        end = request.GET.get('end', '')

        qs = ShiftAssignment.objects.select_related('shift', 'employee')

        if user.is_employee and not user.is_supervisor and not user.is_admin:
            qs = qs.filter(employee=user)
        elif user.is_supervisor and not user.is_admin:
            sub_user_ids = Employee.objects.filter(supervisor=user).values_list('user_id', flat=True)
            qs = qs.filter(employee__in=list(sub_user_ids) + [user.pk])

        if start:
            qs = qs.filter(date__gte=start[:10])
        if end:
            qs = qs.filter(date__lte=end[:10])

        events = []
        for a in qs:
            title = a.shift.name
            if user.is_admin or user.is_supervisor:
                title = f"{a.employee.get_full_name()} — {a.shift.name}"
            events.append({
                'id': a.pk,
                'title': title,
                'start': f"{a.date}T{a.shift.start_time}",
                'end': f"{a.date}T{a.shift.end_time}",
                'color': a.shift.color,
                'extendedProps': {
                    'employee': a.employee.get_full_name(),
                    'shift': a.shift.name,
                    'notes': a.notes or '',
                },
            })
        return JsonResponse(events, safe=False)


class ShiftAssignView(SupervisorRequiredMixin, View):
    def post(self, request):
        employee_id = request.POST.get('employee')
        shift_id = request.POST.get('shift')
        date = request.POST.get('date')
        notes = request.POST.get('notes', '')

        if not employee_id or not shift_id or not date:
            messages.error(request, "Please fill in all fields: employee, shift, and date.")
            return redirect('shifts:calendar')

        try:
            employee = User.objects.get(pk=employee_id)
            shift = ShiftTemplate.objects.get(pk=shift_id)
            obj, created = ShiftAssignment.objects.update_or_create(
                employee=employee, date=date,
                defaults={'shift': shift, 'notes': notes, 'created_by': request.user}
            )
            action = 'assigned' if created else 'updated'
            messages.success(request, f"Shift {action} for {employee.get_full_name()} on {date}.")
        except User.DoesNotExist:
            messages.error(request, "Employee not found.")
        except ShiftTemplate.DoesNotExist:
            messages.error(request, "Shift template not found.")
        except Exception as e:
            messages.error(request, f"Could not assign shift: {e}")

        return redirect('shifts:calendar')
