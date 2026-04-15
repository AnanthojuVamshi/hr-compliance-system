from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Policy

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    department = forms.CharField(max_length=100, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'department']

class PolicyForm(forms.ModelForm):
    class Meta:
        model = Policy
        fields = ['title', 'description', 'department', 'deadline']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }