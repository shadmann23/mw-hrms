"""
accounts/models.py
Custom User model with Role-Based Access Control
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Role(models.Model):
    ADMIN = 'admin'
    SUPERVISOR = 'supervisor'
    EMPLOYEE = 'employee'

    ROLE_CHOICES = [
        (ADMIN, 'HR Administrator'),
        (SUPERVISOR, 'Supervisor'),
        (EMPLOYEE, 'Employee'),
    ]

    name = models.CharField(max_length=50, unique=True, choices=ROLE_CHOICES)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'roles'
        ordering = ['name']

    def __str__(self):
        return self.get_name_display()

    @property
    def is_admin(self):
        return self.name == self.ADMIN

    @property
    def is_supervisor(self):
        return self.name == self.SUPERVISOR

    @property
    def is_employee(self):
        return self.name == self.EMPLOYEE


class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.ForeignKey(
        Role, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='users', db_index=True
    )
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role', 'is_active']),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"

    @property
    def role_name(self):
        return self.role.name if self.role else None

    @property
    def is_admin(self):
        return self.role_name == Role.ADMIN

    @property
    def is_supervisor(self):
        return self.role_name == Role.SUPERVISOR

    @property
    def is_employee(self):
        return self.role_name == Role.EMPLOYEE

    def has_role(self, *roles):
        return self.role_name in roles

    def get_dashboard_url(self):
        from django.urls import reverse
        role_map = {
            Role.ADMIN: 'dashboard:admin',
            Role.SUPERVISOR: 'dashboard:supervisor',
            Role.EMPLOYEE: 'dashboard:employee',
        }
        return reverse(role_map.get(self.role_name, 'dashboard:employee'))
