from django.urls import path
from apps.shifts import views
app_name = 'shifts'
urlpatterns = [
    path('', views.ShiftCalendarView.as_view(), name='calendar'),
    path('api/events/', views.ShiftEventsAPIView.as_view(), name='events_api'),
    path('assign/', views.ShiftAssignView.as_view(), name='assign'),
]
