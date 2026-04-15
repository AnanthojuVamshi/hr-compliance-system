#!/bin/bash

echo "🚀 Starting HR Compliance System..."

# Wait for database to be ready
echo "⏳ Waiting for database..."
while ! nc -z db 5432 2>/dev/null; do
  sleep 1
done
echo "✅ Database is ready!"

# Run migrations
echo "📦 Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if not exists
echo "👤 Creating superuser..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='Test@123'
    )
    print('✅ Superuser created: admin / admin123')
else:
    print('ℹ️ Superuser already exists')
EOF

# Create default employee user
echo "👥 Creating default users..."
python manage.py shell << EOF
from core.models import User
from django.contrib.auth.hashers import make_password

# Create Employee
if not User.objects.filter(username='employee1').exists():
    User.objects.create(
        username='employee1',
        email='employee1@example.com',
        password=make_password('Test@123'),
        role='employee',
        department='Human Resources'
    )
    print('✅ Employee user created: employee1 / Test@123')
else:
    print('ℹ️ Employee user already exists')

# Create Manager
if not User.objects.filter(username='manager1').exists():
    User.objects.create(
        username='manager1',
        email='manager1@example.com',
        password=make_password('Test@123'),
        role='manager',
        department='Human Resources'
    )
    print('✅ Manager user created: manager1 / Test@123')
else:
    print('ℹ️ Manager user already exists')

print('🎉 User setup complete!')
EOF

# Start the application
echo "🚀 Starting Django server..."
exec "$@"