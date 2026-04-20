"""HRMS Root URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.accounts.views import DashboardRedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', DashboardRedirectView.as_view(), name='home'),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('employees/', include('apps.employees.urls', namespace='employees')),
    path('attendance/', include('apps.attendance.urls', namespace='attendance')),
    path('leaves/', include('apps.leaves.urls', namespace='leaves')),
    path('shifts/', include('apps.shifts.urls', namespace='shifts')),
    path('notices/', include('apps.notices.urls', namespace='notices')),
    path('support/', include('apps.support.urls', namespace='support')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('teams/', include('apps.teams.urls', namespace='teams')),
    path('dashboard/', include('apps.accounts.dashboard_urls', namespace='dashboard')),
    path('sysadmin/', include('apps.accounts.sysadmin_urls', namespace='sysadmin')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "HRMS Administration"
admin.site.site_title = "HRMS Admin Portal"
admin.site.index_title = "Welcome to HRMS Administration"
