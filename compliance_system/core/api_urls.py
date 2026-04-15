from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from . import api_views

app_name = 'api'

urlpatterns = [
    # JWT Token endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Auth APIs
    path('register/', api_views.api_register, name='register'),
    path('login/', api_views.api_login, name='login'),
    path('logout/', api_views.api_logout, name='logout'),
    path('refresh/', api_views.api_refresh_token, name='refresh'),
    path('current-user/', api_views.api_current_user, name='current_user'),
    path('dashboard/', api_views.api_dashboard_redirect, name='dashboard'),
    
    # Employee APIs
    path('employee/dashboard/', api_views.api_employee_dashboard, name='employee_dashboard'),
    path('employee/acknowledge/<int:record_id>/', api_views.api_employee_acknowledge, name='employee_acknowledge'),
    
    # Manager APIs
    path('manager/dashboard/', api_views.api_manager_dashboard, name='manager_dashboard'),
    path('manager/policies/', api_views.api_manager_policies, name='manager_policies'),
    path('manager/approve/<int:record_id>/', api_views.api_manager_approve, name='manager_approve'),
    
    # Admin APIs
    path('admin/dashboard/', api_views.api_admin_dashboard, name='admin_dashboard'),
    path('admin/users/', api_views.api_admin_users, name='admin_users'),
    path('admin/users/<int:user_id>/', api_views.api_admin_user_detail, name='admin_user_detail'),
    path('admin/policies/', api_views.api_admin_policies, name='admin_policies'),
    path('admin/policies/<int:policy_id>/', api_views.api_admin_policy_detail, name='admin_policy_detail'),
    path('admin/compliance/', api_views.api_admin_compliance, name='admin_compliance'),
    path('admin/reports/', api_views.api_admin_reports, name='admin_reports'),

  
]