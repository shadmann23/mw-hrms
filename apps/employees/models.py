"""employees/models.py"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='headed_departments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'departments'
        ordering = ['name']

    def __str__(self):
        return f"{self.code} — {self.name}"


class Position(models.Model):
    title = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='positions')
    level = models.PositiveSmallIntegerField(default=1)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'positions'
        unique_together = [('title', 'department')]
        ordering = ['department', 'level', 'title']

    def __str__(self):
        return f"{self.title} ({self.department.code})"


class Employee(models.Model):
    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full Time'), ('part_time', 'Part Time'),
        ('contract', 'Contract'), ('intern', 'Intern'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'), ('on_leave', 'On Leave'),
        ('terminated', 'Terminated'), ('suspended', 'Suspended'),
        ('fired', 'Fired'),
    ]
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]

    TERMINATION_REASON_CHOICES = [
        ('resignation', 'Resignation'),
        ('fired', 'Terminated for Cause'),
        ('redundancy', 'Redundancy / Layoff'),
        ('contract_end', 'Contract Ended'),
        ('retirement', 'Retirement'),
        ('other', 'Other'),
    ]

    # Identity
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='employee_profile'
    )
    employee_id = models.CharField(max_length=20, unique=True, db_index=True)
    national_id = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    # Avatar — stored on the employee profile (separate from User.avatar)
    avatar = models.ImageField(upload_to='employee_avatars/', null=True, blank=True)

    # Job
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='employees')
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, related_name='employees')
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='subordinates'
    )
    hire_date = models.DateField(default=timezone.now)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='full_time')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    annual_leave_balance = models.DecimalField(max_digits=5, decimal_places=1, default=21.0)
    sick_leave_balance = models.DecimalField(max_digits=5, decimal_places=1, default=14.0)

    # Termination info
    termination_date = models.DateField(null=True, blank=True)
    termination_reason = models.CharField(
        max_length=20, choices=TERMINATION_REASON_CHOICES, blank=True
    )
    termination_notes = models.TextField(blank=True)

    # Bank
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=50, blank=True)

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_employees'
    )

    class Meta:
        db_table = 'employees'
        ordering = ['employee_id']
        indexes = [
            models.Index(fields=['department', 'status']),
            models.Index(fields=['supervisor']),
            models.Index(fields=['hire_date']),
        ]

    def __str__(self):
        return f"{self.employee_id} — {self.user.get_full_name()}"

    @property
    def full_name(self):
        return self.user.get_full_name()

    @property
    def email(self):
        return self.user.email

    @property
    def years_of_service(self):
        from datetime import date
        end = self.termination_date or date.today()
        delta = end - self.hire_date
        return round(delta.days / 365.25, 1)

    def get_avatar_url(self):
        """Returns the best available avatar URL, or None."""
        if self.avatar:
            return self.avatar.url
        if self.user.avatar:
            return self.user.avatar.url
        return None


class EmployeeDocument(models.Model):
    DOC_TYPE_CHOICES = [
        ('contract',    'Employment Contract'),
        ('id',          'ID / Passport'),
        ('certificate', 'Certificate / Degree'),
        ('nda',         'NDA / Agreement'),
        ('payslip',     'Payslip'),
        ('warning',     'Warning Letter'),
        ('other',       'Other'),
    ]

    employee    = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    title       = models.CharField(max_length=200)
    document_type = models.CharField(max_length=30, choices=DOC_TYPE_CHOICES, default='other')
    file        = models.FileField(upload_to='employee_documents/%Y/%m/')
    notes       = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='uploaded_documents'
    )
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'employee_documents'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.employee.employee_id} — {self.title}"

    @property
    def filename(self):
        import os
        return os.path.basename(self.file.name)

    @property
    def extension(self):
        import os
        return os.path.splitext(self.file.name)[1].lower().lstrip('.')
