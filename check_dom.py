import os
import sys
import django

# Force UTF-8 output
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joy_lms.settings.base')
django.setup()

from django.test import Client
from apps.accounts.models import User

c = Client(SERVER_NAME='127.0.0.1', SERVER_PORT='8000')
admin = User.objects.filter(role='admin').first()
c.force_login(admin)
r = c.get('/dashboard/institutes/4/profile/')
content = r.content.decode('utf-8')

print('STATUS:', r.status_code)

# Find the rendered profile-nav HTML
search_term = 'profile-nav">'
idx = content.rfind(search_term)
if idx > -1:
    print('NAV HTML FOUND:')
    print(content[idx:idx+600])
else:
    # Try alternate - look for btn-inst-overview
    idx2 = content.find('btn-inst-overview')
    if idx2 > -1:
        snippet = content[max(0, idx2-350):idx2+350]
        # Replace emojis to avoid encoding issues
        import re
        snippet = re.sub(r'[^\x00-\x7F]', '?', snippet)
        print('NAV SECTION FOUND:')
        print(snippet)
    else:
        print('Nav section not found')
        # Check if DIYA is in the page
        if 'DIYA' in content:
            diya_idx = content.find('DIYA')
            snippet = content[max(0,diya_idx-200):diya_idx+200]
            snippet = re.sub(r'[^\x00-\x7F]', '?', snippet)
            print('DIYA context:', snippet)
        else:
            print('DIYA not found in page')
