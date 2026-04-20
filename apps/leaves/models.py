"""leaves/models.py — Leave Requests & Approvals"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError


class LeaveType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    max_days_per_year = models.PositiveSmallIntegerField(default=14)
    requires_documentation = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'leave_types'
        ordering = ['name']

    def __str__(self):
        return f"{self.code} — {self.name}"


class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved_l1', 'Approved (Level 1)'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='leave_requests', db_index=True
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name='requests')
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.PositiveSmallIntegerField(default=1)
    reason = models.TextField()
    attachment = models.FileField(upload_to='leave_attachments/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'leave_requests'
        ordering = ['-applied_at']
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['status', 'applied_at']),
        ]

    def __str__(self):
        return f"{self.employee} | {self.leave_type.code} | {self.start_date}–{self.end_date} | {self.status}"

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            from datetime import timedelta
            delta = self.end_date - self.start_date
            self.total_days = max(1, delta.days + 1)
        super().save(*args, **kwargs)


class LeaveApproval(models.Model):
    ACTION_CHOICES = [('approve', 'Approve'), ('reject', 'Reject')]

    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leave_approvals'
    )
    level = models.PositiveSmallIntegerField(default=1, help_text="1=Supervisor, 2=HR Admin")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    comments = models.TextField(blank=True)
    acted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'leave_approvals'
        # Removed unique_together so admin can add L2 approval after L1
        ordering = ['level', 'acted_at']

    def __str__(self):
        return f"L{self.level} {self.action} by {self.approver} on {self.leave_request}"
