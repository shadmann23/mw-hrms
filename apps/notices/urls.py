from django.urls import path
from apps.notices import views
app_name = 'notices'
urlpatterns = [
    path('', views.NoticeListView.as_view(), name='list'),
    path('create/', views.NoticeCreateView.as_view(), name='create'),
    path('<int:pk>/', views.NoticeDetailView.as_view(), name='detail'),
]
