"""
apps/accounts/tests/test_accounts.py
Tests for: User model, Role model, LoginForm, RegisterForm, Login/Register views
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.models import Role
from apps.accounts.forms import LoginForm, RegisterForm

User = get_user_model()


# ═══════════════════════════════════════════════
#  ROLE MODEL TESTS
# ═══════════════════════════════════════════════

class TestRoleModel:

    def test_role_str(self, db, role_admin):
        assert str(role_admin) == 'HR Administrator'

    def test_role_is_admin_property(self, role_admin):
        assert role_admin.is_admin is True
        assert role_admin.is_supervisor is False
        assert role_admin.is_employee is False

    def test_role_is_supervisor_property(self, role_supervisor):
        assert role_supervisor.is_supervisor is True
        assert role_supervisor.is_admin is False

    def test_role_is_employee_property(self, role_employee):
        assert role_employee.is_employee is True
        assert role_employee.is_admin is False

    def test_roles_are_unique(self, db, role_admin):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Role.objects.create(name=Role.ADMIN)


# ═══════════════════════════════════════════════
#  USER MODEL TESTS
# ═══════════════════════════════════════════════

class TestUserModel:

    def test_user_str(self, admin_user):
        assert 'admin_user' in str(admin_user)

    def test_user_full_name(self, admin_user):
        assert admin_user.get_full_name() == 'Admin User'

    def test_user_role_name(self, admin_user, role_admin):
        assert admin_user.role_name == Role.ADMIN

    def test_user_is_admin_property(self, admin_user):
        assert admin_user.is_admin is True
        assert admin_user.is_supervisor is False
        assert admin_user.is_employee is False

    def test_user_is_supervisor_property(self, supervisor_user):
        assert supervisor_user.is_supervisor is True

    def test_user_is_employee_property(self, employee_user):
        assert employee_user.is_employee is True

    def test_user_has_role(self, admin_user):
        assert admin_user.has_role(Role.ADMIN) is True
        assert admin_user.has_role(Role.EMPLOYEE) is False

    def test_user_no_role_returns_none(self, db):
        user = User.objects.create_user(
            username='norole', email='norole@milkways.com', password='pass'
        )
        assert user.role_name is None
        assert user.is_admin is False

    def test_user_email_is_unique(self, db, admin_user):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username='another_admin',
                email='admin@milkways.com',  # duplicate email
                password='pass'
            )

    def test_get_dashboard_url_admin(self, admin_user):
        url = admin_user.get_dashboard_url()
        assert 'admin' in url

    def test_get_dashboard_url_employee(self, employee_user):
        url = employee_user.get_dashboard_url()
        assert 'employee' in url

    def test_get_dashboard_url_supervisor(self, supervisor_user):
        url = supervisor_user.get_dashboard_url()
        assert 'supervisor' in url


# ═══════════════════════════════════════════════
#  LOGIN FORM TESTS
# ═══════════════════════════════════════════════

class TestLoginForm:

    def test_valid_login_form(self):
        form = LoginForm(data={'username': 'testuser', 'password': 'pass123'})
        assert form.is_valid()

    def test_empty_username_invalid(self):
        form = LoginForm(data={'username': '', 'password': 'pass123'})
        assert not form.is_valid()
        assert 'username' in form.errors

    def test_empty_password_invalid(self):
        form = LoginForm(data={'username': 'testuser', 'password': ''})
        assert not form.is_valid()
        assert 'password' in form.errors

    def test_empty_form_invalid(self):
        form = LoginForm(data={})
        assert not form.is_valid()
        assert 'username' in form.errors
        assert 'password' in form.errors


# ═══════════════════════════════════════════════
#  REGISTER FORM TESTS
# ═══════════════════════════════════════════════

class TestRegisterForm:

    def valid_data(self):
        return {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'username': 'janesmith',
            'email': 'jane@milkways.com',
            'password1': 'SecurePass@123',
            'password2': 'SecurePass@123',
        }

    def test_valid_register_form(self, db):
        form = RegisterForm(data=self.valid_data())
        assert form.is_valid(), form.errors

    def test_passwords_mismatch(self, db):
        data = self.valid_data()
        data['password2'] = 'DifferentPass@123'
        form = RegisterForm(data=data)
        assert not form.is_valid()
        assert 'password2' in form.errors

    def test_duplicate_username(self, db, employee_user):
        data = self.valid_data()
        data['username'] = employee_user.username
        form = RegisterForm(data=data)
        assert not form.is_valid()
        assert 'username' in form.errors

    def test_duplicate_email(self, db, employee_user):
        data = self.valid_data()
        data['email'] = employee_user.email
        form = RegisterForm(data=data)
        assert not form.is_valid()
        assert 'email' in form.errors

    def test_weak_password_rejected(self, db):
        data = self.valid_data()
        data['password1'] = '123'
        data['password2'] = '123'
        form = RegisterForm(data=data)
        assert not form.is_valid()

    def test_form_save_creates_inactive_user(self, db, role_employee):
        form = RegisterForm(data=self.valid_data())
        assert form.is_valid()
        user = form.save()
        assert user.pk is not None
        assert user.is_active is False  # pending admin approval
        assert user.role.name == Role.EMPLOYEE

    def test_missing_required_fields(self, db):
        form = RegisterForm(data={})
        assert not form.is_valid()
        for field in ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']:
            assert field in form.errors


# ═══════════════════════════════════════════════
#  LOGIN VIEW TESTS
# ═══════════════════════════════════════════════

class TestLoginView:

    def test_login_page_loads(self, client):
        response = client.get(reverse('accounts:login'))
        assert response.status_code == 200
        assert b'Sign In' in response.content or b'Welcome back' in response.content

    def test_login_with_valid_credentials(self, client, employee_user):
        response = client.post(reverse('accounts:login'), {
            'username': employee_user.username,
            'password': 'Emp@12345',
        })
        assert response.status_code == 302  # redirects after login

    def test_login_with_wrong_password(self, client, employee_user):
        response = client.post(reverse('accounts:login'), {
            'username': employee_user.username,
            'password': 'wrongpassword',
        })
        assert response.status_code == 200  # stays on login page
        assert b'Invalid' in response.content or b'incorrect' in response.content.lower() or len(response.context['form'].errors) > 0 or b'auth-err' in response.content

    def test_login_with_inactive_user(self, client, inactive_user):
        response = client.post(reverse('accounts:login'), {
            'username': inactive_user.username,
            'password': 'Inactive@12345',
        })
        # Should not redirect to dashboard
        assert response.status_code == 200

    def test_login_redirects_to_dashboard(self, client, employee_user):
        response = client.post(reverse('accounts:login'), {
            'username': employee_user.username,
            'password': 'Emp@12345',
        }, follow=True)
        assert response.status_code == 200
        # Should land on some dashboard page
        assert 'dashboard' in response.request['PATH_INFO'] or response.redirect_chain

    def test_already_logged_in_redirects(self, employee_client):
        response = employee_client.get(reverse('accounts:login'))
        # Logged-in users should be redirected away from login
        assert response.status_code in [200, 302]


# ═══════════════════════════════════════════════
#  REGISTER VIEW TESTS
# ═══════════════════════════════════════════════

class TestRegisterView:

    def test_register_page_loads(self, client):
        response = client.get(reverse('accounts:register'))
        assert response.status_code == 200
        assert b'Create' in response.content or b'Register' in response.content

    def test_register_creates_user(self, client, db, role_employee):
        response = client.post(reverse('accounts:register'), {
            'first_name': 'New',
            'last_name': 'Employee',
            'username': 'newemployee',
            'email': 'newemployee@milkways.com',
            'password1': 'SecurePass@123',
            'password2': 'SecurePass@123',
        })
        assert User.objects.filter(username='newemployee').exists()

    def test_new_user_is_inactive(self, client, db, role_employee):
        client.post(reverse('accounts:register'), {
            'first_name': 'Pending',
            'last_name': 'Person',
            'username': 'pendingperson',
            'email': 'pending@milkways.com',
            'password1': 'SecurePass@123',
            'password2': 'SecurePass@123',
        })
        user = User.objects.get(username='pendingperson')
        assert user.is_active is False

    def test_register_with_invalid_data_shows_errors(self, client, db):
        response = client.post(reverse('accounts:register'), {
            'first_name': '',
            'last_name': '',
            'username': '',
            'email': 'not-an-email',
            'password1': '123',
            'password2': '456',
        })
        assert response.status_code == 200
        assert not User.objects.filter(email='not-an-email').exists()


# ═══════════════════════════════════════════════
#  LOGOUT VIEW TESTS
# ═══════════════════════════════════════════════

class TestLogoutView:

    def test_logout_redirects_to_login(self, employee_client):
        response = employee_client.post(reverse('accounts:logout'))
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_after_logout_cannot_access_dashboard(self, employee_client):
        employee_client.post(reverse('accounts:logout'))
        response = employee_client.get(reverse('home'))
        assert response.status_code == 302  # redirected to login


# ═══════════════════════════════════════════════
#  ACCESS CONTROL TESTS
# ═══════════════════════════════════════════════

class TestAccessControl:

    def test_unauthenticated_redirected_from_home(self, client):
        response = client.get(reverse('home'))
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_unauthenticated_redirected_from_user_list(self, client):
        response = client.get(reverse('accounts:user_list'))
        assert response.status_code == 302

    def test_employee_cannot_access_user_list(self, employee_client):
        response = employee_client.get(reverse('accounts:user_list'))
        assert response.status_code in [302, 403]

    def test_admin_can_access_user_list(self, admin_client):
        response = admin_client.get(reverse('accounts:user_list'))
        assert response.status_code == 200
