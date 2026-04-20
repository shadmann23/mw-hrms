"""
apps/employees/tests/test_employees.py
Tests for: Department, Position, Employee models and views
"""
import pytest
from datetime import date
from django.urls import reverse
from apps.employees.models import Department, Position, Employee


# ═══════════════════════════════════════════════
#  DEPARTMENT MODEL TESTS
# ═══════════════════════════════════════════════

class TestDepartmentModel:

    def test_department_str(self, department):
        assert 'HR' in str(department)
        assert 'Human Resources' in str(department)

    def test_department_created(self, department):
        assert department.pk is not None
        assert department.is_active is True

    def test_department_name_is_unique(self, db, department):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Department.objects.create(name='Human Resources', code='HR2')

    def test_department_code_is_unique(self, db, department):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Department.objects.create(name='Another Dept', code='HR')

    def test_department_ordering(self, db):
        Department.objects.create(name='Zebra Dept', code='ZD')
        Department.objects.create(name='Apple Dept', code='AD')
        depts = list(Department.objects.values_list('name', flat=True))
        assert depts == sorted(depts)


# ═══════════════════════════════════════════════
#  POSITION MODEL TESTS
# ═══════════════════════════════════════════════

class TestPositionModel:

    def test_position_str(self, position, department):
        assert 'HR Officer' in str(position)
        assert department.code in str(position)

    def test_position_unique_per_department(self, db, position, department):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Position.objects.create(title='HR Officer', department=department)

    def test_position_same_title_different_dept(self, db, position):
        other_dept = Department.objects.create(name='Finance', code='FIN')
        pos = Position.objects.create(title='HR Officer', department=other_dept)
        assert pos.pk is not None


# ═══════════════════════════════════════════════
#  EMPLOYEE MODEL TESTS
# ═══════════════════════════════════════════════

class TestEmployeeModel:

    def test_employee_str(self, employee):
        assert 'EMP001' in str(employee)

    def test_employee_full_name(self, employee, employee_user):
        assert employee.full_name == employee_user.get_full_name()

    def test_employee_email(self, employee, employee_user):
        assert employee.email == employee_user.email

    def test_employee_years_of_service(self, employee):
        years = employee.years_of_service
        assert isinstance(years, float)
        assert years >= 0

    def test_employee_default_status_is_active(self, employee):
        assert employee.status == 'active'

    def test_employee_default_leave_balances(self, employee):
        assert float(employee.annual_leave_balance) == 21.0
        assert float(employee.sick_leave_balance) == 14.0

    def test_employee_id_is_unique(self, db, employee, supervisor_user, department, position):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Employee.objects.create(
                user=supervisor_user,
                employee_id='EMP001',  # duplicate
                department=department,
                position=position,
            )

    def test_employee_get_avatar_url_no_avatar(self, employee):
        assert employee.get_avatar_url() is None

    def test_employee_one_to_one_with_user(self, employee, employee_user):
        assert employee_user.employee_profile == employee

    def test_employee_status_choices(self, employee):
        valid_statuses = ['active', 'on_leave', 'terminated', 'suspended', 'fired']
        assert employee.status in valid_statuses

    def test_employee_employment_type_choices(self, employee):
        valid_types = ['full_time', 'part_time', 'contract', 'intern']
        assert employee.employment_type in valid_types


# ═══════════════════════════════════════════════
#  EMPLOYEE VIEWS TESTS
# ═══════════════════════════════════════════════

class TestEmployeeViews:

    def test_employee_list_requires_login(self, client):
        response = client.get(reverse('employees:list'))
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_employee_list_accessible_by_admin(self, admin_client, employee):
        response = admin_client.get(reverse('employees:list'))
        assert response.status_code == 200

    def test_employee_list_accessible_by_supervisor(self, supervisor_client, employee):
        response = supervisor_client.get(reverse('employees:list'))
        assert response.status_code == 200

    def test_employee_detail_accessible_by_admin(self, admin_client, employee):
        response = admin_client.get(reverse('employees:detail', kwargs={'pk': employee.pk}))
        assert response.status_code == 200

    def test_employee_detail_contains_name(self, admin_client, employee):
        response = admin_client.get(reverse('employees:detail', kwargs={'pk': employee.pk}))
        assert employee.user.first_name.encode() in response.content

    def test_employee_create_page_loads_for_admin(self, admin_client):
        response = admin_client.get(reverse('employees:create'))
        assert response.status_code == 200

    def test_employee_create_blocked_for_employee(self, employee_client):
        response = employee_client.get(reverse('employees:create'))
        assert response.status_code in [302, 403]

    def test_nonexistent_employee_returns_404(self, admin_client):
        response = admin_client.get(reverse('employees:detail', kwargs={'pk': 99999}))
        assert response.status_code == 404


# ═══════════════════════════════════════════════
#  EMPLOYEE PROFILE VIEW TESTS
# ═══════════════════════════════════════════════

class TestEmployeeProfileView:

    def test_own_profile_accessible(self, employee_client, employee):
        response = employee_client.get(reverse('employees:profile'))
        assert response.status_code == 200

    def test_profile_requires_login(self, client):
        response = client.get(reverse('employees:profile'))
        assert response.status_code == 302
        assert 'login' in response['Location']
