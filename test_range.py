import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joy_lms.settings.base')
django.setup()

from django.http import HttpRequest, FileResponse
from django.conf import settings

req = HttpRequest()
req.META['HTTP_RANGE'] = 'bytes=0-100'

file_path = os.path.join(settings.MEDIA_ROOT, 'lessons', 'videos', 'PPE_detection_output.mp4')
resp = FileResponse(open(file_path, 'rb'))
# simulate middleware or view resolving
resp.resolve_context = lambda *args: None
# FileResponse normally needs to be processed by middleware, or maybe it handles Range on __init__?
# Let's call the WSGI or ASGI logic? No, FileResponse implements it in set_headers
resp.set_headers(req)
print('Status code:', resp.status_code)
print('Headers:', dict(resp.headers))
