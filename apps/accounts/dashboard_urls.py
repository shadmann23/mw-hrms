"""accounts/dashboard_urls.py"""
from django.urls import path
from apps.accounts import views

app_name = 'dashboard'

urlpatterns = [
    path('admin/', views.AdminDashboardView.as_view(), name='admin'),
    path('supervisor/', views.SupervisorDashboardView.as_view(), name='supervisor'),
    path('employee/', views.EmployeeDashboardView.as_view(), name='employee'),
]
