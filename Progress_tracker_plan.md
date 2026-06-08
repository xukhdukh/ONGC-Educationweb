# Progress Tracker Plan

Date: 2026-05-31
Workspace: D:/A_LMS
Primary app reviewed: A_LMS_upgrade (Django + DRF + template UI)
Secondary app reviewed: ajoy-academy (Streamlit + SQLAlchemy) for historical/reference patterns

## 1) Executive Summary

The current learner progress model is clear and mostly practical:
- Lesson-level state is stored in lesson_progresses.
- Course-level progress is stored in enrollments.progress_percentage.
- Progress is completion-count based (completed lessons / total lessons), with time tracking as a parallel metric.

However, there are reliability and product-design gaps that can produce inaccurate progress and weak analytics quality. The most critical issue is API path mismatch in the main course player template, which can prevent progress writes from firing. In addition, tracker events are not yet normalized as immutable events, and completion policy is not strongly configurable per activity type like Moodle.

Recommended direction:
- Keep the current model as a base.
- Add a Moodle-like completion rules engine and event pipeline.
- Separate evidence events from derived progress snapshots.
- Roll out in phases: quick fixes first, then data/model upgrades, then analytics and adaptive learning.

## 2) Current Methodology (As Implemented)

### 2.1 Core data structures

Django app:
- Enrollment tracks learner-course aggregate progress and completion:
  - apps/courses/models.py: Enrollment.progress_percentage, completed_at, certificate_issued
- LessonProgress tracks learner-lesson granular state:
  - apps/courses/models.py: is_completed, watch_duration_seconds, watch_percentage, revise_count, completion_count, last_accessed_at, completed_at, quiz_results
- Completion aggregation:
  - apps/courses/models.py: Enrollment.recalculate_progress()
  - Formula: completed lessons / total lessons * 100

Legacy/parallel Streamlit app (reference):
- Similar schema in ajoy-academy/database/models.py with the same conceptual entities.

### 2.2 Update flow used in Django

Primary API entry:
- apps/courses/views.py: LessonViewSet.progress()
  - GET returns LessonProgress.
  - POST updates watch_duration_seconds and watch_percentage using max() semantics.
  - Auto-complete if watch_percentage >= 90.
  - Manual completion via is_completed true with optional duration check.
  - Awards points/streak tasks on first completion path.

Timer-based tracking:
- apps/courses/views.py: LessonViewSet.ping_time()
  - Adds 10 seconds per call.
- Template timer:
  - templates/dashboard/courses/detail.html
  - setInterval every 10 seconds calls ping_time endpoint.

Course player rendering:
- apps/dashboard/views.py: course_player()
  - Pulls enrollment.progress_percentage.
  - Builds lesson_progresses map for per-lesson status.
  - Computes separate time_progress_percentage from total watched seconds vs estimated course hours.

### 2.3 UX logic in learner player

- Mark Complete button posts completion payload.
- Quiz UI is client-side in the template for lesson.quiz_data.
- Functional Test View exists for manager QA and logs test runs separately (not learner progress).

## 3) Strengths in Current Design

1. Clean two-layer model
- LessonProgress (granular) + Enrollment (aggregate) is the right baseline architecture.

2. Idempotent-ish watch updates
- max() on watch metrics helps avoid regressions from late/out-of-order updates.

3. Multiple engagement dimensions
- Completion status, watch time, revise counts, and completion_count provide richer telemetry than a single boolean.

4. Gamification integration
- Completion can trigger points and streak updates via async tasks.

5. Separate quality/test telemetry
- LessonTestRun for Functional Test View avoids contaminating learner data.

## 4) Critical Gaps and Risks

### 4.1 Endpoint mismatch in template (high severity)

Observed:
- templates/dashboard/courses/detail.html posts to:
  - /api/v1/courses/lessons/{id}/progress/
  - /api/v1/courses/lessons/{id}/ping_time/
  - /api/v1/courses/lessons/{id}/test_run/

But DRF router registers lessons at:
- api/v1/urls.py -> router.register('lessons', LessonViewSet)
- Expected endpoints are /api/v1/lessons/{id}/...

Impact:
- Progress writes/timer/test-run calls can fail (404), causing missing or stale learner tracking.

### 4.2 Completion policy inconsistency

- Auto completion uses watch_percentage >= 90.
- Manual completion enforces duration_minutes only in one branch.
- Policy is hardcoded and not activity-specific (video, PDF, quiz, external, text) as in mature LMS systems.

### 4.3 Weak anti-gaming controls for time

- ping_time adds seconds on a fixed timer regardless of visibility, activity, or playback state.
- No explicit server-side cap per session/request cadence.
- Can overstate time-based engagement.

### 4.4 Counters can inflate

- revise_count increments on every progress POST, including machine-generated update bursts.
- completion_count may increment on repeated mark-complete actions.
- Useful for engagement analysis, but should be event-derived to avoid ambiguous semantics.

### 4.5 Mixed tracking stacks

- static/js/progress_tracker.js uses bearer tokens/localStorage style API flow.
- Main template flow appears session/cookie based and uses inline scripts.
- This split creates drift risk and duplicate/unused tracking paths.

### 4.6 Quiz evidence not consistently centralized

- There is an assessments API (QuizAttempt model/viewset), but lesson quiz flow in template is mostly client-driven.
- Progress completion and assessment quality signals are not unified under one completion policy.

### 4.7 Certificate lifecycle not tightly coupled to completion

