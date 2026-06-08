"""
DOM Test for Course Completion Workflow
Tests: /dashboard/learn/3/lesson/15/  (first lesson, not completed)
       /dashboard/learn/3/lesson/16/  (video, not completed after reset)
       /dashboard/learn/3/lesson/17/  (quiz, last lesson)
Also tests Mark Complete API functionality
"""
import os, django, json
os.environ['DJANGO_SETTINGS_MODULE'] = 'joy_lms.settings.base'
django.setup()

# Force Celery to run tasks locally (skip Redis entirely)
from joy_lms.celery import app as celery_app
celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = False

from django.test import Client
from apps.accounts.models import User

c = Client(SERVER_NAME='127.0.0.1')
c.raise_request_exception = False  # Don't crash on Celery/Redis errors
u = User.objects.get(username='new')
c.force_login(u)

print("=" * 70)
print("DOM TEST: Course Completion Workflow")
print("=" * 70)

# ── TEST 1: Lesson 15 (first lesson, text, 10s duration) ──
print("\n--- TEST 1: Lesson 15 (Intro, text, 10s) ---")
res = c.get('/dashboard/learn/3/lesson/15/')
html = res.content.decode('utf-8')
print(f"  Status: {res.status_code}")

# Check JS variables
for var in ['LESSON_ID', 'COURSE_ID', 'LESSON_DURATION_REQ', 'TOTAL_LESSONS', 'watchedSeconds', 'lessonAlreadyCompleted']:
    import re
    match = re.search(rf'(?:const|let)\s+{var}\s*=\s*(.+?)[\s;]', html)
    if match:
        print(f"  {var} = {match.group(1).strip()}")
    else:
        print(f"  !! {var} NOT FOUND")

# Check Mark Complete button exists
mc_count = html.count('mark-complete-btn')
print(f"  Mark Complete buttons: {mc_count}")

# Check Next button exists
next_count = html.count('next-lesson-btn')
print(f"  Next Lesson buttons: {next_count}")

# Check Course Completed button
cc_count = html.count('course-completed-btn')
cert_count = html.count('Realise your Certification')
print(f"  Course Completed buttons: {cc_count}")
print(f"  Realise Certification links: {cert_count}")

# Check timer intervals
ping_count = html.count('setInterval')
print(f"  setInterval calls: {ping_count}")

# Check format_duration usage
fd_count = html.count('format_duration')
dur_display = re.findall(r'Intro.*?\(([^)]+)\)', html)
print(f"  Duration format in sidebar: {dur_display[:3] if dur_display else 'not found'}")


# ── TEST 2: Mark Complete API for lesson 15 ──
print("\n--- TEST 2: Mark Complete API for Lesson 15 ---")
try:
    res2 = c.post('/api/v1/lessons/15/progress/', 
                  json.dumps({'is_completed': True, 'watch_percentage': 100}),
                  content_type='application/json')
    data = res2.json()
    print(f"  Status: {res2.status_code}")
    print(f"  is_completed: {data.get('is_completed')}")
    print(f"  course_progress_percentage: {data.get('course_progress_percentage')}")
    print(f"  is_course_completed: {data.get('is_course_completed')}")
    print(f"  completed_lessons: {data.get('completed_lessons')}")
    print(f"  total_lessons: {data.get('total_lessons')}")
except Exception as e:
    print(f"  ERROR: {e}")


# ── TEST 3: Mark Complete API for lesson 16 ──
print("\n--- TEST 3: Mark Complete API for Lesson 16 ---")
try:
    res3 = c.post('/api/v1/lessons/16/progress/', 
                  json.dumps({'is_completed': True, 'watch_percentage': 100}),
                  content_type='application/json')
    data3 = res3.json()
    print(f"  Status: {res3.status_code}")
    print(f"  is_completed: {data3.get('is_completed')}")
    print(f"  course_progress_percentage: {data3.get('course_progress_percentage')}")
    print(f"  is_course_completed: {data3.get('is_course_completed')}")
    print(f"  completed_lessons: {data3.get('completed_lessons')}")
    print(f"  total_lessons: {data3.get('total_lessons')}")
except Exception as e:
    print(f"  ERROR: {e}")


# ── TEST 4: Mark Complete API for lesson 17 (last lesson → course complete) ──
print("\n--- TEST 4: Mark Complete API for Lesson 17 (LAST - should complete course) ---")
try:
    # First submit quiz results
    c.post('/api/v1/lessons/17/progress/', 
           json.dumps({'quiz_results': {'attempted': True, 'score': 3, 'total_questions': 3, 'percentage': 100}}),
           content_type='application/json')
    # Then mark complete
    res4 = c.post('/api/v1/lessons/17/progress/', 
                  json.dumps({'is_completed': True, 'watch_percentage': 100}),
                  content_type='application/json')
    data4 = res4.json()
    print(f"  Status: {res4.status_code}")
    print(f"  is_completed: {data4.get('is_completed')}")
    print(f"  course_progress_percentage: {data4.get('course_progress_percentage')}")
    print(f"  is_course_completed: {data4.get('is_course_completed')}")
    print(f"  completed_lessons: {data4.get('completed_lessons')}")
    print(f"  total_lessons: {data4.get('total_lessons')}")
except Exception as e:
    print(f"  ERROR: {e}")


# ── TEST 5: Verify page after ALL lessons complete ──
print("\n--- TEST 5: Lesson 17 page after course completion ---")
res5 = c.get('/dashboard/learn/3/lesson/17/')
html5 = res5.content.decode('utf-8')
print(f"  Status: {res5.status_code}")

# Check for Realise Certification
cert_link = 'Realise your Certification' in html5
print(f"  'Realise your Certification' present: {cert_link}")

# Check can_view_completion_summary
can_view = 'completion-summary' in html5
print(f"  'completion-summary' URL present: {can_view}")

# Check lessonAlreadyCompleted
match = re.search(r'lessonAlreadyCompleted\s*=\s*(true|false)', html5)
print(f"  lessonAlreadyCompleted: {match.group(1) if match else 'NOT FOUND'}")

# Check course progress
match_prog = re.search(r'Course Progress.*?(\d+(?:\.\d+)?)%', html5, re.DOTALL)
print(f"  Course Progress shown: {match_prog.group(1) if match_prog else 'NOT FOUND'}%")

print("\n" + "=" * 70)
print("DOM TEST COMPLETE")
print("=" * 70)
