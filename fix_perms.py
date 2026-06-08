import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joy_lms.settings.base')
django.setup()

from apps.accounts.models import RolePermission

roles_to_update = ['admin', 'institute_admin', 'course_coordinator', 'teacher']
features = ['tab.courses.edit_settings', 'tab.courses.edit_builder', 'tab.courses.edit_preview']

for role in roles_to_update:
    for feature in features:
        RolePermission.objects.update_or_create(
            role=role,
            feature=feature,
            defaults={'is_allowed': True}
        )

print("Permissions updated successfully.")
