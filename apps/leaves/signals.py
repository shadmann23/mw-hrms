"""leaves/signals.py"""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='leaves.LeaveRequest')
def notify_on_leave_status_change(sender, instance, created, **kwargs):
    if created:
        return
    from apps.notifications.models import Notification
    if instance.status in ('approved', 'rejected'):
        label = 'approved' if instance.status == 'approved' else 'rejected'
        Notification.send(
            recipient=instance.employee,
            notification_type=f'leave_{label}',
            title=f'Leave Request {label.capitalize()}',
            message=f'Your {instance.leave_type.name} request ({instance.total_days} day(s)) has been {label}.',
            link=f'/leaves/{instance.pk}/',
        )
