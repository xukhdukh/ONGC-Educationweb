# Joy LMS — Migration to Scale
## Streamlit + SQLite → Django + PostgreSQL + pgvector

> **Document Date**: 2026-05-26  
> **Target Deployment**: Render (functional testing) → VM Intranet (production)  
> **Source Codebase**: `d:\A_LMS\ajoy-academy\`

---

## 1. Executive Summary

The current Joy LMS is a **Streamlit monolith** backed by **SQLite via SQLAlchemy**. It is feature-rich (16 development phases complete) with multi-role auth, course/module/lesson hierarchy, gamification, analytics, AI-ready dependencies, and custom HTML components. However, Streamlit's architecture has fundamental limits for scale:

| Constraint | Current (Streamlit+SQLite) | Target (Django+PostgreSQL) |
|---|---|---|
| Concurrency | Single-threaded per session | Full WSGI/ASGI multi-worker |
| DB | SQLite (file lock, single-writer) | PostgreSQL (MVCC, concurrent writes) |
| Auth | Cookie + st.session_state | Django Sessions / JWT (DRF) |
| API | None (monolith) | REST API (DRF) |
| Vector Search | ChromaDB (in-memory) | pgvector (persistent, SQL-native) |
| Frontend | Streamlit widgets | React/Next.js or Django templates |
| File Storage | Local `uploads/` | Render Disk / NFS / S3-compatible |
| Background Jobs | APScheduler (in-process) | Celery + Redis (already in deps) |
| Deployment | `streamlit run app.py` | Gunicorn + Nginx + Docker |

The migration is **additive and non-destructive**: the existing SQLite database is used as the data migration source, and the new Django app is built alongside it. The Streamlit app remains live until Django reaches feature parity.

---

## 2. Current Architecture — Codebase Inventory

### 2.1 Application Structure

```
ajoy-academy/
├── app.py                    # Streamlit entry point + router
├── config.py                 # DB URL, upload dirs, content types
├── auth/
│   ├── login.py              # bcrypt login form
│   ├── register.py           # role-based registration
│   ├── session.py            # st.session_state + cookie management
│   └── permissions.py        # role-based decorators
├── database/
│   ├── engine.py             # SQLAlchemy engine + SessionLocal + Base
│   └── models.py             # 21 SQLAlchemy models (410 lines)
├── dashboard/
│   ├── admin_dashboard.py    # admin + institute_admin
│   ├── teacher_dashboard.py  # teacher
│   ├── parent_dashboard.py   # parent
│   └── child_dashboard.py    # child (gamified hub)
├── modules/
│   ├── courses.py            # 129KB — Course builder, player, enrollment
│   ├── analytics.py          # Plotly dashboards
│   ├── quizzes.py            # XLS quiz builder + interactive player
│   ├── homework.py           # Assignment + grading queue
│   ├── timeline.py           # Social feed + moderation
│   ├── rewards.py            # Points, badges, streaks
│   ├── certificates.py       # PDF cert generation (reportlab)
│   ├── leaderboard.py        # Weekly + all-time rankings
│   ├── profile.py            # User profile management
│   ├── institutes.py         # Multi-institute management
│   └── user_management.py    # Admin user CRUD
├── components/
│   ├── navbar.py / sidebar.py / cards.py / post_composer.py
│   ├── youtube_tracker/      # Custom Streamlit component (Iframe API)
│   └── pdf_tracker/          # Custom Streamlit component (scroll depth)
└── utils/
    ├── gsheets.py            # Google Sheets integration
    └── pdf_generator.py      # reportlab certificate generator
