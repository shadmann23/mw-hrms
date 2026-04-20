"""notices/views.py"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone

from apps.notices.models import Notice
from apps.notices.forms import NoticeForm
from apps.accounts.decorators import AdminRequiredMixin
from apps.notifications.models import Notification
from django.contrib.auth import get_user_model


class NoticeListView(LoginRequiredMixin, ListView):
    model = Notice
    template_name = 'notices/list.html'
    context_object_name = 'notices'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        today = timezone.localdate()
        qs = Notice.objects.filter(
            is_active=True,
            publish_date__lte=today,
        ).order_by('-priority', '-publish_date')

        vis_filter = ['all']
        if user.is_admin or user.is_supervisor:
            vis_filter += ['supervisors', 'admin']
        elif user.is_employee:
            vis_filter += ['employees']

        return qs.filter(visibility__in=vis_filter)


class NoticeDetailView(LoginRequiredMixin, DetailView):
    model = Notice
    template_name = 'notices/detail.html'
    context_object_name = 'notice'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        self.object.views_count += 1
        self.object.save(update_fields=['views_count'])
        return response


class NoticeCreateView(AdminRequiredMixin, CreateView):
    model = Notice
    form_class = NoticeForm
    template_name = 'notices/create.html'
    success_url = reverse_lazy('notices:list')

    def form_valid(self, form):
        notice = form.save(commit=False)
        notice.created_by = self.request.user
        notice.save()
        # Notify all users
        User = get_user_model()
        recipients = User.objects.filter(is_active=True).exclude(pk=self.request.user.pk)
        Notification.send_bulk(
            recipients=recipients,
            notification_type='notice_posted',
            title='New Notice Posted',
            message=f"New notice: {notice.title}",
            sender=self.request.user,
            link=f'/notices/{notice.pk}/',
        )
        messages.success(self.request, "Notice posted and staff notified.")
        return redirect(self.success_url)
