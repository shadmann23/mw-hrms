"""accounts/middleware.py — Security Middleware"""
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings


class RoleBasedAccessMiddleware:
    PUBLIC_PATHS = [
        '/accounts/login/',
        '/accounts/logout/',
        '/accounts/register/',
        '/admin/',
        '/static/',
        '/media/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        is_public = any(path.startswith(p) for p in self.PUBLIC_PATHS)
        if not is_public and not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={path}")
        return self.get_response(request)


class ActiveUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_active:
            from django.contrib.auth import logout
            logout(request)
            messages.error(request, "Your account has been deactivated. Please contact HR.")
            return redirect(settings.LOGIN_URL)
        return self.get_response(request)