```

### 2.2 Data Models (21 SQLAlchemy Models → Django Models)

| SQLAlchemy Model | Table | Key Relations |
|---|---|---|
| `User` | `users` | roles: admin, institute_admin, teacher, parent, child |
| `UserRelation` | `user_relations` | guardian_id ↔ child_id |
| `Institute` | `institutes` | multi-institute support |
| `UserInstitute` | `user_institutes` | M2M: User ↔ Institute |
| `Course` | `courses` | creator, institute, access_type, difficulty |
| `Module` | `modules` | course FK, order_index, lock logic |
| `Lesson` | `lessons` | module FK, lesson_type, quiz_data JSON |
| `Quiz` | `quizzes` | course + module FK, JSON questions |
| `Homework` | `homeworks` | course + module FK, multi-type |
| `HomeworkSubmission` | `homework_submissions` | child, grader FKs |
| `Enrollment` | `enrollments` | child ↔ course, progress_percentage |
| `LessonProgress` | `lesson_progresses` | watch %, duration, quiz_results JSON |
| `QuizAttempt` | `quiz_attempts` | answers JSON, score, passed |
| `ActivityLog` | `activity_logs` | action_type, session_duration, metadata JSON |
| `Reward` | `rewards` | points, reference_type/id |
| `Badge` | `badges` | criteria_type, tier |
| `UserBadge` | `user_badges` | M2M: User ↔ Badge |
| `Streak` | `streaks` | current/longest streak, freeze_count |
| `WeeklyGoal` | `weekly_goals` | target vs actual metrics |
| `Certificate` | `certificates` | cert_number, PDF path |
| `TimelinePost` | `timeline_posts` | media_paths JSON, auto_post_type |
| `TimelineReaction` | `timeline_reactions` | post ↔ user, reaction_type |
| `TimelineComment` | `timeline_comments` | post ↔ user, text |

### 2.3 Key Dependencies Already Present

The `requirements.txt` already contains the full target stack — no new installs needed:

```
Django==5.2.1
djangorestframework==3.16.0
psycopg2-binary==2.9.10
pgvector==0.4.2
celery==5.6.3
redis==7.4.0
whitenoise==6.12.0
sentence-transformers==5.0.0
langchain==1.2.15
langchain-community==0.4.1
```

Additional packages to add:
```
gunicorn
django-environ
djangorestframework-simplejwt
django-cors-headers
```

---

## 3. Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RENDER (Testing)                         │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │   Frontend   │    │   Django     │    │  PostgreSQL      │  │
│  │  (React /    │◄──►│   + DRF      │◄──►│  + pgvector      │  │
│  │  Next.js or  │    │  (Gunicorn)  │    │  (Render DB)     │  │
│  │  Templates)  │    └──────┬───────┘    └──────────────────┘  │
│  └──────────────┘           │                                   │
│                      ┌──────┴───────┐    ┌──────────────────┐  │
│                      │   Celery     │◄──►│  Redis           │  │
│                      │  (Workers)   │    │  (Render Redis)  │  │
│                      └──────────────┘    └──────────────────┘  │
│                                          ┌──────────────────┐  │
│                                          │  Render Disk     │  │
│                                          │  (File Uploads)  │  │
│                                          └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    VM INTRANET (Production)                      │
│                                                                 │
│  Nginx (reverse proxy + SSL)                                    │
│    ├── → Django (Gunicorn, multiple workers)                    │
│    └── → Static files (whitenoise / Nginx direct)              │
│                                                                 │
│  PostgreSQL + pgvector (dedicated server or same VM)           │
│  Redis (Celery broker + cache)                                  │
│  NFS / local volume (file uploads)                              │
│  Celery workers (badge awards, cert generation, AI tasks)       │
└─────────────────────────────────────────────────────────────────┘
```

### Django App Structure (Target)

```
joy_lms/                      # Django project root
├── manage.py
├── joy_lms/                  # Project settings package
│   ├── settings/
│   │   ├── base.py
│   │   ├── render.py         # Render-specific settings
│   │   └── production.py     # VM intranet settings
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/             # User, UserRelation, Institute, UserInstitute
│   ├── courses/              # Course, Module, Lesson, Enrollment, LessonProgress
│   ├── assessments/          # Quiz, QuizAttempt, Homework, HomeworkSubmission
│   ├── gamification/         # Reward, Badge, UserBadge, Streak, WeeklyGoal
│   ├── social/               # TimelinePost, TimelineReaction, TimelineComment
│   ├── certificates/         # Certificate + PDF generation
│   ├── analytics/            # Analytics views (no models)
│   └── ai_features/          # pgvector embeddings, semantic search
├── api/                      # DRF ViewSets + Routers
│   └── v1/
├── frontend/                 # Django templates (or React build output)
├── media/                    # Uploaded files (mapped to disk/NFS)
├── static/
├── requirements/
│   ├── base.txt
│   ├── render.txt
│   └── production.txt
├── Procfile                  # Render process file
├── render.yaml               # Render infrastructure-as-code
└── docker-compose.yml        # Local dev + VM deployment
```

---

## 4. Migration Phases

---

### PHASE 0 — Preparation and Environment Setup
**Duration**: 1–2 days  
**Goal**: Scaffold the Django project alongside the existing Streamlit app

#### Tasks

- [ ] Create `joy_lms/` Django project at `d:\A_LMS\joy_lms\`
- [ ] Install target packages: `django-environ`, `gunicorn`, `django-cors-headers`
- [ ] Configure `settings/base.py`: installed apps, middleware, DRF, static/media
- [ ] Configure `settings/render.py`: DATABASE_URL from env, ALLOWED_HOSTS, whitenoise
- [ ] Set up `.env` file with `DATABASE_URL`, `SECRET_KEY`, `REDIS_URL`
- [ ] Add `render.yaml` for infrastructure-as-code (web service + PostgreSQL + Redis)
- [ ] Add `Procfile`: `web: gunicorn joy_lms.wsgi --workers 2`
- [ ] Add `docker-compose.yml` for local dev (postgres + redis + django)
- [ ] Add `requirements/base.txt`, `requirements/render.txt`
- [ ] Verify: `python manage.py check` passes with no errors

#### Key Config Snippet

```python
# joy_lms/settings/base.py (excerpt)
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'pgvector.django',
    'apps.accounts',
    'apps.courses',
    'apps.assessments',
    'apps.gamification',
    'apps.social',
    'apps.certificates',
    'apps.analytics',
    'apps.ai_features',
]

