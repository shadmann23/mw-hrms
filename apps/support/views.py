"""support/views.py"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, CreateView, DetailView
from django.views import View
from django.urls import reverse_lazy, reverse

from apps.support.models import SupportTicket, TicketResponse
from apps.support.forms import SupportTicketForm, TicketResponseForm
from apps.notifications.models import Notification
from django.contrib.auth import get_user_model


class TicketListView(LoginRequiredMixin, ListView):
    model = SupportTicket
    template_name = 'support/list.html'
    context_object_name = 'tickets'
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        if user.has_role('admin'):
            qs = SupportTicket.objects.all()
        else:
            qs = SupportTicket.objects.filter(requester=user)
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs.select_related('requester', 'category').order_by('-created_at')


class TicketCreateView(LoginRequiredMixin, CreateView):
    model = SupportTicket
    form_class = SupportTicketForm
    template_name = 'support/create.html'

    def form_valid(self, form):
        ticket = form.save(commit=False)
        ticket.requester = self.request.user
        ticket.save()
        # Notify admins
        User = get_user_model()
        admins = User.objects.filter(role__name='admin', is_active=True)
        Notification.send_bulk(
            recipients=admins,
            notification_type='ticket_response',
            title='New Support Ticket',
            message=f"#{ticket.ticket_number}: {ticket.subject} from {self.request.user.get_full_name()}",
            sender=self.request.user,
            link=reverse('support:detail', kwargs={'pk': ticket.pk}),
        )
        messages.success(self.request, f"Ticket #{ticket.ticket_number} submitted.")
        return redirect('support:list')


class TicketDetailView(LoginRequiredMixin, DetailView):
    model = SupportTicket
    template_name = 'support/detail.html'
    context_object_name = 'ticket'

    def dispatch(self, request, *args, **kwargs):
        ticket = self.get_object()
        if not request.user.has_role('admin') and ticket.requester != request.user:
            messages.error(request, "Access denied.")
            return redirect('support:list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['response_form'] = TicketResponseForm()
        show_internal = self.request.user.has_role('admin')
        ctx['responses'] = self.object.responses.filter(
            is_internal=False
        ) if not show_internal else self.object.responses.all()
        return ctx

    def post(self, request, *args, **kwargs):
        ticket = self.get_object()
        form = TicketResponseForm(request.POST)
        if form.is_valid():
            resp = form.save(commit=False)
            resp.ticket = ticket
            resp.responder = request.user
            if not request.user.has_role('admin'):
                resp.is_internal = False
            resp.save()
            # Update ticket status
            if request.user.has_role('admin') and ticket.status == 'open':
                ticket.status = 'in_progress'
                ticket.save(update_fields=['status'])
            # Notify requester if admin replied
            if request.user.has_role('admin') and not resp.is_internal:
                Notification.send(
                    recipient=ticket.requester,
                    notification_type='ticket_response',
                    title='Support Ticket Updated',
                    message=f"Your ticket #{ticket.ticket_number} received a response.",
                    sender=request.user,
                    link=reverse('support:detail', kwargs={'pk': ticket.pk}),
                )
            messages.success(request, "Response added.")
        return redirect('support:detail', pk=ticket.pk)


class TicketResolveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not request.user.has_role('admin'):
            messages.error(request, "Only admins can resolve tickets.")
            return redirect('support:list')
        ticket = get_object_or_404(SupportTicket, pk=pk)
        ticket.status = 'resolved'
        ticket.save()
        Notification.send(
            recipient=ticket.requester,
            notification_type='ticket_resolved',
            title='Ticket Resolved',
            message=f"Your ticket #{ticket.ticket_number} has been resolved.",
            sender=request.user,
            link=reverse('support:detail', kwargs={'pk': ticket.pk}),
        )
        messages.success(request, "Ticket resolved.")
        return redirect('support:detail', pk=pk)
