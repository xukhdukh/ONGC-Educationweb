import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joy_lms.settings.base')
django.setup()

from apps.courses.models import Course

courses = Course.objects.all()
count = 0
for course in courses:
    course.save()
    count += 1
    print(f"Updated course '{course.title}' | Serial: {course.unique_id} | Code: {course.course_code}")

print(f"Successfully backfilled {count} courses.")
