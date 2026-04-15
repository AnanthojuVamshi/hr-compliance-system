from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ('employee', 'Employee'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='employee')
    department = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.username} ({self.role})"

class Policy(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_policies')
    department = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateField()
    
    def __str__(self):
        return self.title

class ComplianceRecord(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('acknowledged', 'Acknowledged'),
        ('rejected', 'Rejected'),
        ('approved', 'Approved by Manager'),
    )
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compliance_records')
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='compliance_records')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    employee_remark = models.TextField(blank=True)
    manager_remark = models.TextField(blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.employee.username} - {self.policy.title} - {self.status}"