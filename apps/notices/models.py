"""notices/models.py — Company Notices & Announcements"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class Notice(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    VISIBILITY_CHOICES = [
        ('all', 'All Staff'),
        ('admin', 'HR Admins Only'),
        ('supervisors', 'Supervisors & Above'),
        ('employees', 'Employees Only'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='all')
    attachment = models.FileField(upload_to='notice_attachments/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    publish_date = models.DateField(default=timezone.localdate)
    expiry_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_notices'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'notices'
        ordering = ['-priority', '-publish_date']
        indexes = [
            models.Index(fields=['is_active', 'visibility']),
            models.Index(fields=['publish_date', 'expiry_date']),
        ]

    def __str__(self):
        return f"[{self.priority.upper()}] {self.title}"

    @property
    def is_expired(self):
        if self.expiry_date:
            return timezone.localdate() > self.expiry_date
        return False

    @property
    def is_visible(self):
        return self.is_active and not self.is_expired and self.publish_date <= timezone.localdate()
