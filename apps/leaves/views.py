"""leaves/views.py — Leave Request & Approval Views"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.views.generic import ListView, CreateView, DetailView
from django.views import View
from django.urls import reverse_lazy, reverse
from django.db import transaction

from apps.leaves.models import LeaveRequest, LeaveApproval
from apps.leaves.forms import LeaveRequestForm
from apps.notifications.models import Notification


class LeaveListView(LoginRequiredMixin, ListView):
    model = LeaveRequest
    template_name = 'leaves/list.html'
    context_object_name = 'leaves'
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        if user.has_role('admin'):
            qs = LeaveRequest.objects.all()
        elif user.has_role('supervisor'):
            # Supervisor sees own leaves + their subordinates' leaves
            sub_ids = user.subordinates.values_list('user_id', flat=True)
            qs = LeaveRequest.objects.filter(employee__in=list(sub_ids) + [user.pk])
        else:
            qs = LeaveRequest.objects.filter(employee=user)
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs.select_related('employee', 'leave_type').order_by('-applied_at')


class LeaveRequestCreateView(LoginRequiredMixin, CreateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'leaves/create.html'

    def form_valid(self, form):
        leave = form.save(commit=False)
        leave.employee = self.request.user
        # Calculate total_days before validation
        if leave.start_date and leave.end_date:
            delta = leave.end_date - leave.start_date
            leave.total_days = max(1, delta.days + 1)

        # Validate dates
        from django.utils import timezone
        if leave.end_date < leave.start_date:
            form.add_error('end_date', 'End date must be on or after start date.')
            return self.form_invalid(form)

        # Check leave balance
        try:
            profile = self.request.user.employee_profile
            if leave.leave_type.code == 'SL':
                balance = float(profile.sick_leave_balance)
            else:
                balance = float(profile.annual_leave_balance)
            if leave.total_days > balance:
                messages.error(self.request, f"Insufficient leave balance. You have {balance} days available.")
                return self.form_invalid(form)
        except Exception:
            pass

        leave.save()

        # Notify supervisor
        try:
            supervisor = self.request.user.employee_profile.supervisor
            if supervisor:
                Notification.send(
                    recipient=supervisor,
                    notification_type='leave_request',
                    title='New Leave Request',
                    message=f"{self.request.user.get_full_name()} submitted a {leave.leave_type.name} request ({leave.total_days} day(s)).",
                    sender=self.request.user,
                    link=reverse('leaves:detail', kwargs={'pk': leave.pk}),
                )
        except Exception:
            pass

        messages.success(self.request, "Leave request submitted successfully.")
        return redirect('leaves:list')


class LeaveDetailView(LoginRequiredMixin, DetailView):
    model = LeaveRequest
    template_name = 'leaves/detail.html'
    context_object_name = 'leave'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx['approvals'] = self.object.approvals.select_related('approver').all()
        ctx['can_approve'] = (
            self.request.user.has_role('admin', 'supervisor') and
            self.object.status in ('pending', 'approved_l1') and
            self.object.employee != self.request.user
        )
        return ctx


class LeaveApprovalView(LoginRequiredMixin, View):
    """Multi-level approval. Admin can approve at any level. Supervisor at L1."""

    def post(self, request, pk):
        leave = get_object_or_404(LeaveRequest, pk=pk)
        user = request.user

        if not user.has_role('admin', 'supervisor'):
            messages.error(request, "You are not authorized to approve leaves.")
            return redirect('leaves:list')

        if leave.status in ('approved', 'rejected', 'cancelled'):
            messages.warning(request, "This request has already been finalized.")
            return redirect('leaves:detail', pk=pk)

        action = request.POST.get('action')
        comments = request.POST.get('comments', '')

        if action not in ('approve', 'reject'):
            messages.error(request, "Please select Approve or Reject.")
            return redirect('leaves:detail', pk=pk)

        # Determine approval level
        if user.is_admin:
            level = 2
        else:
            level = 1

        with transaction.atomic():
            LeaveApproval.objects.create(
                leave_request=leave,
                approver=user,
                level=level,
                action=action,
                comments=comments,
            )

            if action == 'reject':
                leave.status = 'rejected'
                leave.save(update_fields=['status', 'updated_at'])
                msg = f"Your {leave.leave_type.name} leave request has been rejected by {user.get_full_name()}."
                notif_type = 'leave_rejected'

            elif user.is_admin:
                # Admin fully approves
                leave.status = 'approved'
                leave.save(update_fields=['status', 'updated_at'])
                # Deduct balance
                try:
                    profile = leave.employee.employee_profile
                    if leave.leave_type.code == 'SL':
                        profile.sick_leave_balance = max(0, float(profile.sick_leave_balance) - leave.total_days)
                    else:
                        profile.annual_leave_balance = max(0, float(profile.annual_leave_balance) - leave.total_days)
                    profile.save(update_fields=['annual_leave_balance', 'sick_leave_balance'])
                except Exception:
                    pass
                msg = f"Your {leave.leave_type.name} leave request has been fully approved."
                notif_type = 'leave_approved'

            else:
                # Supervisor L1 approval — escalate to admin
                leave.status = 'approved_l1'
                leave.save(update_fields=['status', 'updated_at'])
                msg = f"Your {leave.leave_type.name} leave has been approved by your supervisor and forwarded to HR."
                notif_type = 'leave_approved'
                # Notify all admins
                from django.contrib.auth import get_user_model
                User = get_user_model()
                admins = User.objects.filter(role__name='admin', is_active=True)
                Notification.send_bulk(
                    recipients=admins,
                    notification_type='leave_request',
                    title='Leave Awaiting Final Approval',
                    message=f"{leave.employee.get_full_name()}'s leave (L1 approved by {user.get_full_name()}) needs final HR approval.",
                    sender=user,
                    link=reverse('leaves:detail', kwargs={'pk': leave.pk}),
                )

            Notification.send(
                recipient=leave.employee,
                notification_type=notif_type,
                title='Leave Request Update',
                message=msg,
                sender=user,
                link=reverse('leaves:detail', kwargs={'pk': leave.pk}),
            )

        messages.success(request, f"Leave request {action}d successfully.")
        return redirect('leaves:list')


class LeaveCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        leave = get_object_or_404(LeaveRequest, pk=pk, employee=request.user)
        if leave.status not in ('pending', 'approved_l1'):
            messages.error(request, "Only pending requests can be cancelled.")
        else:
            leave.status = 'cancelled'
            leave.save(update_fields=['status', 'updated_at'])
            messages.success(request, "Leave request cancelled.")
        return redirect('leaves:list')