AUTH_USER_MODEL = 'accounts.User'   # Custom user model

DATABASES = {
    'default': env.db('DATABASE_URL')  # django-environ parses postgres://...
}
```

```yaml
# render.yaml
services:
  - type: web
    name: joy-lms
    env: python
    buildCommand: pip install -r requirements/render.txt && python manage.py migrate && python manage.py collectstatic --noinput
    startCommand: gunicorn joy_lms.wsgi --workers 2 --bind 0.0.0.0:$PORT
    disk:
      name: joy-lms-uploads
      mountPath: /app/media
      sizeGB: 10
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: joy-lms-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: joy-lms-redis
          type: redis
          property: connectionString

databases:
  - name: joy-lms-db
    databaseName: joy_lms
    user: joy_lms_user
```

---

### PHASE 1 — PostgreSQL + pgvector Setup
**Duration**: 1 day  
**Goal**: Running PostgreSQL with pgvector extension, schema created

#### Tasks

- [ ] Create Render PostgreSQL service (or local Docker postgres+pgvector image)
- [ ] Enable pgvector extension via migration:

```python
# apps/ai_features/migrations/0001_enable_pgvector.py
from django.db import migrations

class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS vector;")
    ]
```

- [ ] Verify: `SELECT * FROM pg_extension WHERE extname = 'vector';` returns a row
- [ ] Configure connection pooling: set `CONN_MAX_AGE = 60` in settings
- [ ] Test Django ORM can write and read VectorField

---

### PHASE 2 — Django Model Migration (SQLAlchemy → Django ORM)
**Duration**: 3–4 days  
**Goal**: All 21 models ported to Django ORM, migrations generated and applied

#### Model-to-App Mapping

| Django App | Models |
|---|---|
| `apps.accounts` | `User`, `UserRelation`, `Institute`, `UserInstitute` |
| `apps.courses` | `Course`, `Module`, `Lesson`, `Enrollment`, `LessonProgress` |
| `apps.assessments` | `Quiz`, `QuizAttempt`, `Homework`, `HomeworkSubmission` |
| `apps.gamification` | `Reward`, `Badge`, `UserBadge`, `Streak`, `WeeklyGoal` |
| `apps.social` | `TimelinePost`, `TimelineReaction`, `TimelineComment` |
| `apps.certificates` | `Certificate` |

#### Custom User Model

```python
# apps/accounts/models.py
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, username, email, password, role, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, role=role, **extra_fields)
        user.set_password(password)  # Django handles bcrypt internally
        user.save()
        return user

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Admin'), ('institute_admin', 'Institute Admin'),
        ('teacher', 'Teacher'), ('parent', 'Parent'), ('child', 'Child'),
    ]
    username     = models.CharField(max_length=50, unique=True)
    email        = models.EmailField(unique=True)
    role         = models.CharField(max_length=20, choices=ROLE_CHOICES)
    full_name    = models.CharField(max_length=100, blank=True)
    avatar_emoji = models.CharField(max_length=10, default='👤')
    date_of_birth    = models.DateField(null=True, blank=True)
    is_active        = models.BooleanField(default=True)
    is_staff         = models.BooleanField(default=False)
    created_at       = models.DateTimeField(auto_now_add=True)
    profile_photo    = models.CharField(max_length=255, blank=True)
    description      = models.CharField(max_length=100, blank=True)
    contact_address  = models.CharField(max_length=255, blank=True)
    mobile_no        = models.CharField(max_length=20, blank=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'role']
    objects = UserManager()
```

#### pgvector Fields (New — AI Enhancement)

```python
# apps/ai_features/models.py
from pgvector.django import VectorField
from django.db import models

class LessonEmbedding(models.Model):
    lesson       = models.OneToOneField('courses.Lesson', on_delete=models.CASCADE, related_name='embedding')
    embedding    = VectorField(dimensions=384)   # sentence-transformers all-MiniLM-L6-v2
    content_hash = models.CharField(max_length=64)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(name='lesson_emb_hnsw', fields=['embedding'],
                         opclasses=['vector_cosine_ops'])
        ]

class CourseEmbedding(models.Model):
    course     = models.OneToOneField('courses.Course', on_delete=models.CASCADE, related_name='embedding')
    embedding  = VectorField(dimensions=384)
    updated_at = models.DateTimeField(auto_now=True)
