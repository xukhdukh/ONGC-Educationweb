import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joy_lms.settings.base')
django.setup()

from apps.courses.models import Course
from django.utils import timezone

year = timezone.now().year
for course in Course.objects.all():
    if not course.unique_id:
        course.unique_id = f"DIYA-FY{year}-{course.pk:04d}"
        course.save()

print("Backfill complete.")
