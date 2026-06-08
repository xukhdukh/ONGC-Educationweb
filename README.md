# Joy LMS — Django + PostgreSQL + pgvector

> **Version**: 2.0.0-django  
> **Upgraded from**: Streamlit + SQLite monolith  
> **Stack**: Django 5.2 + DRF + PostgreSQL + pgvector + Celery + Redis

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (recommended)
- OR: PostgreSQL 16+ with pgvector, Redis

### Option A — Docker Compose (Recommended)

```bash
# 1. Clone / copy this folder anywhere
cd A_LMS_upgrade

# 2. Copy env template
copy .env.example .env
# Edit .env — at minimum check DATABASE_URL and REDIS_URL

# 3. Start all services
docker-compose up --build

# 4. Run migrations (first time only)
docker-compose exec web python manage.py migrate

# 5. Create superuser
docker-compose exec web python manage.py createsuperuser

# 6. Open browser
# App: http://localhost:8000
# Admin: http://localhost:8000/admin/
# API: http://localhost:8000/api/v1/
```

### Option B — Local Python Environment

```bash
# 1. Create and activate virtualenv
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements/base.txt

# 3. Configure .env
copy .env.example .env
# Edit DATABASE_URL to point to your local PostgreSQL

# 4. Apply migrations
python manage.py migrate

# 5. Run dev server
python manage.py runserver
```

---

## 📦 Project Structure

```
A_LMS_upgrade/
├── manage.py
├── Procfile                    # Render process definitions
├── render.yaml                 # Render infrastructure-as-code
├── docker-compose.yml          # Local dev + VM deployment
├── Dockerfile
├── nginx.conf                  # VM intranet Nginx config
├── .env.example                # Environment template
├── requirements/
│   ├── base.txt                # All packages
│   ├── render.txt              # Render (inherits base)
│   └── production.txt          # VM (inherits base)
├── joy_lms/                    # Django project package
│   ├── settings/
│   │   ├── base.py             # Shared settings
│   │   ├── render.py           # Render.com overrides
│   │   └── production.py       # VM intranet overrides
│   ├── urls.py                 # Root URL config
│   ├── celery.py               # Celery + Beat config
│   ├── wsgi.py
│   └── asgi.py
├── apps/                       # Django apps (feature modules)
│   ├── accounts/               # Users, auth, institutes
│   ├── courses/                # Courses, modules, lessons, progress
│   ├── assessments/            # Quizzes, homework, activity logs
│   ├── gamification/           # Points, badges, streaks, goals
│   ├── social/                 # Timeline posts + reactions + comments
│   ├── certificates/           # PDF certificates
│   ├── analytics/              # Dashboards and reporting
│   └── ai_features/            # pgvector embeddings + semantic search
├── api/
│   └── v1/
│       └── urls.py             # Central REST API router
├── templates/                  # Django HTML templates
│   ├── base.html
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   └── dashboard/
│       └── index.html
├── static/
│   ├── css/joy_lms.css         # Main stylesheet (dark mode)
│   └── js/progress_tracker.js  # Video/PDF progress tracker
├── media/                      # Uploaded files (git-ignored)
└── scripts/
    └── migrate_sqlite_to_postgres.py  # One-time data migration
```

---

## 🔑 API Reference

Base URL: `/api/v1/`

| Endpoint | Method | Description |
|---|---|---|
| `auth/login/` | POST | JWT login → returns access + refresh tokens |
| `auth/logout/` | POST | Blacklist refresh token |
| `auth/register/` | POST | Create new user account |
| `auth/me/` | GET, PATCH | Current user profile |
| `users/` | GET, POST | User list (admin) |
| `users/{id}/link-child/` | POST | Link guardian ↔ child |
| `institutes/` | CRUD | Institute management |
| `courses/` | CRUD | Course catalog |
| `courses/{id}/enroll/` | POST | Enroll child in course |
| `courses/{id}/publish/` | POST | Toggle publish state |
| `modules/` | CRUD | Module management |
| `lessons/` | CRUD | Lesson management |
| `lessons/{id}/progress/` | GET, POST | Track watch % / completion |
| `quizzes/{id}/attempt/` | POST | Submit quiz answers → auto-grade |
| `homework/{id}/submit/` | POST | Submit homework |
| `homework/{id}/grade/` | PATCH | Grade a submission |
| `gamification/streak/` | GET, POST | Streak tracking |
| `gamification/leaderboard/` | GET | Top 20 leaderboard |
| `rewards/` | GET | Points history |
| `badges/` | GET | All badges (with earned flag) |
| `timeline/` | CRUD | Timeline posts |
| `timeline/{id}/react/` | POST | Toggle reaction |
| `timeline/{id}/comment/` | POST | Add comment |
| `certificates/` | CRUD | Certificate management |
| `certificates/{id}/download/` | GET | Stream PDF |
| `analytics/overview/` | GET | Institute overview stats |
| `analytics/child/{id}/` | GET | Per-child detailed analytics |
| `analytics/platform/` | GET | Platform-wide stats (admin) |
| `ai/search/?q=query` | GET | Semantic search |
| `ai/recommend/` | GET | Personalized course recommendations |
| `health/` | GET | Health check |

---

## 🗄️ Data Migration from Old App

```bash
# Set path to old SQLite database
set SQLITE_DB_PATH=D:\A_LMS\ajoy-academy\ajoy_academy.db

# Run migration script (after Django migrations applied)
python scripts/migrate_sqlite_to_postgres.py

# Generate AI embeddings for all lessons
python manage.py shell -c "from apps.ai_features.services import embed_all_lessons; embed_all_lessons()"

# Copy uploaded media files
# xcopy /E "D:\A_LMS\ajoy-academy\uploads\" ".\media\uploads\"
```

---

## ☁️ Deploying to Render

1. Push this folder to a GitHub repo
2. Connect repo to Render
3. Render auto-detects `render.yaml` and creates:
   - Web service (Django + Gunicorn)
   - Worker service (Celery)
   - PostgreSQL database
   - Redis instance
   - 10GB persistent disk for uploads
4. Run migrations: Render build command includes `python manage.py migrate`

---

## 🖥️ VM Intranet Deployment

```bash
# On the VM:
git clone <repo> /app
cd /app
pip install -r requirements/production.txt

# Configure environment
cp .env.example .env
nano .env  # Set DATABASE_URL, REDIS_URL, ALLOWED_HOSTS

# Run migrations
DJANGO_SETTINGS_MODULE=joy_lms.settings.production python manage.py migrate
python manage.py collectstatic --noinput

# Start with Docker Compose
docker-compose -f docker-compose.yml up -d

# OR with systemd (manual setup)
# Configure Gunicorn, Celery, Beat as systemd services
# Use nginx.conf as reverse proxy
```

---

## 🧪 Roles

| Role | Access |
|---|---|
| `admin` | Full platform access |
| `institute_admin` | Institute-scoped management |
| `teacher` | Course builder, homework grading, analytics |
| `parent` | View child progress, timeline |
| `child` | Course player, quizzes, social feed |

---

*Built with ❤️ for Joy Academy*
