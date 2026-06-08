# RESOLUTION PLAN — Course Progress & Mark Complete Bug

## 1. Root Cause Analysis

I have investigated the codebase based on your screenshot and description of the `/dashboard/learn/3/lesson/15/` issue. There are two distinct root causes that perfectly explain what you are experiencing:

### Issue 1: "Mark Complete" is falsely appearing checked
**Root Cause**: In `templates/dashboard/courses/detail.html`, the button code is hardcoded as:
```html
<button class="btn btn-ghost" onclick="markComplete()">Mark Complete ✅</button>
```
Because the green checkmark emoji (`✅`) is hardcoded unconditionally into the template, it always looks "checked" to the user, even when their progress is 0% and they haven't completed the lesson yet.

### Issue 2: "Course Progress" remains at 0%
**Root Cause**: When a learner actually clicks the "Mark Complete" button, it sends an API request to `apps/courses/views.py` (`LessonViewSet.progress`). 
While the backend correctly marks the specific `LessonProgress` record as `is_completed = True`, it **fails to call the `enroll.recalculate_progress()` function** in the manual completion block. 
*(Note: The recalculation function was only being called during video auto-completion or quiz submission, which is why manual text/PDF lesson completions were leaving the overall course progress stuck at 0%).*

---

## 2. Proposed Resolution Steps

### Step 1: Fix the UI Button (Dynamic Rendering)
Modify `templates/dashboard/courses/detail.html` (lines ~608 and ~697) to check the `lesson_progresses` context dynamically:
- **If completed**: Render the button as a disabled, green success button: `Completed ✅`
- **If not completed**: Render the button normally without the checkmark: `Mark Complete ⚪`

### Step 2: Fix the Backend Progress Recalculation
Modify `apps/courses/views.py` in the `progress()` API action.
Inject the following logic into the manual `is_completed` block so that overall course progress updates immediately:
```python
try:
    enroll = Enrollment.objects.get(learner=request.user, course=lesson.module.course)
    enroll.recalculate_progress()
except Enrollment.DoesNotExist:
    pass
```

### Step 3: Enforce Minimum Duration Transparency
If a learner tries to mark a lesson complete before spending the required time (e.g., 2 minutes for the Intro), the backend already correctly blocks it and returns a 400 error. The frontend flashes a red message, but we will ensure this UX is crystal clear so they understand *why* it can't be completed yet.

---

> **Please review this plan. Once you approve, I will execute the code changes.**
