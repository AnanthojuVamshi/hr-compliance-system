from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from .models import User, Policy, ComplianceRecord
from .serializers import (
    UserSerializer, PolicySerializer, ComplianceRecordSerializer,
    RegisterSerializer, LoginSerializer
)

# ========== HELPER FUNCTIONS ==========

def get_tokens_for_user(user):
    """Generate JWT tokens for user"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

# ========== AUTHENTICATION APIS ==========

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])

def api_register(request):
    """Register new user and return JWT tokens"""
    serializer = RegisterSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    username = serializer.validated_data['username']
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    department = serializer.validated_data.get('department', '')
    
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
    
    user = User.objects.create(
        username=username,
        email=email,
        password=make_password(password),
        role='employee',
        department=department
    )
    
    # Generate JWT tokens
    tokens = get_tokens_for_user(user)
    
    return Response({
        'message': 'User created successfully',
        'user': UserSerializer(user).data,
        'tokens': tokens
    }, status=status.HTTP_201_CREATED)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])

def api_login(request):
    """Login user and return JWT tokens"""
    serializer = LoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    username = serializer.validated_data['username']
    password = serializer.validated_data['password']
    
    user = authenticate(username=username, password=password)
    
    if user:
        # Generate JWT tokens
        tokens = get_tokens_for_user(user)
        
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'role': user.role,
            'tokens': tokens
        })
    
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """Logout user by blacklisting refresh token"""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Logged out successfully'})
    except Exception as e:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def api_refresh_token(request):
    """Refresh access token using refresh token"""
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response({'error': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        return Response({
            'access': access_token,
            'refresh': str(refresh)
        })
    except Exception as e:
        return Response({'error': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_current_user(request):
    """Get current logged-in user data using JWT"""
    return Response(UserSerializer(request.user).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_dashboard_redirect(request):
    """Redirect to role-specific dashboard"""
    if request.user.role == 'employee':
        return Response({'redirect': '/api/employee/dashboard/'})
    elif request.user.role == 'manager':
        return Response({'redirect': '/api/manager/dashboard/'})
    elif request.user.role == 'admin':
        return Response({'redirect': '/api/admin/dashboard/'})
    return Response({'error': 'Invalid role'}, status=status.HTTP_400_BAD_REQUEST)


# ========== EMPLOYEE APIS ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_employee_dashboard(request):
    """Get employee dashboard data"""
    if request.user.role != 'employee':
        return Response({'error': 'Employee access required'}, status=status.HTTP_403_FORBIDDEN)
    
    pending_records = ComplianceRecord.objects.filter(
        employee=request.user,
        status__in=['pending', 'rejected']
    ).select_related('policy')
    
    acknowledged_records = ComplianceRecord.objects.filter(
        employee=request.user,
        status='acknowledged'
    ).select_related('policy')
    
    approved_records = ComplianceRecord.objects.filter(
        employee=request.user,
        status='approved'
    ).select_related('policy')
    
    return Response({
        'pending': ComplianceRecordSerializer(pending_records, many=True).data,
        'acknowledged': ComplianceRecordSerializer(acknowledged_records, many=True).data,
        'approved': ComplianceRecordSerializer(approved_records, many=True).data,
        'counts': {
            'pending': pending_records.count(),
            'acknowledged': acknowledged_records.count(),
            'approved': approved_records.count()
        }
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_employee_acknowledge(request, record_id):
    """Employee acknowledges or rejects a policy"""
    if request.user.role != 'employee':
        return Response({'error': 'Employee access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        record = ComplianceRecord.objects.get(id=record_id, employee=request.user)
    except ComplianceRecord.DoesNotExist:
        return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)
    
    action = request.data.get('action')
    remark = request.data.get('remark', '')
    
    if action == 'acknowledge':
        record.status = 'acknowledged'
        record.employee_remark = remark
        record.acknowledged_at = timezone.now()
        message = 'Policy acknowledged successfully'
    elif action == 'reject':
        record.status = 'rejected'
        record.employee_remark = remark
        message = 'Policy rejected'
    else:
        return Response({'error': 'Invalid action. Use "acknowledge" or "reject"'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    record.save()
    
    return Response({
        'message': message,
        'record': ComplianceRecordSerializer(record).data
    })


# ========== MANAGER APIS ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_manager_dashboard(request):
    """Get manager dashboard data"""
    if request.user.role not in ['manager', 'admin']:
        return Response({'error': 'Manager access required'}, status=status.HTTP_403_FORBIDDEN)
    
    my_policies = Policy.objects.filter(created_by=request.user)
    
    dept_records = ComplianceRecord.objects.filter(
        policy__department=request.user.department
    ).select_related('employee', 'policy')
    
    total_employees = User.objects.filter(
        department=request.user.department, 
        role='employee'
    ).count()
    
    total_policies = my_policies.count()
    pending_approvals = dept_records.filter(status='acknowledged').count()
    
    total_records = dept_records.count()
    approved_records = dept_records.filter(status='approved').count()
    completion_rate = (approved_records / total_records * 100) if total_records > 0 else 0
    
    return Response({
        'my_policies': PolicySerializer(my_policies, many=True).data,
        'department_records': ComplianceRecordSerializer(dept_records, many=True).data,
        'statistics': {
            'total_employees': total_employees,
            'total_policies': total_policies,
            'pending_approvals': pending_approvals,
            'completion_rate': round(completion_rate, 1)
        }
    })

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_manager_policies(request):
    """Get or create policies (Manager/Admin only)"""
    if request.user.role not in ['manager', 'admin']:
        return Response({'error': 'Manager access required'}, status=status.HTTP_403_FORBIDDEN)
    
    # GET - List policies
    if request.method == 'GET':
        policies = Policy.objects.filter(department=request.user.department)
        department_filter = request.GET.get('department')
        if department_filter:
            policies = policies.filter(department=department_filter)
        return Response(PolicySerializer(policies, many=True).data)
    
    # POST - Create policy
    elif request.method == 'POST':
        title = request.data.get('title')
        description = request.data.get('description')
        department = request.data.get('department')
        deadline = request.data.get('deadline')
        
        if not all([title, description, department, deadline]):
            return Response({'error': 'All fields are required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        policy = Policy.objects.create(
            title=title,
            description=description,
            created_by=request.user,
            department=department,
            deadline=deadline
        )
        
        # Create compliance records for all employees in that department
        employees = User.objects.filter(department=department, role='employee')
        for employee in employees:
            ComplianceRecord.objects.create(
                employee=employee,
                policy=policy,
                status='pending'
            )
        
        return Response({
            'message': f'Policy "{title}" created and assigned to {employees.count()} employees',
            'policy': PolicySerializer(policy).data
        }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_manager_approve(request, record_id):
    """Manager approves or rejects compliance record"""
    if request.user.role not in ['manager', 'admin']:
        return Response({'error': 'Manager access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        record = ComplianceRecord.objects.get(id=record_id)
    except ComplianceRecord.DoesNotExist:
        return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)
    
    action = request.data.get('action')
    remark = request.data.get('remark', '')
    
    if action == 'approve':
        record.status = 'approved'
        record.manager_remark = remark
        record.approved_at = timezone.now()
        message = 'Compliance approved'
    elif action == 'reject':
        record.status = 'rejected'
        record.manager_remark = remark
        message = 'Compliance rejected'
    else:
        return Response({'error': 'Invalid action. Use "approve" or "reject"'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    record.save()
    
    return Response({
        'message': message,
        'record': ComplianceRecordSerializer(record).data
    })


# ========== ADMIN APIS ==========
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_admin_dashboard(request):
    
    if not request.user or not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.role != 'admin':
        return Response({
            'error': f'Admin access required. Your role is: {request.user.role}',
            'your_role': request.user.role,
            'your_username': request.user.username
        }, status=status.HTTP_403_FORBIDDEN)

    
    
    users = User.objects.all()
    policies = Policy.objects.all()
    compliance_records = ComplianceRecord.objects.all()
    
    total_users = users.count()
    total_employees = users.filter(role='employee').count()
    total_managers = users.filter(role='manager').count()
    total_admins = users.filter(role='admin').count()
    total_policies = policies.count()
    total_compliance = compliance_records.count()
    completed_compliance = compliance_records.filter(status='approved').count()
    completion_rate = (completed_compliance / total_compliance * 100) if total_compliance > 0 else 0
    
    return Response({
        'statistics': {
            'total_users': total_users,
            'total_employees': total_employees,
            'total_managers': total_managers,
            'total_admins': total_admins,
            'total_policies': total_policies,
            'total_compliance': total_compliance,
            'completion_rate': round(completion_rate, 1)
        },
        'recent_users': UserSerializer(users[:5], many=True).data,
        'recent_policies': PolicySerializer(policies[:5], many=True).data
    })

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_admin_users(request):
    """List, create, filter, search users (Admin only)"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    # GET - List users with filters
    if request.method == 'GET':
        users = User.objects.all().order_by('-date_joined')
        
        role_filter = request.GET.get('role')
        if role_filter:
            users = users.filter(role=role_filter)
        
        search = request.GET.get('search')
        if search:
            users = users.filter(
                Q(username__icontains=search) | 
                Q(email__icontains=search)
            )
        
        return Response({
            'users': UserSerializer(users, many=True).data,
            'total': users.count()
        })
    
    # POST - Create new user
    elif request.method == 'POST':
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        role = request.data.get('role')
        department = request.data.get('department', '')
        
        if not all([username, email, password, role]):
            return Response({'error': 'Username, email, password, and role are required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            department=department
        )
        
        return Response({
            'message': f'User {username} created successfully',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def api_admin_user_detail(request, user_id):
    """Get, update, or delete a specific user (Admin only)"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # GET - Get user details
    if request.method == 'GET':
        return Response(UserSerializer(user).data)
    
    # PUT - Update user
    elif request.method == 'PUT':
        user.role = request.data.get('role', user.role)
        user.department = request.data.get('department', user.department)
        user.email = request.data.get('email', user.email)
        
        new_password = request.data.get('new_password')
        if new_password:
            user.set_password(new_password)
        
        user.save()
        
        return Response({
            'message': f'User {user.username} updated successfully',
            'user': UserSerializer(user).data
        })
    
    # DELETE - Delete user
    elif request.method == 'DELETE':
        # Prevent admin from deleting themselves
        if request.user.id == user.id:
            return Response({'error': 'You cannot delete your own account'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        username = user.username
        user.delete()
        
        return Response({'message': f'User {username} deleted successfully'})

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])

def api_admin_policies(request):
    """List, filter, or create policies (Admin only)"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    # GET - List policies with filters
    if request.method == 'GET':
        policies = Policy.objects.all().order_by('-created_at')
        
        department_filter = request.GET.get('department')
        if department_filter:
            policies = policies.filter(department=department_filter)
        
        return Response({
            'policies': PolicySerializer(policies, many=True).data,
            'total': policies.count()
        })
    
    # POST - Create policy
    elif request.method == 'POST':
        title = request.data.get('title')
        description = request.data.get('description')
        department = request.data.get('department')
        deadline = request.data.get('deadline')
        
        if not all([title, description, department, deadline]):
            return Response({'error': 'All fields are required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        policy = Policy.objects.create(
            title=title,
            description=description,
            created_by=request.user,
            department=department,
            deadline=deadline
        )
        
        # Create compliance records for all employees in that department
        employees = User.objects.filter(department=department, role='employee')
        for employee in employees:
            ComplianceRecord.objects.create(
                employee=employee,
                policy=policy,
                status='pending'
            )
        
        return Response({
            'message': f'Policy "{title}" created and assigned to {employees.count()} employees',
            'policy': PolicySerializer(policy).data
        }, status=status.HTTP_201_CREATED)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def api_admin_policy_detail(request, policy_id):
    """Get, update, or delete a specific policy (Admin only)"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        policy = Policy.objects.get(id=policy_id)
    except Policy.DoesNotExist:
        return Response({'error': 'Policy not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # GET - Get policy details
    if request.method == 'GET':
        return Response(PolicySerializer(policy).data)
    
    # PUT - Update policy
    elif request.method == 'PUT':
        policy.title = request.data.get('title', policy.title)
        policy.description = request.data.get('description', policy.description)
        policy.department = request.data.get('department', policy.department)
        policy.deadline = request.data.get('deadline', policy.deadline)
        policy.save()
        
        return Response({
            'message': f'Policy "{policy.title}" updated successfully',
            'policy': PolicySerializer(policy).data
        })
    
    # DELETE - Delete policy
    elif request.method == 'DELETE':
        title = policy.title
        policy.delete()
        
        return Response({'message': f'Policy "{title}" deleted successfully'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_admin_compliance(request):
    """Get all compliance records with filters (Admin only)"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    records = ComplianceRecord.objects.all().select_related(
        'employee', 'policy'
    ).order_by('-acknowledged_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        records = records.filter(status=status_filter)
    
    department_filter = request.GET.get('department')
    if department_filter:
        records = records.filter(employee__department=department_filter)
    
    departments = User.objects.values_list('department', flat=True).distinct()
    
    return Response({
        'records': ComplianceRecordSerializer(records, many=True).data,
        'total': records.count(),
        'departments': list(departments)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_admin_reports(request):
    """Get department-wise compliance reports (Admin only)"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    departments = User.objects.filter(role='employee').values_list('department', flat=True).distinct()
    
    dept_stats = []
    for dept in departments:
        total_policies = Policy.objects.filter(department=dept).count()
        total_records = ComplianceRecord.objects.filter(policy__department=dept).count()
        approved_records = ComplianceRecord.objects.filter(
            policy__department=dept, 
            status='approved'
        ).count()
        completion_rate = (approved_records / total_records * 100) if total_records > 0 else 0
        
        dept_stats.append({
            'department': dept,
            'total_policies': total_policies,
            'total_records': total_records,
            'approved_records': approved_records,
            'completion_rate': round(completion_rate, 1)
        })
    
    total_compliance = ComplianceRecord.objects.count()
    completion_rate = round(
        ComplianceRecord.objects.filter(status='approved').count() / total_compliance * 100, 1
    ) if total_compliance > 0 else 0
    
    return Response({
        'department_statistics': dept_stats,
        'overall': {
            'total_users': User.objects.count(),
            'total_policies': Policy.objects.count(),
            'total_compliance': total_compliance,
            'completion_rate': completion_rate
        }
    })