- Enrollment completion and certificate issuance are loosely connected.
- certificate_issued flag exists, but auto-issuance policy and audit trail are not strongly enforced in one workflow.

### 4.8 Testing coverage gap

- No automated tests found for progress tracking behavior in app modules.
- Risk of regressions in core learner outcomes.

## 5) Target Model (Moodle-style, adapted)

Adopt a two-layer tracking strategy:

Layer A: Evidence events (append-only)
- Track immutable events:
  - lesson_opened, video_played, video_heartbeat, video_seek,
  - quiz_started, quiz_submitted, quiz_passed,
  - pdf_opened, pdf_scrolled,
  - lesson_marked_complete, lesson_reopened.
- Keep source, timestamp, client_session_id, actor, course/module/lesson context.

Layer B: Derived state snapshots
- Derive LessonProgress and Enrollment from events via deterministic jobs/services.
- Keep snapshots query-fast for dashboards.
- Rebuildable if rules change (major Moodle advantage).

### 5.1 Completion Rules Engine

For each lesson type, configurable completion rules:
- Video:
  - watch_percentage >= X and watch_seconds >= Y and min_unique_heartbeats >= N.
- PDF:
  - scroll depth >= X and dwell_time >= Y.
- Quiz:
  - pass score >= threshold and attempts <= max attempts.
- Text/external:
  - dwell time and explicit acknowledgement/marker.

Course completion:
- Weighted by mandatory activities (not only lesson count).
- Optional items may contribute bonus progress but not gate completion.

### 5.2 Tracking quality controls

- Server validates heartbeat intervals and caps per-minute accrual.
- Ignore progress events when tab hidden/inactive for long periods.
- Detect abnormal seek patterns and require effective watch time.

### 5.3 Analytics model

Add explicit metrics beyond percent complete:
- pace index (actual vs expected cadence)
- consistency index (days active per week)
- mastery trend (quiz outcomes over time)
- at-risk flag (low pace + low mastery + long inactivity)

### 5.4 Learning path progression

Moodle-like gating:
- prerequisite lessons/modules
- minimum score to unlock next module
- remediation loop for failed assessments
- due windows and soft/hard deadlines

## 6) Recommended Improvement Plan

## Phase 0 (Immediate fixes: 1-3 days)

1. Fix API route usage in template JS to /api/v1/lessons/{id}/... endpoints.
2. Add server-side logging for failed progress writes and endpoint mismatch telemetry.
3. Add quick smoke tests for progress, ping_time, and completion updates.
4. Add a feature flag to switch old/new progress endpoint usage safely.

Deliverable:
- Stable progress write path with monitored success rate.

## Phase 1 (Policy hardening: 1-2 weeks)

1. Introduce lesson completion_policy JSON per lesson type:
   - min_watch_pct, min_watch_seconds, require_quiz_pass, etc.
2. Move completion decision into a dedicated service module (single source of truth).
3. Normalize counters:
   - revise_count from revisit events,
   - completion_count from completion transitions only.
4. Standardize timezone-safe timestamps and audit fields.

Deliverable:
- Configurable completion rules and predictable state transitions.

## Phase 2 (Event architecture: 2-4 weeks)

1. Add progress_events table (append-only).
2. Emit events from UI/API; keep snapshots in lesson_progresses and enrollments.
3. Build reconciliation job to recompute snapshots from events.
4. Add data quality checks (heartbeat cadence, impossible jumps, duplicate event suppression).

Deliverable:
- Moodle-grade traceability and re-computation capability.

## Phase 3 (Advanced LMS features: 3-6 weeks)

1. Add gradebook-like aggregation:
   - weighted completion + quiz mastery + assignment outcomes.
2. Add at-risk learner signals and instructor intervention queue.
3. Add cohort pacing analytics and pathway bottleneck analysis.
4. Couple certificate issuance to verified completion policy + optional proctoring evidence.

Deliverable:
- Enterprise-ready progress intelligence similar to best LMS platforms.

## 7) Proposed Data Additions

Minimal new tables/fields:

1. progress_events
- id, learner_id, course_id, module_id, lesson_id
- event_type, event_payload (JSON)
- client_session_id, occurred_at, received_at
- source (web/mobile/api), is_validated

2. lesson_completion_rules
- lesson_id (or template by lesson_type)
- policy_json
- version, active_from

3. progress_quality_flags
- learner_id, lesson_id, event_id
- flag_type (suspicious_seek, heartbeat_gap, etc.)
- severity, resolved

## 8) KPI Targets

After Phase 1:
- progress write success rate >= 99.5%
- mismatch/404 progress calls = 0
- completion calculation parity > 99% in reconciliation checks

After Phase 2:
- reproducible progress rebuild from events >= 99.9% match
- time inflation anomalies reduced by >= 70%

After Phase 3:
- +15-25% improvement in on-time course completion for at-risk cohort intervention groups

## 9) Suggested Implementation Order (Practical)

1. Endpoint and smoke-test fixes (now)
2. Completion rules service extraction
3. Event table and emitters
4. Snapshot reconciliation worker
5. Instructor dashboards with at-risk alerts
6. Certificate automation tied to validated completion

## 10) Final Recommendation

Do not replace the current progress system from scratch.
Instead, evolve it incrementally:
- Keep Enrollment and LessonProgress as fast query snapshots.
- Add an event backbone and policy engine.
- Adopt Moodle-style configurable completion and grade logic.

This path minimizes migration risk while giving you robust, auditable, and analytics-ready progress tracking at scale.
