"""attendance/models.py — Attendance Records"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError


class AttendanceRecord(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('on_leave', 'On Leave'),
    ]

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='attendance_records', db_index=True
    )
    date = models.DateField(default=timezone.localdate, db_index=True)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    working_hours = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attendance_records'
        unique_together = [('employee', 'date')]
        ordering = ['-date', 'employee']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date', 'status']),
        ]

    def __str__(self):
        return f"{self.employee} | {self.date} | {self.status}"

    def save(self, *args, **kwargs):
        # Calculate working hours and status when both times present
        if self.check_in and self.check_out:
            if self.check_out > self.check_in:
                delta = self.check_out - self.check_in
                self.working_hours = round(delta.total_seconds() / 3600, 2)
                if float(self.working_hours) < 4:
                    self.status = 'half_day'
                elif self.check_in.hour > 9 or (self.check_in.hour == 9 and self.check_in.minute > 15):
                    self.status = 'late'
                else:
                    self.status = 'present'
        elif self.check_in and not self.check_out:
            self.status = 'present'
        # Do NOT call full_clean() here — it breaks partial saves (check-in only)
        super().save(*args, **kwargs)

    @property
    def is_checked_in(self):
        return self.check_in is not None and self.check_out is None

    @property
    def is_complete(self):
        return self.check_in is not None and self.check_out is not None
