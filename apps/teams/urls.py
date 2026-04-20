from django.urls import path
from apps.teams import views
app_name = 'teams'
urlpatterns = [
    path('', views.TeamListView.as_view(), name='list'),
    path('create/', views.TeamCreateView.as_view(), name='create'),
    path('<int:pk>/', views.TeamDetailView.as_view(), name='detail'),
    path('<int:pk>/add-member/', views.TeamAddMemberView.as_view(), name='add_member'),
    path('<int:pk>/remove-member/<int:member_pk>/', views.TeamRemoveMemberView.as_view(), name='remove_member'),
]
