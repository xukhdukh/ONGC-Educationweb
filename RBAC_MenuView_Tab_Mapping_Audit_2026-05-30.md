# RBAC Menu View Tab Mapping Audit

Date: 2026-05-30
Scope: Horizontal tabs in dashboard templates vs mappings shown in Dashboard -> RBAC Settings -> Menu View.
Reference URL: http://127.0.0.1:8000/dashboard/rbac/

## 1) Current Menu View subgroup mappings in code

Source of mapping definitions:
- apps/dashboard/views.py (rbac_matrix -> MENU_FEATURES_BASE)

Currently mapped subgroups:
- menu.users
  - tab.users.administration -> User Administration
  - tab.users.directory -> User Directory
- menu.institutes
  - tab.institutes.list -> Institutes List
  - tab.institutes.mapusers -> Map Users
  - tab.institutes.profiles -> Institute Profiles
- menu.rbac
  - tab.rbac.permissions -> Permissions Matrix
  - tab.rbac.menuview -> Menu View
  - tab.rbac.menutoggle -> Menu Vertical Toggle
  - tab.rbac.scoping -> Scoping Controls
- menu.analytics
  - tab.analytics.overview -> Overview
  - tab.analytics.performance -> System Performance
  - tab.analytics.login -> Login Monitor
  - tab.analytics.activity -> Activity Monitor

No subgroup tabs currently declared for:
- menu.dashboard
- menu.my_courses
- menu.notes
- menu.timeline
- menu.leaderboard
- menu.grading
- menu.timeline_mod
- menu.profile

## 2) Horizontal tabs found in templates (inventory)

### A) Dashboard (menu.dashboard)
- templates/dashboard/home.html
  - Overview
  - Browser
Status in Menu View: NOT MAPPED

### B) My Courses (menu.my_courses)
- templates/dashboard/courses/list.html
  - My Courses
  - Explore Courses
- templates/dashboard/courses/edit.html
  - Settings
  - Builder Mode
  - Functional Test View
Status in Menu View: NOT MAPPED

### C) Manage Users (menu.users)
- templates/dashboard/users/management.html
  - User Administration
  - User Directory
Status in Menu View: MAPPED

Additional tabs under user profile drilldown:
- templates/dashboard/users/profile_detail.html
  - About
  - Timeline
  - Courses
  - Analytics
  - User Hierarchy
  - Edit Profile
Status in Menu View: NOT MAPPED

### D) Institutes (menu.institutes)
- templates/dashboard/institutes.html
  - Institutes List
  - Map Users
  - Institute Profiles
Status in Menu View: MAPPED

Additional tabs under institute detail page:
- templates/dashboard/institutes/profile.html
  - Overview
  - Dashboard
Status in Menu View: NOT MAPPED

### E) RBAC Settings (menu.rbac)
- templates/dashboard/rbac_matrix.html
  - Permission Matrix
  - Menu View
  - Menu Vertical Toggle
  - Scoping Controls
Status in Menu View: MAPPED

### F) Analytics (menu.analytics)
- templates/dashboard/analytics/_tabs.html
  - Overview
  - System Performance
  - Login Monitor
  - Activity Monitor
Status in Menu View: MAPPED

### G) My Profile (menu.profile)
- templates/dashboard/profile.html
  - About
  - My Hierarchy
  - Edit Profile
Status in Menu View: NOT MAPPED

## 3) Gap summary (unmapped horizontal tabs)

Unmapped tab groups by vertical menu:
- menu.dashboard: 2 tabs
- menu.my_courses: 5 tabs (2 list tabs + 3 course-edit tabs)
- menu.users: 6 drilldown/profile tabs
- menu.institutes: 2 institute-profile tabs
- menu.profile: 3 tabs

Total unmapped horizontal tabs found: 18

## 4) Recommended subgroup keys to add to MENU_FEATURES_BASE

### menu.dashboard
- tab.dashboard.overview -> Overview
- tab.dashboard.browser -> Browser

### menu.my_courses
- tab.courses.list.my -> My Courses
- tab.courses.list.explore -> Explore Courses
- tab.courses.edit.settings -> Settings
- tab.courses.edit.builder -> Builder Mode
- tab.courses.edit.preview -> Functional Test View

### menu.users (add to existing)
- tab.users.profile.about -> About
- tab.users.profile.timeline -> Timeline
- tab.users.profile.courses -> Courses
- tab.users.profile.analytics -> Analytics
- tab.users.profile.hierarchy -> User Hierarchy
- tab.users.profile.edit -> Edit Profile

### menu.institutes (add to existing)
- tab.institutes.profile.overview -> Institute Overview
- tab.institutes.profile.dashboard -> Institute Dashboard

### menu.profile
- tab.profile.about -> About
- tab.profile.hierarchy -> My Hierarchy
- tab.profile.edit -> Edit Profile

## 5) Notes

- This audit is based on implemented tab UI controls in templates and current RBAC Menu View feature list.
- Notes, Timeline, Leaderboard, Homework Grading, and Timeline Moderation currently show no horizontal tab controls in their reviewed templates.
- If desired, the next step is implementing these subgroup keys in:
  - apps/dashboard/views.py (MENU_FEATURES_BASE)
  - permission checks where tab-level permissions are enforced in views/templates/JS.
