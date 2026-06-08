# Add EK Resources Explorer and Metadata Features

This plan outlines the steps to add unique IDs to Modules and Lessons, introduce keyword tagging for semantic search, and build an "EK Resources" explorer tab inside the Course Builder.

## Proposed Changes

### 1. Database Model Updates (`apps/courses/models.py`)

We will update the core content models to support unique IDs, keywords, and timestamp tracking.

#### `Course`
- `[NEW FIELD]` **keywords**: A `TextField(blank=True)` for storing comma-separated tags or semantic descriptors.

#### `Module`
- `[NEW FIELD]` **unique_id**: A `CharField(max_length=50, unique=True)`. We will override the `save()` method to auto-generate an ID in the format `MOD-XXXXXX` for new and existing modules.
- `[NEW FIELD]` **keywords**: A `TextField(blank=True)` for tagging the module.
- `[NEW FIELD]` **updated_at**: A `DateTimeField(auto_now=True)` to track when a module was last changed. (It already has `created_at`).

#### `Lesson`
- `[NEW FIELD]` **unique_id**: A `CharField(max_length=50, unique=True)`. We will override the `save()` method to auto-generate an ID in the format `LES-XXXXXX`.
- `[NEW FIELD]` **keywords**: A `TextField(blank=True)` for tagging the lesson.
- `[NEW FIELD]` **updated_at**: A `DateTimeField(auto_now=True)` to track when a lesson was last changed.

> [!IMPORTANT]  
> After adding these fields, we will create and run a database migration. Existing rows will automatically be assigned unique IDs upon saving.

### 2. Backend Views (`apps/dashboard/views.py`)

#### `course_edit` View
- We will fetch all `Published` courses in the platform alongside their associated modules and lessons to serve as the "EK Resources" catalog.
- We will pass this data (e.g. `ek_courses = Course.objects.filter(status='Published').prefetch_related('modules__lessons')`) to the template context.
- We will also add form handling so users can update the `keywords` for their courses, modules, and lessons.

### 3. Frontend UI (`templates/dashboard/courses/edit.html`)

#### Forms
- Add a "Keywords/Tags" input field to the Course Settings tab, the Add/Edit Module forms, and the Add/Edit Lesson forms.
- Ensure the Course `unique_id`, Module `unique_id`, and Lesson `unique_id` are displayed prominently in the Course Builder.

#### The "EK Resources" Tab
- `[NEW]` Add an "EK Resources" button to the main navigation tabs, positioned right after "Functional Test View".
- `[NEW]` Build the EK Resources panel. It will feature:
  - **A Search/Filter Bar:** To quickly search by course title, module ID, lesson ID, or keywords using Javascript.
  - **Hierarchical Drill-down Dashboard:** A tree-like explorer rendering `ek_courses`. 
    - Clicking a Course expands its Modules.
    - Clicking a Module expands its Lessons.
    - Each item will clearly show its Unique ID, Keywords, and basic metadata (duration, date, type).

## Verification Plan

### Automated Tests
- Run `python manage.py makemigrations` and `python manage.py migrate` to ensure the schema updates without breaking existing data.
- Run a Python script snippet to loop through all existing Modules and Lessons and call `.save()` to populate their unique IDs automatically.

### Manual Verification
- Open the Course Builder and confirm the new Keywords inputs save correctly.
- Open the EK Resources tab and verify the explorer displays the hierarchy properly and the filtering correctly searches the new keyword fields and Unique IDs.

## Open Questions

None at this time. Please approve this plan so we can begin execution!
