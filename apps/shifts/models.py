"""shifts/models.py — Shift & Schedule Management"""
from django.db import models
from django.conf import settings


class ShiftTemplate(models.Model):
    name = models.CharField(max_length=50, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.CharField(max_length=200, blank=True)
    color = models.CharField(max_length=7, default='#3B82F6', help_text="Hex color for calendar")

    class Meta:
        db_table = 'shift_templates'
        ordering = ['start_time']

    def __str__(self):
        return f"{self.name} ({self.start_time}–{self.end_time})"


class ShiftAssignment(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shift_assignments', db_index=True
    )
    shift = models.ForeignKey(ShiftTemplate, on_delete=models.PROTECT, related_name='assignments')
    date = models.DateField(db_index=True)
    notes = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_shifts'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shift_assignments'
        unique_together = [('employee', 'date')]
        ordering = ['date', 'employee']

    def __str__(self):
        return f"{self.employee} | {self.date} | {self.shift.name}"
