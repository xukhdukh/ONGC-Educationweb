# Role-Based Access Control (RBAC) Matrix - Current State

This document outlines the existing RBAC implementation across the Joy LMS web application, based on the backend DRF permissions (`accounts/permissions.py`), models, and frontend routing.

## 1. Defined Roles
The system currently implements a hierarchical and functional role model with 5 distinct roles:

- **Admin (`admin`)**: Superuser with full platform access.
- **Institute Admin (`institute_admin`)**: Tenant-level administrator with scoped management capabilities.
- **Teacher (`teacher`)**: Content creator and evaluator (Course builder, homework grading, analytics).
- **Parent (`parent`)**: Observer role (View child progress, timeline, analytics).
- **Child (`child`)**: Primary consumer (Course player, quizzes, homework submission, social feed).

## 2. Permission Classes (Backend)
The backend enforces access using the following DRF Permission Classes:
- `IsSuperAdmin`: Strictly `admin` only.
- `IsAdmin`: `admin` or `institute_admin`.
- `IsTeacher`: Strictly `teacher`.
- `IsParent`: Strictly `parent`.
- `IsChild`: Strictly `child`.
- `IsGuardian`: `teacher` or `parent`.
- `IsGuardianOrAdmin`: `teacher`, `parent`, `admin`, or `institute_admin`.
- `IsOwnerOrAdmin`: Object-level permission ensuring users can only access their own records (or linked child records for guardians), while admins can access all.

## 3. Detailed Access Matrix

| Feature / Module | Super Admin | Institute Admin | Teacher | Parent | Child |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **User Management** |
| List All Users | ✅ | ⚠️ (Institute only) | ❌ | ❌ | ❌ |
| Create/Edit Users | ✅ | ⚠️ (Institute only) | ❌ | ❌ | ❌ |
| Link Guardian to Child | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Institutes** |
| Manage Institutes | ✅ | ⚠️ (Own only) | ❌ | ❌ | ❌ |
| **Courses & Content** |
| Create/Edit Courses | ✅ | ✅ | ✅ | ❌ | ❌ |
| Publish Courses | ✅ | ✅ | ✅ | ❌ | ❌ |
| View Course Catalog | ✅ | ✅ | ✅ | ✅ | ✅ |
| Enroll in Course | ✅ | ✅ | ✅ | ❌ | ✅ |
| Access Course Player | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Assessments** |
| Create Quizzes/HW | ✅ | ✅ | ✅ | ❌ | ❌ |
| Attempt Quiz / Submit HW | ❌ | ❌ | ❌ | ❌ | ✅ |
| Grade Submissions | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Social / Timeline** |
| View Timeline | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create Posts / React / Comment| ✅ | ✅ | ✅ | ❌ | ✅ |
| **Gamification & Rewards** |
| View Leaderboard / Badges | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Analytics & Reporting** |
| Platform Overview | ✅ | ❌ | ❌ | ❌ | ❌ |
| Institute Overview | ✅ | ✅ | ❌ | ❌ | ❌ |
| Child Detailed Analytics | ✅ | ✅ | ✅ (Linked)| ✅ (Linked)| ✅ (Own) |
| **AI Features** |
| AI Semantic Search / Recs | ❌ | ❌ | ❌ | ❌ | ✅ |

*Legend: ✅ Full Access | ⚠️ Partial/Scoped Access | ❌ No Access*

## 4. Proposed Review Areas
*(Space for your modifications and review notes)*
- Are there any overlapping permissions between Teacher and Institute Admin that need splitting?
- Should Parents have more proactive permissions (e.g., enrolling children into specific courses)?
- Do we need an intermediate role (e.g., `content_reviewer` or `moderator`)?
- Should AI Features be exposed to Teachers for course generation or grading assistance?

---
*Please add your modifications or notes below this line, or leave comments on specific matrix cells above.*
