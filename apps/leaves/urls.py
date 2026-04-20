from django.urls import path
from apps.leaves import views
app_name = 'leaves'
urlpatterns = [
    path('', views.LeaveListView.as_view(), name='list'),
    path('apply/', views.LeaveRequestCreateView.as_view(), name='apply'),
    path('<int:pk>/', views.LeaveDetailView.as_view(), name='detail'),
    path('<int:pk>/approve/', views.LeaveApprovalView.as_view(), name='approve'),
    path('<int:pk>/cancel/', views.LeaveCancelView.as_view(), name='cancel'),
]