```

#### JSON Fields

All SQLAlchemy `JSON` columns map directly to Django `models.JSONField()` (PostgreSQL JSONB):

```python
# SQLAlchemy:  quiz_data = Column(JSON, nullable=True)
# Django ORM:  quiz_data = models.JSONField(null=True, blank=True)
```

#### Data Migration Script (SQLite → PostgreSQL)

```python
# scripts/migrate_sqlite_to_postgres.py
"""
Run ONCE after Django migrations are applied.
Reads existing ajoy_academy.db and bulk-inserts into PostgreSQL.
Preserves all IDs, relationships, and JSON fields.
Order: users → institutes → user_institutes → user_relations →
       courses → modules → lessons → quizzes → homeworks →
       enrollments → lesson_progresses → quiz_attempts →
       rewards → badges → user_badges → streaks → weekly_goals →
       certificates → timeline_posts → timeline_reactions →
       timeline_comments → activity_logs
"""
import sqlite3, django, os, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joy_lms.settings.render')
django.setup()

from apps.accounts.models import User, Institute, UserInstitute, UserRelation

SQLITE_PATH = r"d:\A_LMS\ajoy-academy\ajoy_academy.db"
conn = sqlite3.connect(SQLITE_PATH)
conn.row_factory = sqlite3.Row

def migrate_users():
    rows = conn.execute("SELECT * FROM users").fetchall()
    for r in rows:
        obj, created = User.objects.get_or_create(
            id=r['id'],
            defaults={
                'username':  r['username'],
                'email':     r['email'],
                'password':  r['password_hash'],  # bcrypt hash — compatible directly
                'role':      r['role'],
                'full_name': r['full_name'] or '',
                'is_active': bool(r['is_active']),
            }
        )
    print(f"Users migrated: {User.objects.count()}")

# ... repeat pattern for all 21 models
```

> [!IMPORTANT]
> Existing bcrypt password hashes from the SQLite database are **fully compatible** with Django's `AbstractBaseUser.password` field. No password resets required for existing users.

---

### PHASE 3 — Authentication Layer
**Duration**: 2 days  
**Goal**: Django auth + JWT tokens, replacing Streamlit sessions + cookies

#### Strategy

| Current (Streamlit) | Target (Django + DRF) |
|---|---|
| `st.session_state['user_id']` | Django session cookie OR JWT Bearer token |
| `bcrypt.checkpw()` | `user.check_password()` (Django handles bcrypt) |
| `streamlit-cookies-controller` | `HttpOnly` session cookie (secure, SameSite=Lax) |
| Role stored in session_state | `request.user.role` attribute |
| `permissions.py` decorators | DRF `IsAuthenticated` + custom `IsRole` permission classes |

#### Auth Endpoints

```python
# api/v1/auth/urls.py
urlpatterns = [
    path('login/',    LoginView.as_view()),          # POST → returns JWT pair
    path('logout/',   LogoutView.as_view()),         # POST → blacklists refresh token
    path('register/', RegisterView.as_view()),       # POST → creates user
    path('refresh/',  TokenRefreshView.as_view()),   # POST → rotates tokens
    path('me/',       CurrentUserView.as_view()),    # GET → returns user profile
]
```

#### Role Permission Classes

```python
# apps/accounts/permissions.py
from rest_framework.permissions import BasePermission

class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'teacher'

class IsParentOrTeacher(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['parent', 'teacher']

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'institute_admin']
```

---

### PHASE 4 — REST API Layer (Django REST Framework)
**Duration**: 5–7 days  
**Goal**: Full REST API covering all LMS features

#### API Surface (v1)

```
/api/v1/
├── auth/
│   ├── login/           POST
│   ├── logout/          POST
│   ├── register/        POST
│   ├── refresh/         POST
│   └── me/              GET, PATCH
├── users/               GET, POST, GET/{id}, PATCH/{id}, DELETE/{id}
│   └── {id}/link-child/ POST
├── institutes/          GET, POST, GET/{id}, PATCH/{id}, DELETE/{id}
│   └── {id}/members/    GET, POST, DELETE
├── courses/             GET, POST, GET/{id}, PATCH/{id}, DELETE/{id}
│   ├── {id}/enroll/     POST
│   ├── {id}/publish/    POST
│   └── {id}/analytics/  GET
├── modules/             GET, POST, GET/{id}, PATCH/{id}, DELETE/{id}
│   └── {id}/reorder/    POST
├── lessons/             GET, POST, GET/{id}, PATCH/{id}, DELETE/{id}
│   ├── {id}/progress/   GET, POST  (track watch %, duration)
│   └── {id}/reorder/    POST
├── quizzes/             GET, POST, GET/{id}, PATCH/{id}
│   └── {id}/attempt/    POST  (submit answers → grade → award points)
├── homework/            GET, POST, GET/{id}, PATCH/{id}
│   ├── {id}/submit/     POST
│   └── {id}/grade/      PATCH
├── gamification/
│   ├── rewards/         GET
│   ├── badges/          GET, GET/{id}
│   ├── my-badges/       GET
│   ├── streak/          GET, POST
│   └── leaderboard/     GET
├── timeline/
│   ├── posts/           GET, POST, GET/{id}, DELETE/{id}
│   ├── posts/{id}/react/    POST
│   ├── posts/{id}/comment/  POST, DELETE
│   └── posts/{id}/approve/  POST
├── certificates/        GET, POST/{child_id}/{course_id}
│   └── {id}/download/   GET  (streams PDF)
├── analytics/
│   ├── overview/        GET
│   ├── child/{id}/      GET
│   └── platform/        GET  (admin-only)
└── ai/
    ├── search/          GET ?q=query  (semantic search)
    ├── recommend/       GET           (personalized course recommendations)
    └── similar/         GET ?lesson_id=X
