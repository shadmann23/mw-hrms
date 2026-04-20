from django.urls import path
from apps.support import views
app_name = 'support'
urlpatterns = [
    path('', views.TicketListView.as_view(), name='list'),
    path('new/', views.TicketCreateView.as_view(), name='create'),
    path('<int:pk>/', views.TicketDetailView.as_view(), name='detail'),
    path('<int:pk>/resolve/', views.TicketResolveView.as_view(), name='resolve'),
]
