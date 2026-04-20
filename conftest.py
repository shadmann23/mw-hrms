"""
conftest.py — Shared pytest fixtures for MilkWays HRMS test suite
Place this file in the project root (same level as manage.py)
"""
import pytest
from django.utils import timezone
from datetime import date, timedelta


# ─────────────────────────────────────────────
#  ROLES
# ─────────────────────────────────────────────

@pytest.fixture
def role_admin(db):
    from apps.accounts.models import Role
    role, _ = Role.objects.get_or_create(name=Role.ADMIN)
    return role

@pytest.fixture
def role_supervisor(db):
    from apps.accounts.models import Role
    role, _ = Role.objects.get_or_create(name=Role.SUPERVISOR)
    return role

@pytest.fixture
def role_employee(db):
    from apps.accounts.models import Role
    role, _ = Role.objects.get_or_create(name=Role.EMPLOYEE)
    return role


# ─────────────────────────────────────────────
#  USERS
# ─────────────────────────────────────────────

@pytest.fixture
def admin_user(db, role_admin):
    from apps.accounts.models import User
    user = User.objects.create_user(
        username='admin_user',
        email='admin@milkways.com',
        password='Admin@12345',
        first_name='Admin',
        last_name='User',
        role=role_admin,
        is_active=True,
    )
    return user

@pytest.fixture
def supervisor_user(db, role_supervisor):
    from apps.accounts.models import User
    user = User.objects.create_user(
        username='supervisor_user',
        email='supervisor@milkways.com',
        password='Super@12345',
        first_name='Super',
        last_name='Visor',
        role=role_supervisor,
        is_active=True,
    )
    return user

@pytest.fixture
def employee_user(db, role_employee):
    from apps.accounts.models import User
    user = User.objects.create_user(
        username='employee_user',
        email='employee@milkways.com',
        password='Emp@12345',
        first_name='John',
        last_name='Doe',
        role=role_employee,
        is_active=True,
    )
    return user

@pytest.fixture
def inactive_user(db, role_employee):
    from apps.accounts.models import User
    user = User.objects.create_user(
        username='inactive_user',
        email='inactive@milkways.com',
        password='Inactive@12345',
        first_name='Pending',
        last_name='User',
        role=role_employee,
        is_active=False,
    )
    return user


# ─────────────────────────────────────────────
#  DEPARTMENT & POSITION
# ─────────────────────────────────────────────

@pytest.fixture
def department(db):
    from apps.employees.models import Department
    dept, _ = Department.objects.get_or_create(
        name='Human Resources',
        defaults={'code': 'HR', 'is_active': True}
    )
    return dept

@pytest.fixture
def position(db, department):
    from apps.employees.models import Position
    pos, _ = Position.objects.get_or_create(
        title='HR Officer',
        department=department,
        defaults={'level': 1, 'is_active': True}
    )
    return pos


# ─────────────────────────────────────────────
#  EMPLOYEE PROFILE
# ─────────────────────────────────────────────

@pytest.fixture
def employee(db, employee_user, department, position):
    from apps.employees.models import Employee
    emp, _ = Employee.objects.get_or_create(
        user=employee_user,
        defaults={
            'employee_id': 'EMP001',
            'department': department,
            'position': position,
            'hire_date': date(2023, 1, 1),
            'status': 'active',
            'employment_type': 'full_time',
        }
    )
    return emp


# ─────────────────────────────────────────────
#  LEAVE TYPE
# ─────────────────────────────────────────────

@pytest.fixture
def leave_type(db):
    from apps.leaves.models import LeaveType
    lt, _ = LeaveType.objects.get_or_create(
        code='AL',
        defaults={
            'name': 'Annual Leave',
            'max_days_per_year': 21,
            'is_paid': True,
            'is_active': True,
        }
    )
    return lt


# ─────────────────────────────────────────────
#  SUPPORT CATEGORY
# ─────────────────────────────────────────────

@pytest.fixture
def support_category(db):
    from apps.support.models import SupportCategory
    cat, _ = SupportCategory.objects.get_or_create(name='IT Support')
    return cat


# ─────────────────────────────────────────────
#  AUTHENTICATED CLIENTS
# ─────────────────────────────────────────────

@pytest.fixture
def admin_client(client, admin_user):
    client.force_login(admin_user)
    return client

@pytest.fixture
def supervisor_client(client, supervisor_user):
    client.force_login(supervisor_user)
    return client

@pytest.fixture
def employee_client(client, employee_user):
    client.force_login(employee_user)
    return client
