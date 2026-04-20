"""notifications/models.py — System Notifications"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    TYPE_CHOICES = [
        ('leave_request', 'Leave Request'),
        ('leave_approved', 'Leave Approved'),
        ('leave_rejected', 'Leave Rejected'),
        ('notice_posted', 'Notice Posted'),
        ('ticket_response', 'Ticket Response'),
        ('ticket_resolved', 'Ticket Resolved'),
        ('attendance', 'Attendance'),
        ('system', 'System'),
        ('role_changed', 'Role Changed'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notifications', db_index=True
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sent_notifications'
    )
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, db_index=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, help_text="URL to related resource")
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', 'created_at']),
        ]

    def __str__(self):
        status = 'read' if self.is_read else 'unread'
        return f"[{status}] {self.title} → {self.recipient}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @classmethod
    def send(cls, recipient, notification_type, title, message, sender=None, link=''):
        """Convenience factory method."""
        return cls.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
        )

    @classmethod
    def send_bulk(cls, recipients, notification_type, title, message, sender=None, link=''):
        notifications = [
            cls(
                recipient=r,
                sender=sender,
                notification_type=notification_type,
                title=title,
                message=message,
                link=link,
            ) for r in recipients
        ]
        cls.objects.bulk_create(notifications)