```

#### ViewSet Example

```python
# api/v1/courses/views.py
class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.select_related('creator').prefetch_related('modules')
        if user.role == 'child':
            return qs.filter(enrollments__child=user, is_published=True)
        if user.role in ['teacher', 'parent']:
            inst_id = user.userinstitute_set.values_list('institute_id', flat=True).first()
            return qs.filter(institute_id=inst_id)
        return qs  # admin sees all

    @action(detail=True, methods=['post'], permission_classes=[IsParentOrTeacher])
    def publish(self, request, pk=None):
        course = self.get_object()
        course.is_published = not course.is_published
        course.save()
        return Response({'is_published': course.is_published})
```

---

### PHASE 5 — Frontend Strategy
**Duration**: 7–10 days  
**Goal**: Replace Streamlit widgets with a proper web UI

> [!IMPORTANT]
> **Decision Required Before Starting Phase 5**: Choose one of the two options below.

#### Option A: Django Templates + HTMX (Faster Delivery)

- Server-side rendered pages via Django templates
- HTMX for dynamic interactions without full page reloads
- Alpine.js for lightweight UI state (quiz timer, modal toggles)
- Plotly.js for analytics charts (replaces Streamlit plotly)
- Advantages: No separate frontend deployment, faster to build, simpler for intranet
- Disadvantages: Less reactive UX than full SPA

#### Option B: React / Next.js (Recommended for Long-term Scale)

- Full SPA consuming the DRF API
- Next.js for SSR + file-based routing
- Recharts or Plotly.js for analytics
- Hosted on Render Static Site or same VM Nginx
- Advantages: Best user experience, mobile-ready, easier future mobile app port
- Disadvantages: More build complexity, separate deployment pipeline

#### Page Structure (applies to both options)

| Page | Roles | Key Features |
|---|---|---|
| `/login` | All | Form, persistent login checkbox |
| `/register` | All | Role selector, guardian link for child |
| `/dashboard` | All | Role-based redirect to appropriate hub |
| `/courses` | All | Catalog, enroll, filter by category/age |
| `/courses/:id` | Child | Player: video, PDF, text, quiz, nav |
| `/builder` | Teacher/Parent | Course tree builder |
| `/builder/:id` | Teacher/Parent | Module/Lesson editor panel |
| `/homework` | Teacher/Child | Assignment list + submission |
| `/homework/:id/grade` | Teacher | Grading queue |
| `/timeline` | All | Social feed, compose, react, comment |
| `/analytics` | Teacher/Parent/Admin | Plotly charts per child |
| `/leaderboard` | Child | Weekly + Hall of Fame |
| `/profile` | All | Profile view + edit |
| `/admin/users` | Admin | User CRUD |
| `/admin/institutes` | Admin | Multi-institute management |
| `/certificates` | Child/Teacher | Certificate gallery + PDF download |

#### YouTube Tracker Migration

The current `components/youtube_tracker/index.html` (custom Streamlit iframe component) becomes a standard `<iframe>` + JavaScript module. It sends progress updates to `/api/v1/lessons/{id}/progress/` every 5 seconds via `fetch()`.

#### PDF Tracker Migration

The `components/pdf_tracker/index.html` (scroll-sensing PDF embed) becomes a standard `<embed>` element with a `scroll` event listener posting to the same progress endpoint.

---

### PHASE 6 — Feature-by-Feature Migration
**Duration**: 8–12 days  
**Goal**: All Streamlit module functions reproduced as API + frontend views

Migrate in this order (lowest dependency first):

| # | Module | Source File | Target App |
|---|---|---|---|
| 1 | User Management | `modules/user_management.py` | `accounts` |
| 2 | Institute Management | `modules/institutes.py` | `accounts` |
| 3 | Course Builder | `modules/courses.py` (builder) | `courses` |
| 4 | Course Player | `modules/courses.py` (player) | `courses` |
| 5 | Quiz System | `modules/quizzes.py` + XLS logic | `assessments` |
| 6 | Homework | `modules/homework.py` | `assessments` |
| 7 | Gamification | `modules/rewards.py`, `leaderboard.py` | `gamification` |
| 8 | Certificates | `modules/certificates.py` | `certificates` |
| 9 | Timeline | `modules/timeline.py` | `social` |
| 10 | Analytics | `modules/analytics.py` | `analytics` |
| 11 | Profile | `modules/profile.py` | `accounts` |

#### Background Tasks (Celery Migration)

Move these from in-process Streamlit execution to Celery tasks:

```python
# apps/gamification/tasks.py
from celery import shared_task

