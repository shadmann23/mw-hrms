"""accounts/decorators.py — Role-Based Access"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.role_name not in roles and not request.user.is_superuser:
                messages.error(request, "You do not have permission to access this page.")
                return redirect(request.user.get_dashboard_url())
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class RoleRequiredMixin(LoginRequiredMixin):
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.allowed_roles and request.user.role_name not in self.allowed_roles:
            if not request.user.is_superuser:
                messages.error(request, "Access denied: insufficient permissions.")
                return redirect(request.user.get_dashboard_url())
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['admin']


class SupervisorRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['admin', 'supervisor']
