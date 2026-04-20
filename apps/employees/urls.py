from django.urls import path
from apps.employees import views

app_name = 'employees'

urlpatterns = [
    path('', views.EmployeeListView.as_view(), name='list'),
    path('profile/', views.EmployeeProfileView.as_view(), name='my_profile'),
    path('profile/edit/', views.EmployeeProfileEditView.as_view(), name='profile_edit'),
    path('profile/avatar/', views.AvatarUploadView.as_view(), name='avatar_upload'),
    path('create/', views.EmployeeCreateView.as_view(), name='create'),
    path('<int:pk>/', views.EmployeeDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='update'),
    path('<int:pk>/terminate/', views.EmployeeTerminateView.as_view(), name='terminate'),
    path('<int:pk>/delete/', views.EmployeeDeleteView.as_view(), name='delete'),
    path('<int:pk>/deactivate/', views.EmployeeDeactivateView.as_view(), name='deactivate'),
    path('<int:pk>/reactivate/', views.EmployeeReactivateView.as_view(), name='reactivate'),
    # Documents
    path('<int:pk>/documents/upload/', views.DocumentUploadView.as_view(), name='document_upload'),
    path('documents/<int:doc_pk>/delete/', views.DocumentDeleteView.as_view(), name='document_delete'),
]