@shared_task
def award_badge_if_eligible(user_id, trigger_event):
    """Check badge criteria and award after quiz/lesson completion."""

@shared_task
def update_streak(user_id):
    """Daily streak check. Scheduled via Celery Beat."""

# apps/certificates/tasks.py
@shared_task
def generate_certificate_pdf(child_id, course_id):
    """Generate PDF in background, update Certificate.pdf_file_path."""

# apps/ai_features/tasks.py
@shared_task
def embed_lesson_task(lesson_id):
    """Generate and store pgvector embedding for a lesson."""
```

```python
# joy_lms/celery.py — Scheduled tasks
app.conf.beat_schedule = {
    'update-all-streaks-daily': {
        'task': 'apps.gamification.tasks.update_all_streaks',
        'schedule': crontab(hour=0, minute=5),
    },
    'compute-weekly-goals': {
        'task': 'apps.analytics.tasks.compute_all_weekly_goals',
        'schedule': crontab(day_of_week='monday', hour=1, minute=0),
    },
}
```

---

### PHASE 7 — AI Features with pgvector
**Duration**: 3–4 days  
**Goal**: Semantic search, personalized recommendations, content similarity

#### Embedding Pipeline

```python
# apps/ai_features/services.py
from sentence_transformers import SentenceTransformer
import hashlib

model = SentenceTransformer('all-MiniLM-L6-v2')  # 384-dim, fast

def embed_lesson(lesson_id: int):
    lesson = Lesson.objects.get(id=lesson_id)
    text = f"{lesson.title} {lesson.content_text or ''}"[:2000]
    content_hash = hashlib.sha256(text.encode()).hexdigest()

    # Skip if content unchanged
    if LessonEmbedding.objects.filter(lesson=lesson, content_hash=content_hash).exists():
        return

    vector = model.encode(text).tolist()
    LessonEmbedding.objects.update_or_create(
        lesson=lesson,
        defaults={'embedding': vector, 'content_hash': content_hash}
    )

def embed_all_lessons():
    """Backfill — run once after data migration via manage.py shell."""
    for lesson in Lesson.objects.all():
        embed_lesson(lesson.id)
```

#### Semantic Search API

```python
# api/v1/ai/views.py
from pgvector.django import CosineDistance

class SemanticSearchView(APIView):
    def get(self, request):
        query = request.query_params.get('q', '')
        query_vector = model.encode(query).tolist()

        results = (
            LessonEmbedding.objects
            .annotate(distance=CosineDistance('embedding', query_vector))
            .filter(distance__lt=0.5)
            .select_related('lesson__module__course')
            .order_by('distance')[:10]
        )
        return Response({'results': [
            {
                'lesson_id': r.lesson.id,
                'lesson_title': r.lesson.title,
                'course_title': r.lesson.module.course.title,
                'similarity': round(1 - r.distance, 3),
            } for r in results
        ]})
```

#### Auto-embed on Lesson Save (Django Signal)

```python
# apps/courses/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Lesson)
def trigger_lesson_embedding(sender, instance, **kwargs):
    from apps.ai_features.tasks import embed_lesson_task
    embed_lesson_task.delay(instance.id)  # Non-blocking background task
