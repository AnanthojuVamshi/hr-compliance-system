from rest_framework import serializers
from .models import User, Policy, ComplianceRecord

# ========== USER SERIALIZERS ==========

class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for list views"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'role_display', 'department', 'date_joined', 'last_login']


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed user serializer with additional info"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'role_display', 'department', 
                  'date_joined', 'last_login', 'is_active', 'full_name']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users"""
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password', 'role', 'department']
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "Username already exists"})
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists"})
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating users"""
    class Meta:
        model = User
        fields = ['email', 'role', 'department']


# ========== POLICY SERIALIZERS ==========

class PolicySerializer(serializers.ModelSerializer):
    """Basic policy serializer"""
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    created_by_role = serializers.ReadOnlyField(source='created_by.role')
    days_until_deadline = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = Policy
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']
    
    def get_days_until_deadline(self, obj):
        from django.utils import timezone
        delta = obj.deadline - timezone.now().date()
        return delta.days
    
    def get_is_overdue(self, obj):
        from django.utils import timezone
        return obj.deadline < timezone.now().date()


class PolicyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new policies"""
    class Meta:
        model = Policy
        fields = ['title', 'description', 'department', 'deadline']
    
    def validate_deadline(self, value):
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError("Deadline cannot be in the past")
        return value


# ========== COMPLIANCE RECORD SERIALIZERS ==========

class ComplianceRecordSerializer(serializers.ModelSerializer):
    """Basic compliance record serializer"""
    employee_name = serializers.ReadOnlyField(source='employee.username')
    employee_email = serializers.ReadOnlyField(source='employee.email')
    employee_department = serializers.ReadOnlyField(source='employee.department')
    policy_title = serializers.ReadOnlyField(source='policy.title')
    policy_department = serializers.ReadOnlyField(source='policy.department')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ComplianceRecord
        fields = '__all__'
        read_only_fields = ['employee', 'acknowledged_at', 'approved_at']


class ComplianceRecordDetailSerializer(serializers.ModelSerializer):
    """Detailed compliance record serializer with nested objects"""
    employee = UserSerializer(read_only=True)
    policy = PolicySerializer(read_only=True)
    
    class Meta:
        model = ComplianceRecord
        fields = '__all__'


class ComplianceRecordUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating compliance records (manager approval)"""
    class Meta:
        model = ComplianceRecord
        fields = ['status', 'manager_remark']
    
    def validate_status(self, value):
        if value not in ['approved', 'rejected']:
            raise serializers.ValidationError("Status must be 'approved' or 'rejected'")
        return value


# ========== DASHBOARD STATS SERIALIZERS ==========

class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_policies = serializers.IntegerField()
    total_employees = serializers.IntegerField()
    pending_approvals = serializers.IntegerField()
    acknowledged = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    pending = serializers.IntegerField()
    completion_rate = serializers.FloatField()


class DepartmentStatsSerializer(serializers.Serializer):
    """Serializer for department-wise statistics"""
    department = serializers.CharField()
    total_policies = serializers.IntegerField()
    total_records = serializers.IntegerField()
    approved_records = serializers.IntegerField()
    pending_records = serializers.IntegerField()
    completion_rate = serializers.FloatField()


# ========== AUTH SERIALIZERS ==========

class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration"""
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6, write_only=True)
    confirm_password = serializers.CharField(min_length=6, write_only=True)
    department = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "Username already exists"})
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists"})
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role='employee',
            department=validated_data.get('department', '')
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=6, write_only=True)
    confirm_password = serializers.CharField(min_length=6, write_only=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data


# ========== EXPORT SERIALIZERS ==========

class ExportComplianceSerializer(serializers.ModelSerializer):
    """Serializer for exporting compliance data to CSV/JSON"""
    employee_name = serializers.ReadOnlyField(source='employee.username')
    employee_email = serializers.ReadOnlyField(source='employee.email')
    employee_department = serializers.ReadOnlyField(source='employee.department')
    policy_title = serializers.ReadOnlyField(source='policy.title')
    policy_description = serializers.ReadOnlyField(source='policy.description')
    policy_deadline = serializers.ReadOnlyField(source='policy.deadline')
    
    class Meta:
        model = ComplianceRecord
        fields = [
            'id', 'employee_name', 'employee_email', 'employee_department',
            'policy_title', 'policy_description', 'policy_deadline',
            'status', 'employee_remark', 'manager_remark',
            'acknowledged_at', 'approved_at'
        ]