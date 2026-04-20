from django.urls import path
from apps.attendance import views
app_name = 'attendance'
urlpatterns = [
    path('check-in/', views.AttendanceCheckInView.as_view(), name='check_in'),
    path('check-out/', views.AttendanceCheckOutView.as_view(), name='check_out'),
    path('history/', views.AttendanceHistoryView.as_view(), name='history'),
    path('report/', views.AdminAttendanceReportView.as_view(), name='report'),
]