```

---

### PHASE 8 — File Storage Migration
**Duration**: 1–2 days  
**Goal**: Uploaded files accessible in both Render and VM environments

#### Current File Categories

| Type | Current Path | Volume |
|---|---|---|
| Course PDFs | `uploads/pdfs/` | Medium |
| Homework submissions | `uploads/homework_submissions/` | High |
| Timeline media | `uploads/timeline_media/` | High |
| Certificates | `uploads/certificates/` | Medium |
| Videos | `uploads/videos/` | Very High |
| Notes | `uploads/notes/` | Low |

#### Render: Persistent Disk

```python
# settings/render.py
MEDIA_ROOT = '/app/media/'
MEDIA_URL  = '/media/'
```

#### VM Intranet: NFS or Local Volume

```python
# settings/production.py
MEDIA_ROOT = '/mnt/lms_storage/media/'   # NFS mount or local volume
MEDIA_URL  = '/media/'
# Nginx serves /media/ directly — faster than Django serving files
```

#### File Migration (one-time)

```bash
# Copy uploads from Windows dev machine to Render disk (via scp/sftp) or VM
scp -r "d:/A_LMS/ajoy-academy/uploads/" user@render-shell:/app/media/
```

---

### PHASE 9 — Render Deployment (Functional Testing)
**Duration**: 2–3 days  
**Goal**: Full app live on Render, accessible for team testing

#### Render Services

| Service | Type | Plan |
|---|---|---|
| `joy-lms` | Web Service (Python) | Starter ($7/mo) |
| `joy-lms-db` | PostgreSQL | Free (1GB) → Starter for more |
| `joy-lms-redis` | Redis | Free |
| `joy-lms-worker` | Background Worker (Celery) | Starter |
| `joy-lms-uploads` | Persistent Disk | 10GB |

#### Deployment Checklist

- [ ] `render.yaml` committed to git repository
- [ ] All secret env vars set in Render dashboard: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`
- [ ] `python manage.py collectstatic` runs in build command
- [ ] `python manage.py migrate` runs in build command
- [ ] Data migration script `migrate_sqlite_to_postgres.py` run manually once via Render shell
- [ ] `embed_all_lessons()` run once via `python manage.py shell`
- [ ] Verify all API endpoints via DRF browsable API or Postman
- [ ] Verify frontend pages load and render correctly
- [ ] Verify file uploads work (PDF lesson, homework submission)
- [ ] Verify Celery tasks execute (badge award after quiz completion)
- [ ] Verify YouTube tracker posts progress every 5 seconds
- [ ] Verify PDF tracker scroll depth updates correctly
- [ ] Verify certificate PDF generation and download
- [ ] End-to-end test for all 5 user roles

#### Render Build Command

```bash
pip install -r requirements/render.txt \
  && python manage.py migrate \
  && python manage.py collectstatic --noinput
```

---

### PHASE 10 — VM Intranet Deployment (Production)
**Duration**: 2–3 days  
**Goal**: Self-hosted deployment on intranet VM with Nginx + Docker

#### VM Requirements

| Component | Minimum | Recommended |
|---|---|---|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Disk | 50 GB | 100 GB (for media files + model weights) |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

#### Docker Compose (VM)

```yaml
# docker-compose.yml
version: '3.9'
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: joy_lms
      POSTGRES_USER: joy_lms_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  web:
    build: .
    command: gunicorn joy_lms.wsgi --workers 4 --bind 0.0.0.0:8000
    environment:
      - DATABASE_URL=postgres://joy_lms_user:${DB_PASSWORD}@db:5432/joy_lms
      - REDIS_URL=redis://redis:6379/0
      - DJANGO_SETTINGS_MODULE=joy_lms.settings.production
    volumes:
      - ./media:/app/media
      - ./static:/app/static
    depends_on:
      - db
      - redis
    ports:
      - "8000:8000"
    restart: unless-stopped

  worker:
    build: .
    command: celery -A joy_lms worker --loglevel=info --concurrency=2
    environment:
      - DATABASE_URL=postgres://joy_lms_user:${DB_PASSWORD}@db:5432/joy_lms
      - REDIS_URL=redis://redis:6379/0
      - DJANGO_SETTINGS_MODULE=joy_lms.settings.production
    depends_on:
      - db
      - redis
    restart: unless-stopped

  beat:
    build: .
    command: celery -A joy_lms beat --loglevel=info
    depends_on:
      - redis
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

#### Nginx Configuration

```nginx
# /etc/nginx/sites-available/joy_lms
server {
    listen 80;
    server_name lms.yourintranet.local;

    client_max_body_size 200M;    # Match current 200MB max upload

    location /media/ {
        alias /app/media/;
        expires 1d;
    }

    location /static/ {
        alias /app/static/;
        expires 7d;
    }

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }
}
```

#### Zero-Downtime Cutover

```bash
# 1. Final sync of SQLite delta to PostgreSQL
python scripts/migrate_sqlite_to_postgres.py --delta-only

# 2. Deploy new containers
docker-compose pull && docker-compose up -d --no-deps web worker beat

# 3. Update Nginx
nginx -s reload

