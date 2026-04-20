"""accounts/urls.py"""
from django.urls import path
from apps.accounts import views

app_name = 'accounts'

urlpatterns = [
    path('login/',    views.LoginView.as_view(),    name='login'),
    path('logout/',   views.LogoutView.as_view(),   name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),

    # Admin: user management
    path('users/',                          views.UserListView.as_view(),        name='user_list'),
    path('users/create/',                   views.UserCreateView.as_view(),      name='user_create'),
    path('users/<int:pk>/edit/',            views.UserEditView.as_view(),        name='user_edit'),
    path('users/<int:pk>/approve/',         views.UserApproveView.as_view(),     name='user_approve'),
    path('users/<int:pk>/deactivate/',      views.UserDeactivateView.as_view(),  name='user_deactivate'),
    path('users/<int:pk>/make-employee/',   views.UserMakeEmployeeView.as_view(), name='user_make_employee'),
]
