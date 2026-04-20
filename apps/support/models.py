"""support/models.py — Help Desk / Support Requests"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class SupportCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, default='help-circle', help_text="Feather icon name")

    class Meta:
        db_table = 'support_categories'
        verbose_name_plural = 'Support Categories'

    def __str__(self):
        return self.name


class SupportTicket(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'), ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'), ('closed', 'Closed'),
    ]

    ticket_number = models.CharField(max_length=20, unique=True, editable=False)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets'
    )
    category = models.ForeignKey(SupportCategory, on_delete=models.SET_NULL, null=True)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_tickets'
    )
    attachment = models.FileField(upload_to='ticket_attachments/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'support_tickets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['status', 'priority']),
        ]

    def __str__(self):
        return f"#{self.ticket_number} — {self.subject}"

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            import random, string
            self.ticket_number = 'TKT-' + ''.join(random.choices(string.digits, k=8))
        if self.status == 'resolved' and not self.resolved_at:
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)


class TicketResponse(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='responses')
    responder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    is_internal = models.BooleanField(default=False, help_text="Internal admin-only note")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ticket_responses'
        ordering = ['created_at']

    def __str__(self):
        return f"Response by {self.responder} on #{self.ticket.ticket_number}"
