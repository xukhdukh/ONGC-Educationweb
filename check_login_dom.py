import os, sys, django
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joy_lms.settings.base')
django.setup()

from django.test import Client
c = Client(SERVER_NAME='127.0.0.1', SERVER_PORT='8000')
r = c.get('/login/')
content = r.content.decode('utf-8')
print('STATUS:', r.status_code)

# Check for key elements
checks = [
    'login-fullscreen-page',
    'login-bg-layer',
    'login_banner.png',
    'login-tile-toggle',
    'login-tile',
    'login-tile-inner',
    'login-tile-logo',
    'login-tile-rainbow',
]
for key in checks:
    found = key in content
    print(f"  {'OK' if found else 'MISSING'}: {key}")
