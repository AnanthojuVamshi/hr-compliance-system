from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .forms import RegisterForm, PolicyForm
from .models import User, Policy, ComplianceRecord
from .serializers import PolicySerializer, ComplianceRecordSerializer, DashboardStatsSerializer
from .decorators import role_required
from django.utils import timezone

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'employee'  
            user.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'Logged out successfully.')
    return redirect('login')

@login_required
def dashboard(request):
    if request.user.role == 'employee':
        return redirect('employee_dashboard')
    elif request.user.role == 'manager':
        return redirect('manager_dashboard')
    elif request.user.role == 'admin':
        return redirect('admin_dashboard')  # Now points to the comprehensive admin panel
    return redirect('login')


@login_required
@role_required(['employee'])
def employee_dashboard(request):
    pending_records = ComplianceRecord.objects.filter(
        employee=request.user,
        status__in=['pending', 'rejected']
    ).select_related('policy')

    
    # Add to context for sidebar badge
    request.pending_count = pending_records.count()
    
    acknowledged_records = ComplianceRecord.objects.filter(
        employee=request.user,
        status='acknowledged'
    ).select_related('policy')
    
    approved_records = ComplianceRecord.objects.filter(
        employee=request.user,
        status='approved'
    ).select_related('policy')
    
    context = {
        'pending_records': pending_records,
        'acknowledged_records': acknowledged_records,
        'approved_records': approved_records,
        'pending_count': pending_records.count(),  # Add this
    }
    return render(request, 'employee_dashboard.html', context)

@login_required
@role_required(['employee'])
def acknowledge_policy(request, record_id):
    if request.method == 'POST':
        record = get_object_or_404(ComplianceRecord, id=record_id, employee=request.user)
        action = request.POST.get('action')
        remark = request.POST.get('remark', '')
        
        if action == 'acknowledge':
            record.status = 'acknowledged'
            record.employee_remark = remark
            record.acknowledged_at = timezone.now()
            messages.success(request, 'Policy acknowledged successfully!')
        elif action == 'reject':
            record.status = 'rejected'
            record.employee_remark = remark
            messages.warning(request, 'Policy rejected. Manager will review.')
        
        record.save()
        return redirect('employee_dashboard')
    
    return redirect('employee_dashboard')

@login_required
@role_required(['manager', 'admin'])
def manager_dashboard(request):
    my_policies = Policy.objects.filter(created_by=request.user)
    
    dept_records = ComplianceRecord.objects.filter(
        policy__department=request.user.department
    ).select_related('employee', 'policy')
    
    total_employees = User.objects.filter(department=request.user.department, role='employee').count()
    total_policies = my_policies.count()
    pending_approvals = dept_records.filter(status='acknowledged').count()
    
    total_records = dept_records.count()
    approved_records = dept_records.filter(status='approved').count()
    completion_rate = (approved_records / total_records * 100) if total_records > 0 else 0
    
    context = {
        'my_policies': my_policies,
        'dept_records': dept_records,
        'total_employees': total_employees,
        'total_policies': total_policies,
        'pending_approvals': pending_approvals,
        'completion_rate': round(completion_rate, 1),
    }
    return render(request, 'manager_dashboard.html', context)

@login_required
@role_required(['manager', 'admin'])
def create_policy(request):
    if request.method == 'POST':
        form = PolicyForm(request.POST)
        if form.is_valid():
            policy = form.save(commit=False)
            policy.created_by = request.user
            policy.save()
            
            employees = User.objects.filter(department=policy.department, role='employee')
            for employee in employees:
                ComplianceRecord.objects.create(
                    employee=employee,
                    policy=policy,
                    status='pending'
                )
            
            messages.success(request, f'Policy "{policy.title}" created and assigned to {employees.count()} employees!')
            return redirect('manager_dashboard')
    else:
        form = PolicyForm(initial={'department': request.user.department})
    
    return render(request, 'create_policy.html', {'form': form})

@login_required
@role_required(['manager', 'admin'])
def approve_compliance(request, record_id):
    if request.method == 'POST':
        record = get_object_or_404(ComplianceRecord, id=record_id)
        action = request.POST.get('action')
        remark = request.POST.get('remark', '')
        
        if action == 'approve':
            record.status = 'approved'
            record.manager_remark = remark
            record.approved_at = timezone.now()
            messages.success(request, 'Compliance approved!')
        elif action == 'reject':
            record.status = 'rejected'
            record.manager_remark = remark
            messages.warning(request, 'Compliance rejected and sent back to employee.')
        record.save()
        return redirect('manager_dashboard')
    return redirect('manager_dashboard')