# 4. Verify health check
curl http://lms.yourintranet.local/api/v1/health/
```

---

## 5. Feature Parity Checklist

| Feature | Streamlit | Django |
|---|---|---|
| Login / Logout | ✅ Live | ⬜ |
| Register (all 5 roles) | ✅ Live | ⬜ |
| Persistent login (cookie/JWT) | ✅ Live | ⬜ |
| Multi-institute support | ✅ Live | ⬜ |
| Course catalog | ✅ Live | ⬜ |
| Course builder (tree UI) | ✅ Live | ⬜ |
| Course player (video/PDF/text/quiz) | ✅ Live | ⬜ |
| YouTube progress tracking | ✅ Live | ⬜ |
| PDF scroll tracking | ✅ Live | ⬜ |
| Quiz (XLS upload + randomized player) | ✅ Live | ⬜ |
| Homework assignment + grading | ✅ Live | ⬜ |
| Points + rewards | ✅ Live | ⬜ |
| Badges (auto-award on triggers) | ✅ Live | ⬜ |
| Daily streaks | ✅ Live | ⬜ |
| Leaderboard (weekly + all-time) | ✅ Live | ⬜ |
| Certificate PDF generation | ✅ Live | ⬜ |
| Timeline / social feed | ✅ Live | ⬜ |
| Analytics dashboard (Plotly) | ✅ Live | ⬜ |
| User management (admin CRUD) | ✅ Live | ⬜ |
| **Semantic search (NEW)** | ⬜ New | ⬜ |
| **Course recommendations (NEW)** | ⬜ New | ⬜ |
| **Similar content discovery (NEW)** | ⬜ New | ⬜ |

---

## 6. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `quiz_data` / `quiz_results` JSON schema drift | Medium | Medium | Validate JSON structure before bulk insert |
| `watch_duration_seconds` data loss during migration | Low | High | Verify row counts + checksum comparison after migration |
| bcrypt hashes incompatible with Django AbstractBaseUser | Low | High | Test 3–4 existing hashes via `user.check_password()` before bulk migrate |
| Render free PostgreSQL 1GB fills up | Medium | Medium | Monitor; upgrade to Starter plan before go-live |
| Celery tasks fail silently | Medium | Medium | Add Flower monitoring dashboard; configure Sentry or email alerts |
| AI embedding model slow on first run | Medium | Low | Run backfill as background Celery task, not on startup |
| VM disk space for media + DB + model weights | Medium | Medium | Separate media volume; plan 100GB minimum |
| Render cold starts causing slow first response | Low | Low | Set to always-on; keep Celery worker active as keepalive |

---

## 7. Cutover Strategy

### Parallel Running Period (Recommended: 2–4 weeks)

1. Keep Streamlit app running on existing port during the Django build phase
2. All new data goes into PostgreSQL (Django); Streamlit continues using SQLite
3. Before final cutover: run `migrate_sqlite_to_postgres.py` once more to catch delta
4. Cutover: point DNS / intranet hostname to Django server; take Streamlit offline
5. Post-cutover: Keep Streamlit app archived for 2 weeks as rollback option

---

## 8. Summary Timeline

| Phase | Description | Duration | Cumulative |
|---|---|---|---|
| 0 | Project scaffolding + env setup | 1–2 days | 2 days |
| 1 | PostgreSQL + pgvector setup | 1 day | 3 days |
| 2 | Django models + data migration script | 3–4 days | 7 days |
| 3 | Auth layer (JWT + roles) | 2 days | 9 days |
| 4 | REST API (DRF, all endpoints) | 5–7 days | 16 days |
| 5 | Frontend (templates or React) | 7–10 days | 26 days |
| 6 | Feature migration (all modules) | 8–12 days | 38 days |
| 7 | AI features (pgvector) | 3–4 days | 42 days |
| 8 | File storage migration | 1–2 days | 44 days |
| 9 | Render deployment + functional testing | 2–3 days | 47 days |
| 10 | VM intranet deployment | 2–3 days | 50 days |

**Total estimated duration: 6–8 weeks** (solo developer, part-time)  
**With 2 developers in parallel: 4–5 weeks**

---

## 9. Quick Start Commands

```bash
# 1. Create Django project (run from d:\A_LMS\)
python -m django startproject joy_lms .

# 2. Create app directories
mkdir -p apps/{accounts,courses,assessments,gamification,social,certificates,analytics,ai_features}
for app in accounts courses assessments gamification social certificates analytics ai_features; do
    python manage.py startapp $app apps/$app
done

# 3. Start local dev DB with Docker
docker run -d --name joy_lms_pg \
  -e POSTGRES_DB=joy_lms -e POSTGRES_USER=joy_lms_user -e POSTGRES_PASSWORD=devpassword \
  -p 5432:5432 pgvector/pgvector:pg16

# 4. Run migrations
python manage.py migrate

# 5. Migrate existing data
python scripts/migrate_sqlite_to_postgres.py

# 6. Backfill AI embeddings
python manage.py shell -c "from apps.ai_features.services import embed_all_lessons; embed_all_lessons()"

# 7. Start Celery worker (separate terminal)
celery -A joy_lms worker --loglevel=info

# 8. Run dev server
python manage.py runserver
```

---

*This is a living document. Update Feature Parity Checklist as each module goes live.*  
*Cross-reference with `Dev_plan/ALMS_dev_exec.md` for complete feature inventory.*
