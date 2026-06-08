# DIYA LMS — Big Data Architecture & Infrastructure Plan

> **Document Version**: 1.0  
> **Date**: 6 June 2026  
> **Author**: Architecture Review (AI-assisted)  
> **Status**: DRAFT — Awaiting Stakeholder Review

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [Phase 1 — SQLite Cleanup & PostgreSQL Hardening](#3-phase-1--sqlite-cleanup--postgresql-hardening)
4. [Phase 2 — MinIO Object Storage Integration](#4-phase-2--minio-object-storage-integration)
5. [Phase 3 — DXus Community Timeline (Near Real-Time)](#5-phase-3--dxus-community-timeline-near-real-time)
6. [Phase 4 — AI Layer & RAG Pipeline Readiness](#6-phase-4--ai-layer--rag-pipeline-readiness)
7. [Revised System Architecture Diagram](#7-revised-system-architecture-diagram)
8. [Database Schema Enhancements](#8-database-schema-enhancements)
9. [Infrastructure & DevOps](#9-infrastructure--devops)
10. [Risk Assessment & Mitigation](#10-risk-assessment--mitigation)
11. [Implementation Roadmap](#11-implementation-roadmap)

---

## 1. Executive Summary

DIYA LMS is transitioning from a learning management system to a full **enterprise knowledge & community platform** (DXus). This document outlines the architecture changes required to:

- **Remove the legacy SQLite database** (currently an empty artifact, all live data is already in PostgreSQL).
- **Introduce MinIO** as an S3-compatible object store for all binary assets (images, videos, PDFs, certificates).
- **Optimise the DXus Community Timeline** for near real-time feeds with images/video uploads at scale.
- **Prepare the AI layer** for pgvector semantic search, RAG pipelines, and content ingestion.

---

## 2. Current State Analysis

### 2.1 What's Working Well ✅

| Component | Status | Details |
|-----------|--------|---------|
| **PostgreSQL 16** | ✅ Live | `pgvector/pgvector:pg16` via Docker. All 5 users, 6 courses, 7 modules, 13 lessons are in PG. |
| **pgvector** | ✅ Installed | `pgvector.django` in INSTALLED_APPS. `LessonEmbedding` and `CourseEmbedding` models with HNSW indexes already defined. |
| **Celery + Redis** | ✅ Configured | `docker-compose.yml` has `worker` and `beat` services. Broker = `redis://localhost:6379/0`. |
| **REST API** | ✅ DRF | `djangorestframework` + `simplejwt` for authentication. |
| **Sentence Transformers** | ✅ Installed | `all-MiniLM-L6-v2` (384-dim) configured in `.env`. |

### 2.2 What Needs Attention ⚠️

| Issue | Severity | Details |
|-------|----------|---------|
| **Legacy `db.sqlite3` file** | Medium | 250 KB file at project root with 20 empty tables. Leftover from the old Streamlit app. No live data — all records are in PostgreSQL. Causes confusion. |
| **`scripts/migrate_sqlite_to_postgres.py`** | Low | One-time migration script that references SQLite. Job is done — should be archived. |
| **Local filesystem for media** | High | `MEDIA_ROOT = BASE_DIR / 'media'`. All uploads (videos up to 200 MB, PDFs, images) go to local disk. Not scalable for multi-node, not suitable for CDN, not compatible with container restarts. |
| **No caching layer** | High | No `CACHES` config in `settings/base.py`. Every page hit queries PG directly. Timeline feed will be very slow at scale. |
| **No WebSocket/Channels** | Medium | `ASGI_APPLICATION` is declared but `django-channels` is not installed. Timeline updates require polling instead of push. |
| **`TimelinePost.media_paths`** | Medium | Uses `JSONField` to store file paths as strings. No structured metadata (mime type, dimensions, file size, thumbnails). |
| **No media cataloging** | High | Files are scattered across `media/` subdirectories with no database-level asset registry. Cannot query "all videos uploaded this month" or build a DAM (Digital Asset Manager). |

### 2.3 Current File Upload Points (12 FileField/ImageField)

| Model | Field | Upload Path | Max Size |
|-------|-------|-------------|----------|
| `Course` | `thumbnail` | `courses/thumbnails/` | 1 MB |
| `Lesson` | `video_file_path` | `lessons/videos/` | 200 MB |
| `Lesson` | `pdf_file_path` | `lessons/pdfs/` | 200 MB |
| `Institute` | `cover_image` | `institutes/covers/` | — |
| `Institute` | `profile_pic` | `institutes/profiles/` | — |
| `UserProfile` | `cover_image` | `profiles/covers/` | — |
| `UserProfile` | `profile_pic` | `profiles/photos/` | — |
| `BrandingSettings` | `brand_left_image` | `branding/` | — |
| `BrandingSettings` | `brand_right_image` | `branding/` | — |
| `BrandingSettings` | `footer_icon` | `branding/` | — |
| `MailAttachment` | `file` | `mailbox/attachments/` | — |
| `RestrictedEnrollmentRequest` | `supporting_document` | `enrollment_supporting_docs/` | — |

### 2.4 Current Docker Stack

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   web:8000   │  │  worker      │  │  beat         │
│  (Django)    │  │  (Celery)    │  │  (Celery)     │
└──────┬───────┘  └──────┬───────┘  └──────┬────────┘
       │                 │                 │
       ├─────────────────┤─────────────────┤
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐
│ db:5432      │  │ redis:6379   │
│ (PG+pgvector)│  │ (Broker+     │
│              │  │  Results)    │
└──────────────┘  └──────────────┘
```

---

## 3. Phase 1 — SQLite Cleanup & PostgreSQL Hardening

### 3.1 Remove SQLite Artifacts

**Goal**: Eliminate all SQLite references so there is zero ambiguity about which database is live.

| # | Action | File(s) | Details |
|---|--------|---------|---------|
| 1 | **Delete `db.sqlite3`** | `db.sqlite3` | Empty legacy file (0 records). Safe to delete. |
| 2 | **Archive migration script** | `scripts/migrate_sqlite_to_postgres.py` | Move to `scripts/archive/` with a README noting it was a one-time migration completed in May 2026. |
| 3 | **Add `db.sqlite3` to `.gitignore`** | `.gitignore` | Prevent accidental re-creation if Django falls back to SQLite. |
| 4 | **Verify `.env` DATABASE_URL** | `.env` | Currently: `postgres://postgres:ongc1234@127.0.0.1:5432/joy_lms` ✅ No SQLite fallback. |

### 3.2 PostgreSQL Hardening

| # | Action | Details |
|---|--------|---------|
| 1 | **Connection pooling** | Add `django-db-connection-pool` or use PgBouncer sidecar. Current `CONN_MAX_AGE=60` is a start. |
| 2 | **Read replicas** (future) | For analytics dashboards, consider a read replica to offload reporting queries. |
| 3 | **pg_partitioning** for `activity_logs` | This table will grow fastest. Partition by month using `pg_partman`. |
| 4 | **Indexes audit** | Add composite indexes for hot queries: `(learner_id, course_id)` on enrollments, `(author_id, created_at)` on timeline_posts. |
| 5 | **Backup strategy** | Configure `pg_dump` cron via `pg_cron` extension or Celery Beat for daily logical backups. |

### 3.3 Add Redis Caching Layer

Add to `settings/base.py`:

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

**Cache targets**: Timeline feed (per-user, TTL 30s), Course catalog (TTL 5min), Leaderboard (TTL 1min), User permissions/RBAC (TTL 10min).

---

## 4. Phase 2 — MinIO Object Storage Integration

### 4.1 Why MinIO?

| Requirement | MinIO Advantage |
|-------------|-----------------|
| S3-compatible API | Drop-in replacement for AWS S3. All Django S3 libraries work natively. |
| On-premise / air-gapped | ONGC intranet deployment — no cloud dependency. |
| Scalable to petabytes | Erasure coding, distributed mode across nodes. |
| RAG pipeline ready | Objects can be directly accessed by ingestion workers. |
| Versioning & lifecycle | Object versioning for compliance; lifecycle policies for auto-archival. |

### 4.2 MinIO Bucket Design

```
minio/
├── diya-media/                    # Primary media bucket
│   ├── courses/thumbnails/        # Course thumbnail images
│   ├── lessons/videos/            # Lesson video files
│   ├── lessons/pdfs/              # Lesson PDF worksheets
│   ├── timeline/images/           # DXus timeline image uploads
│   ├── timeline/videos/           # DXus timeline video uploads
│   ├── profiles/photos/           # User profile pictures
│   ├── profiles/covers/           # User cover images
│   ├── institutes/                # Institute branding assets
│   ├── certificates/              # Generated certificate PDFs
│   ├── mailbox/attachments/       # Help desk attachments
│   └── branding/                  # Platform branding assets
│
├── diya-processed/                # Processed/derived assets
│   ├── thumbnails/                # Auto-generated video thumbnails
│   ├── transcodes/                # Lower-resolution video variants
│   └── previews/                  # PDF preview images
│
└── diya-rag-staging/              # RAG pipeline staging bucket
    ├── pending/                   # Newly uploaded docs awaiting ingestion
    ├── chunked/                   # Text chunks ready for embedding
    └── indexed/                   # Successfully indexed documents
```

### 4.3 Django Integration

**Dependencies to add:**
```
django-storages[s3]==1.14.4
boto3==1.38.0
```

**Settings:**
```python
# settings/base.py — MinIO / S3 Storage
STORAGES = {
    'default': {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

AWS_S3_ENDPOINT_URL = env('MINIO_ENDPOINT', default='http://localhost:9000')
AWS_ACCESS_KEY_ID = env('MINIO_ACCESS_KEY', default='minioadmin')
AWS_SECRET_ACCESS_KEY = env('MINIO_SECRET_KEY', default='minioadmin')
AWS_STORAGE_BUCKET_NAME = env('MINIO_BUCKET', default='diya-media')
AWS_S3_REGION_NAME = 'us-east-1'
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = True
AWS_QUERYSTRING_EXPIRE = 3600  # 1-hour signed URLs
```

### 4.4 New Model: `MediaAsset` (Digital Asset Registry)

```python
class MediaAsset(models.Model):
    """Central registry for all binary assets stored in MinIO."""
    ASSET_TYPES = [
        ('image', 'Image'), ('video', 'Video'), ('pdf', 'PDF'),
        ('document', 'Document'), ('certificate', 'Certificate'),
    ]
    STATUS_CHOICES = [
        ('uploading', 'Uploading'), ('processing', 'Processing'),
        ('ready', 'Ready'), ('failed', 'Failed'), ('archived', 'Archived'),
    ]

    asset_id        = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    asset_type      = models.CharField(max_length=20, choices=ASSET_TYPES)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploading')

    # Storage
    bucket          = models.CharField(max_length=100, default='diya-media')
    object_key      = models.CharField(max_length=500, unique=True)  # Full MinIO path
    original_filename = models.CharField(max_length=255)
    mime_type       = models.CharField(max_length=100)
    file_size_bytes = models.BigIntegerField()

    # Metadata
    width           = models.IntegerField(null=True, blank=True)  # For images/video
    height          = models.IntegerField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)   # For video/audio
    checksum_sha256 = models.CharField(max_length=64)

    # Derived assets
    thumbnail_key   = models.CharField(max_length=500, blank=True)
    preview_key     = models.CharField(max_length=500, blank=True)

    # Ownership
    uploaded_by     = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    
    # RAG pipeline tracking
    is_rag_indexed  = models.BooleanField(default=False)
    rag_indexed_at  = models.DateTimeField(null=True, blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'media_assets'
        indexes = [
            models.Index(fields=['asset_type', 'status']),
            models.Index(fields=['uploaded_by', '-created_at']),
            models.Index(fields=['is_rag_indexed']),
        ]
```

### 4.5 Migration Strategy for Existing Files

```
Step 1: Deploy MinIO container alongside existing stack
Step 2: Run bulk migration Celery task:
        - Scan all MEDIA_ROOT subdirectories
        - Upload each file to MinIO with correct object_key
        - Create MediaAsset record with metadata
        - Update model FileField/ImageField to point to MinIO URL
Step 3: Verify all files accessible via MinIO
Step 4: Remove local media/ directory
Step 5: Update MEDIA_URL to MinIO endpoint
```

### 4.6 Docker-Compose Addition

```yaml
  minio:
    image: minio/minio:latest
    container_name: joy_lms_minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"   # S3 API
      - "9001:9001"   # Web Console
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  createbuckets:
    image: minio/mc:latest
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      mc alias set myminio http://minio:9000 minioadmin minioadmin123;
      mc mb myminio/diya-media --ignore-existing;
      mc mb myminio/diya-processed --ignore-existing;
      mc mb myminio/diya-rag-staging --ignore-existing;
      mc anonymous set download myminio/diya-media;
      "

volumes:
  minio_data:
```

---

## 5. Phase 3 — DXus Community Timeline (Near Real-Time)

### 5.1 Architecture Pattern: Fan-Out on Write + Redis Cache

For social network timelines, the industry-proven approach (Twitter, Instagram) is **Fan-Out on Write**:

```
User creates post
       │
       ▼
┌─────────────────┐
│ Django View      │ ← Synchronous: save to PG + upload media to MinIO
│ (POST /timeline) │
└────────┬────────┘
         │
         ▼ (async Celery task)
┌─────────────────────────────────────┐
│ fan_out_post_to_followers()         │
│                                     │
│  1. Get all followers of author     │
│  2. For each follower:              │
│     → LPUSH to Redis list           │
│       key: timeline:{user_id}       │
│     → Trim list to 500 items        │
│  3. Send WebSocket notification     │
│     to online followers             │
│  4. Create Notification records     │
└─────────────────────────────────────┘
```

### 5.2 Enhanced Timeline Models

```python
# social/models.py — Enhanced

class TimelinePost(models.Model):
    POST_TYPES = [
        ('text', 'Text'), ('image', 'Image'), ('video', 'Video'),
        ('achievement', 'Achievement'), ('milestone', 'Milestone'),
        ('poll', 'Poll'), ('article', 'Article'),
    ]
    
    author          = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    post_type       = models.CharField(max_length=20, choices=POST_TYPES)
    text_content    = models.TextField(blank=True)
    visibility      = models.CharField(max_length=20, default='institute')
    
    # NEW: Link to MediaAsset registry instead of raw JSON
    media_assets    = models.ManyToManyField('MediaAsset', blank=True, related_name='timeline_posts')
    
    # NEW: Denormalized counters for fast reads (updated via signals/Celery)
    reaction_count_cached  = models.IntegerField(default=0)
    comment_count_cached   = models.IntegerField(default=0)
    share_count_cached     = models.IntegerField(default=0)
    
    # NEW: Content moderation
    is_flagged      = models.BooleanField(default=False)
    moderated_by    = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL)
    moderated_at    = models.DateTimeField(null=True, blank=True)
    
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'timeline_posts'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['visibility', '-created_at']),
        ]


class UserFollow(models.Model):
    """Who follows whom — drives timeline fan-out."""
    follower    = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='following')
    following   = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='followers')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_follows'
        unique_together = ('follower', 'following')
        indexes = [
            models.Index(fields=['following']),  # "Who follows this user?" (for fan-out)
        ]
```

### 5.3 Redis Feed Cache Structure

```
Key Pattern              │ Type  │ TTL      │ Purpose
─────────────────────────┼───────┼──────────┼──────────────────────────
timeline:{user_id}       │ LIST  │ 24h      │ User's personalised feed (post IDs)
post:{post_id}           │ HASH  │ 1h       │ Serialised post data (avoids PG hit)
trending:global          │ ZSET  │ 5min     │ Trending posts by engagement score
online:users             │ SET   │ —        │ Currently connected WebSocket users
notif:{user_id}:unread   │ INT   │ —        │ Unread notification counter
```

### 5.4 WebSocket Layer (Django Channels)

**New dependencies:**
```
channels==4.2.0
channels-redis==4.2.1
daphne==4.1.0
```

**Routing:**
```python
# joy_lms/routing.py
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from apps.social.consumers import TimelineConsumer, NotificationConsumer

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter([
            path('ws/timeline/', TimelineConsumer.as_asgi()),
            path('ws/notifications/', NotificationConsumer.as_asgi()),
        ])
    ),
})
```

### 5.5 Video Upload Pipeline (via Celery)

```
User uploads video
       │
       ▼
┌───────────────────┐
│ Direct upload to  │  ← Presigned URL (MinIO)
│ MinIO via browser │     Bypasses Django entirely
└────────┬──────────┘
         │ (webhook / callback)
         ▼
┌───────────────────────────────────┐
│ Celery: process_video_upload()    │
│                                   │
│  1. Extract metadata (ffprobe)    │
│  2. Generate thumbnail at 5s      │
│  3. Transcode to 720p if >1080p   │
│  4. Create MediaAsset record      │
│  5. Update TimelinePost           │
│  6. Trigger fan-out               │
└───────────────────────────────────┘
```

---

## 6. Phase 4 — AI Layer & RAG Pipeline Readiness

### 6.1 Current AI Foundation (Already Built)

```python
# apps/ai_features/models.py (EXISTING)
class LessonEmbedding(models.Model):
    lesson    = models.OneToOneField('courses.Lesson', ...)
    embedding = VectorField(dimensions=384)          # all-MiniLM-L6-v2
    content_hash = models.CharField(max_length=64)   # Skip re-embed if unchanged
    
    class Meta:
        indexes = [HnswIndex(name='lesson_emb_hnsw', fields=['embedding'],
                             m=16, ef_construction=64,
                             opclasses=['vector_cosine_ops'])]
```

### 6.2 RAG Ingestion Pipeline Architecture

```
                    ┌─────────────────────────┐
                    │   Content Sources        │
                    │ ┌────┐ ┌────┐ ┌───────┐ │
                    │ │PDF │ │Video│ │Lessons│ │
                    │ └──┬─┘ └──┬─┘ └───┬───┘ │
                    └────┼──────┼───────┼─────┘
                         │      │       │
                         ▼      ▼       ▼
               ┌─────────────────────────────┐
               │  MinIO: diya-rag-staging/    │
               │  bucket: pending/            │
               └──────────┬──────────────────┘
                          │
                          ▼ (Celery Beat: every 5 min)
               ┌─────────────────────────────┐
               │  Stage 1: EXTRACT            │
               │  - PDF → text (PyMuPDF)      │
               │  - Video → transcript (Whisper)│
               │  - Lesson → content_text     │
               └──────────┬──────────────────┘
                          │
                          ▼
               ┌─────────────────────────────┐
               │  Stage 2: CHUNK              │
               │  - Split into 512-token      │
               │    overlapping chunks         │
               │  - Preserve metadata:        │
               │    source_type, course_id,    │
               │    module_id, lesson_id       │
               └──────────┬──────────────────┘
                          │
                          ▼
               ┌─────────────────────────────┐
               │  Stage 3: EMBED              │
               │  - sentence-transformers     │
               │    all-MiniLM-L6-v2 (384d)   │
               │  - Batch processing          │
               └──────────┬──────────────────┘
                          │
                          ▼
               ┌─────────────────────────────┐
               │  Stage 4: STORE              │
               │  - PostgreSQL + pgvector     │
               │  - HNSW index for ANN search │
               │  - Update MediaAsset:        │
               │    is_rag_indexed = True      │
               └─────────────────────────────┘
```

### 6.3 New Models for RAG

```python
# apps/ai_features/models.py — NEW additions

class ContentChunk(models.Model):
    """Individual text chunk for RAG retrieval."""
    SOURCE_TYPES = [
        ('lesson_text', 'Lesson Text Content'),
        ('lesson_pdf', 'Lesson PDF'),
        ('lesson_video_transcript', 'Video Transcript'),
        ('timeline_post', 'Timeline Post'),
        ('course_description', 'Course Description'),
    ]

    chunk_id        = models.UUIDField(default=uuid.uuid4, unique=True)
    source_type     = models.CharField(max_length=30, choices=SOURCE_TYPES)
    content_text    = models.TextField()
    embedding       = VectorField(dimensions=384)
    
    # Source references (nullable — depends on source_type)
    course          = models.ForeignKey('courses.Course', null=True, blank=True, on_delete=models.CASCADE)
    module          = models.ForeignKey('courses.Module', null=True, blank=True, on_delete=models.CASCADE)
    lesson          = models.ForeignKey('courses.Lesson', null=True, blank=True, on_delete=models.CASCADE)
    media_asset     = models.ForeignKey('MediaAsset', null=True, blank=True, on_delete=models.CASCADE)
    
    # Chunk metadata
    chunk_index     = models.IntegerField(default=0)  # Position within source
    token_count     = models.IntegerField(default=0)
    content_hash    = models.CharField(max_length=64)  # For deduplication
    
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'content_chunks'
        indexes = [
            HnswIndex(
                name='chunk_emb_hnsw',
                fields=['embedding'],
                m=16, ef_construction=64,
                opclasses=['vector_cosine_ops']
            ),
            models.Index(fields=['source_type', 'course']),
            models.Index(fields=['content_hash']),
        ]


class RAGQueryLog(models.Model):
    """Audit log for AI search queries — used to improve relevance."""
    user            = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    query_text      = models.TextField()
    query_embedding = VectorField(dimensions=384)
    results_count   = models.IntegerField(default=0)
    top_chunk_ids   = models.JSONField(default=list)
    relevance_score = models.FloatField(null=True, blank=True)  # User feedback
    latency_ms      = models.IntegerField(default=0)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rag_query_logs'
        ordering = ['-created_at']
```

### 6.4 Semantic Search API

```python
# apps/ai_features/views.py — NEW endpoint

@api_view(['POST'])
@permission_required('ai.search')
def semantic_search(request):
    """
    POST /api/v1/ai/search/
    Body: {"query": "How to interpret well log data?", "top_k": 10, "source_filter": "lesson_pdf"}
    
    Returns ranked chunks with source metadata.
    Uses pgvector cosine similarity: 1 - (embedding <=> query_embedding)
    """
    query = request.data.get('query', '')
    top_k = min(request.data.get('top_k', 10), 50)
    
    # Embed query
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(settings.EMBEDDING_MODEL)
    query_vec = model.encode(query).tolist()
    
    # Vector search via pgvector
    chunks = ContentChunk.objects.order_by(
        CosineDistance('embedding', query_vec)
    )[:top_k]
    
    return Response(ChunkSerializer(chunks, many=True).data)
```

---

## 7. Revised System Architecture Diagram

```
                        ┌──────────────────────────────┐
                        │       DIYA LMS Clients        │
                        │  (Browser / Mobile / API)     │
                        └──────────┬───────────────────┘
                                   │
                          ┌────────┴────────┐
                          │   Nginx / LB     │
                          │  (Reverse Proxy) │
                          └────────┬────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
           ┌──────────────┐ ┌──────────┐ ┌──────────────┐
           │ Django/ASGI  │ │ Daphne   │ │ Celery       │
           │ (HTTP API)   │ │ (WS)     │ │ Workers (x3) │
           └──────┬───────┘ └────┬─────┘ └──────┬───────┘
                  │              │              │
        ┌─────────┼──────────────┼──────────────┼─────────┐
        │         │              │              │         │
        ▼         ▼              ▼              ▼         ▼
 ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────────┐
 │PostgreSQL │ │  Redis     │ │  MinIO    │ │ Sentence         │
 │ 16        │ │  7         │ │  (S3)     │ │ Transformers     │
 │ + pgvector│ │ • Cache    │ │ • Media   │ │ (Embedding)      │
 │ • Data    │ │ • Broker   │ │ • Assets  │ │                  │
 │ • Vectors │ │ • Sessions │ │ • RAG     │ │                  │
 │ • Chunks  │ │ • Feeds    │ │   Staging │ │                  │
 └───────────┘ └───────────┘ └───────────┘ └──────────────────┘
```

---

## 8. Database Schema Enhancements

### 8.1 New Tables Summary

| Table | App | Purpose |
|-------|-----|---------|
| `media_assets` | `courses` or new `media` app | Central asset registry for MinIO objects |
| `content_chunks` | `ai_features` | RAG text chunks with pgvector embeddings |
| `rag_query_logs` | `ai_features` | AI search audit trail |
| `user_follows` | `social` | Follow graph for timeline fan-out |

### 8.2 Indexes to Add to Existing Tables

```sql
-- Timeline performance
CREATE INDEX idx_timeline_posts_author_created ON timeline_posts (author_id, created_at DESC);
CREATE INDEX idx_timeline_posts_visibility_created ON timeline_posts (visibility, created_at DESC);

-- Course catalog search
CREATE INDEX idx_courses_status_created ON courses (status, created_at DESC);

-- Activity logs partitioning candidate
-- ALTER TABLE activity_logs SET (autovacuum_vacuum_cost_delay = 0);

-- Enrollment lookups
CREATE INDEX idx_enrollments_learner_progress ON enrollments (learner_id, progress_percentage);
```

---

## 9. Infrastructure & DevOps

### 9.1 Updated `docker-compose.yml`

The final production docker-compose will include these services:

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| `db` | `pgvector/pgvector:pg16` | 5432 | Primary database |
| `redis` | `redis:7-alpine` | 6379 | Cache + broker + sessions + feeds |
| `minio` | `minio/minio:latest` | 9000, 9001 | Object storage |
| `web` | Custom Dockerfile | 8000 | Django HTTP |
| `daphne` | Custom Dockerfile | 8001 | WebSocket server |
| `worker` | Custom Dockerfile | — | Celery workers (x3 concurrency) |
| `beat` | Custom Dockerfile | — | Celery Beat scheduler |

### 9.2 New Dependencies to Add

```
# requirements/base.txt — additions
django-storages[s3]==1.14.4     # MinIO/S3 integration
boto3==1.38.0                    # AWS SDK for S3 API
django-redis==5.4.0             # Redis cache backend
channels==4.2.0                  # WebSocket support
channels-redis==4.2.1            # Channel layer backend
daphne==4.1.0                    # ASGI server for WebSockets
ffmpeg-python==0.2.0             # Video processing
```

### 9.3 Environment Variables to Add

```env
# MinIO
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=diya-media

# Channels
CHANNEL_LAYERS_BACKEND=channels_redis.core.RedisChannelLayer
CHANNEL_LAYERS_HOST=redis://localhost:6379/2
```

---

## 10. Risk Assessment & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Data loss during MinIO migration | Critical | Low | Run migration in parallel — keep local files until 100% verified. Checksum validation for every file. |
| PostgreSQL performance under load | High | Medium | Add pgBouncer, optimize indexes, implement Redis caching for hot paths. |
| WebSocket connection limits | Medium | Medium | Use Redis channel layer with horizontal scaling. Set connection limits per user. |
| Large video uploads timing out | High | High | Use MinIO presigned URLs for direct browser-to-MinIO uploads. Bypass Django entirely. |
| RAG embedding compute cost | Medium | Low | Batch processing via Celery. Use `content_hash` to skip re-embedding unchanged content. |
| MinIO single-point-of-failure | High | Medium | Deploy MinIO in distributed mode (4+ nodes) for production. Daily backup to NFS. |

---

## 11. Implementation Roadmap

### Sprint Plan

| Sprint | Duration | Phase | Deliverables |
|--------|----------|-------|--------------|
| **S1** | 1 week | Phase 1 | SQLite cleanup, `.gitignore`, Redis caching, PG index audit |
| **S2** | 2 weeks | Phase 2 | MinIO deployment, `django-storages` config, `MediaAsset` model, bulk file migration |
| **S3** | 2 weeks | Phase 2 | Update all 12 FileField/ImageField to use MinIO, presigned upload for videos |
| **S4** | 2 weeks | Phase 3 | `UserFollow` model, timeline fan-out, Redis feed cache, denormalized counters |
| **S5** | 1 week | Phase 3 | Django Channels, WebSocket consumers, real-time notifications |
| **S6** | 2 weeks | Phase 4 | `ContentChunk` model, RAG ingestion pipeline, PDF/video text extraction |
| **S7** | 1 week | Phase 4 | Semantic search API endpoint, search UI integration |
| **S8** | 1 week | All | Integration testing, load testing, documentation |

**Total estimated duration: ~12 weeks**

### Priority Matrix

```
                    HIGH IMPACT
                        │
         Phase 1        │        Phase 2
      (SQLite cleanup   │     (MinIO storage)
       + Redis cache)   │
                        │
  LOW EFFORT ───────────┼──────────── HIGH EFFORT
                        │
         Phase 3        │        Phase 4
      (Timeline WS)    │     (RAG Pipeline)
                        │
                    LOW IMPACT
```

> **Recommendation**: Execute Phase 1 immediately (low effort, high impact), then Phase 2 (foundational for all future work), then Phase 3 and 4 in parallel.

---

## Appendix A: Files to Modify

| File | Changes |
|------|---------|
| `settings/base.py` | Add CACHES, STORAGES, CHANNEL_LAYERS, MinIO config |
| `docker-compose.yml` | Add minio, daphne services |
| `requirements/base.txt` | Add django-storages, boto3, django-redis, channels |
| `.env` | Add MINIO_* variables |
| `.gitignore` | Add `db.sqlite3` |
| `apps/social/models.py` | Enhance TimelinePost, add UserFollow |
| `apps/ai_features/models.py` | Add ContentChunk, RAGQueryLog |
| `apps/courses/models.py` or new `apps/media/` | Add MediaAsset |
| `joy_lms/routing.py` | New file — WebSocket routing |
| `apps/social/consumers.py` | New file — WebSocket consumers |

---

*End of Document*