@login_required
@role_required(['admin'])
def admin_dashboard(request):
    """Admin dashboard with statistics"""
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
    
    context = {
        'users': users[:5],  # Show only 5 recent users
        'policies': policies[:5],  # Show only 5 recent policies
        'total_users': total_users,
        'total_employees': total_employees,
        'total_managers': total_managers,
        'total_admins': total_admins,
        'total_policies': total_policies,
        'total_compliance': total_compliance,
        'completion_rate': round(completion_rate, 1),
    }
    return render(request, 'admin/admin_dashboard.html', context)

@login_required
@role_required(['admin'])
def admin_users(request):
    users = User.objects.all().order_by('-date_joined')

    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)
    
    search = request.GET.get('search')
    if search:
        users = users.filter(username__icontains=search) | users.filter(email__icontains=search)
    
    context = {
        'users': users,
        'current_role': role_filter,
        'search': search,
    }
    return render(request, 'admin/admin_users.html', context)

@login_required
@role_required(['admin'])
def admin_user_create(request):
    """Admin creates new user (any role)"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        department = request.POST.get('department')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
        else:
            User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                department=department
            )
            messages.success(request, f'User {username} created successfully!')
            return redirect('admin_users')
    
    return render(request, 'admin/admin_user_create.html')

@login_required
@role_required(['admin'])
def admin_user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    print(user)
    
    if request.method == 'POST':
        user.role = request.POST.get('role')
        user.department = request.POST.get('department')
        user.email = request.POST.get('email')
        
        new_password = request.POST.get('new_password')
        if new_password:
            user.set_password(new_password)
        
        user.save()
        messages.success(request, f'User {user.username} updated successfully!')
        return redirect('admin_users')
    
    context = {'edit_user': user}
    return render(request, 'admin/admin_user_edit.html', context)

@login_required
@role_required(['admin'])
def admin_user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    # Prevent admin from deleting themselves
    if request.user.id == user.id:
        messages.error(request, 'You cannot delete your own account!')
        return redirect('admin_users')
    
    # Delete the user
    username = user.username
    user.delete()
    messages.success(request, f'User "{username}" deleted successfully!')
    
    return redirect('admin_users')

@login_required
@role_required(['manager', 'admin'])
def admin_policies(request):
    policies = Policy.objects.all().order_by('-created_at')
    
    department_filter = request.GET.get('department')
    if department_filter:
        policies = policies.filter(department=department_filter)
    
    departments = User.objects.values_list('department', flat=True).distinct()
    
    context = {
        'policies': policies,
        'departments': departments,
        'current_department': department_filter,
    }
    return render(request, 'admin/admin_policies.html', context)

@login_required
@role_required(['manager', 'admin'])
def admin_policy_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        department = request.POST.get('department')
        deadline = request.POST.get('deadline')
        
        policy = Policy.objects.create(
            title=title,
            description=description,
            created_by=request.user,
            department=department,
            deadline=deadline
        )
        
        employees = User.objects.filter(department=department, role='employee')
        for employee in employees:
            ComplianceRecord.objects.create(
                employee=employee,
                policy=policy,
                status='pending'
            )
        
        messages.success(request, f'Policy "{title}" created and assigned to {employees.count()} employees!')
        return redirect('admin_policies')
    
    departments = User.objects.values_list('department', flat=True).distinct()
    context = {'departments': departments}
    return render(request, 'admin/admin_policy_create.html', context)

@login_required
@role_required(['manager', 'admin'])
def admin_policy_edit(request, policy_id):
    policy = get_object_or_404(Policy, id=policy_id)
    
    if request.method == 'POST':
        policy.title = request.POST.get('title')
        policy.description = request.POST.get('description')
        policy.department = request.POST.get('department')
        policy.deadline = request.POST.get('deadline')
        policy.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Policy "{policy.title}" updated successfully!'})
        
        messages.success(request, f'Policy "{policy.title}" updated successfully!')
        return redirect('admin_policies')
    
    return JsonResponse({
        'id': policy.id,
        'title': policy.title,
        'description': policy.description,
        'department': policy.department,
        'deadline': policy.deadline.strftime('%Y-%m-%d')
    })

@login_required
@role_required(['manager', 'admin'])
def admin_policy_delete(request, policy_id):
    policy = get_object_or_404(Policy, id=policy_id)
    
    if request.method == 'POST':
        title = policy.title
        policy.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Policy "{title}" deleted successfully!'})
        
        messages.success(request, f'Policy "{title}" deleted successfully!')
        return redirect('admin_policies')
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@role_required(['admin'])
def admin_compliance(request):
    records = ComplianceRecord.objects.all().select_related('employee', 'policy').order_by('-acknowledged_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        records = records.filter(status=status_filter)
    
    department_filter = request.GET.get('department')
    if department_filter:
        records = records.filter(employee__department=department_filter)
    
    departments = User.objects.values_list('department', flat=True).distinct()
    
    context = {
        'records': records,
        'departments': departments,
        'current_status': status_filter,
        'current_department': department_filter,
    }
    return render(request, 'admin/admin_compliance.html', context)

@login_required
@role_required(['admin'])
def admin_reports(request):
    departments = User.objects.filter(role='employee').values_list('department', flat=True).distinct()
    
    dept_stats = []
    for dept in departments:
        total_policies = Policy.objects.filter(department=dept).count()
        total_records = ComplianceRecord.objects.filter(policy__department=dept).count()
        approved_records = ComplianceRecord.objects.filter(policy__department=dept, status='approved').count()
        completion_rate = (approved_records / total_records * 100) if total_records > 0 else 0
        
        dept_stats.append({
            'department': dept,
            'total_policies': total_policies,
            'total_records': total_records,
            'approved_records': approved_records,
            'completion_rate': round(completion_rate, 1)
        })
    
    context = {
        'dept_stats': dept_stats,
        'total_users': User.objects.count(),
        'total_policies': Policy.objects.count(),
        'total_compliance': ComplianceRecord.objects.count(),
        'completion_rate': round(ComplianceRecord.objects.filter(status='approved').count() / ComplianceRecord.objects.count() * 100, 1) if ComplianceRecord.objects.count() > 0 else 0,
    }
    return render(request, 'admin/admin_reports.html', context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_user_policies(request):
    if request.user.role == 'employee':
        records = ComplianceRecord.objects.filter(employee=request.user).select_related('policy')
        data = [{
            'id': r.id,
            'policy_title': r.policy.title,
            'status': r.status,
            'deadline': r.policy.deadline,
            'employee_remark': r.employee_remark,
        } for r in records]
    else:
        policies = Policy.objects.filter(department=request.user.department)
        data = PolicySerializer(policies, many=True).data
    
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_submit_compliance(request):
    record_id = request.data.get('record_id')
    action = request.data.get('action')
    remark = request.data.get('remark', '')
    
    record = get_object_or_404(ComplianceRecord, id=record_id, employee=request.user)
    
    if action == 'acknowledge':
        record.status = 'acknowledged'
        record.employee_remark = remark
        record.acknowledged_at = timezone.now()
    elif action == 'reject':
        record.status = 'rejected'
        record.employee_remark = remark
    
    record.save()
    return Response({'status': record.status, 'message': 'Submitted successfully'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_dashboard_stats(request):
    if request.user.role == 'manager':
        records = ComplianceRecord.objects.filter(policy__department=request.user.department)
        total = records.count()
        acknowledged = records.filter(status='acknowledged').count()
        approved = records.filter(status='approved').count()
        rejected = records.filter(status='rejected').count()
        pending = records.filter(status='pending').count()
        
        stats = {
            'total_policies': Policy.objects.filter(department=request.user.department).count(),
            'acknowledged': acknowledged,
            'approved': approved,
            'rejected': rejected,
            'pending': pending,
            'completion_rate': (approved / total * 100) if total > 0 else 0,
        }
        return Response(stats)
    return Response({'error': 'Unauthorized'}, status=403)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_export_report(request):
    if request.user.role != 'admin':
        return Response({'error': 'Admin only'}, status=403)
    
    records = ComplianceRecord.objects.select_related('employee', 'policy')
    data = ComplianceRecordSerializer(records, many=True).data
    return Response(data)