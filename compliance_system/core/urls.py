from django.urls import path
from . import views
from . import api_views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

urlpatterns = [
    # Auth
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Employee
    path('employee/', views.employee_dashboard, name='employee_dashboard'),
    path('acknowledge/<int:record_id>/', views.acknowledge_policy, name='acknowledge_policy'),
    
    # Manager
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('create-policy/', views.create_policy, name='create_policy'),
    path('approve/<int:record_id>/', views.approve_compliance, name='approve_compliance'),
    
    # Admin HTML
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/users/', views.admin_users, name='admin_users'),
    path('dashboard/users/create/', views.admin_user_create, name='admin_user_create'),
    path('dashboard/users/edit/<int:user_id>/', views.admin_user_edit, name='admin_user_edit'),
    path('dashboard/users/delete/<int:user_id>/', views.admin_user_delete, name='admin_user_delete'),
    path('dashboard/policies/', views.admin_policies, name='admin_policies'),
    path('dashboard/policies/create/', views.admin_policy_create, name='admin_policy_create'),
    path('dashboard/policies/edit/<int:policy_id>/', views.admin_policy_edit, name='admin_policy_edit'),
    path('dashboard/policies/delete/<int:policy_id>/', views.admin_policy_delete, name='admin_policy_delete'),
    path('dashboard/compliance/', views.admin_compliance, name='admin_compliance'),
    path('dashboard/reports/', views.admin_reports, name='admin_reports'),
   
]