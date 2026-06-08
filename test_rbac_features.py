from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRelation, Institute
from apps.courses.models import Course, Enrollment
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
import json

class FullFunctionalityTests(TestCase):
    def setUp(self):
        # Initialize RBAC
        call_command('init_rbac')

        self.client = APIClient()

        # Create Institute
        self.institute = Institute.objects.create(name="Test Institute")

        # Create Users
        self.admin = User.objects.create_user(username="sysadmin", email="admin@test.com", password="pwd", role="admin")
        self.coordinator = User.objects.create_user(username="coord", email="coord@test.com", password="pwd", role="course_coordinator")
        self.teacher = User.objects.create_user(username="teacher", email="teacher@test.com", password="pwd", role="teacher")
        self.mentor = User.objects.create_user(username="mentor", email="mentor@test.com", password="pwd", role="mentor")
        self.learner = User.objects.create_user(username="learner", email="learner@test.com", password="pwd", role="learner")
        self.other_learner = User.objects.create_user(username="learner2", email="learner2@test.com", password="pwd", role="learner")

        # Link mentor to learner
        UserRelation.objects.create(guardian=self.mentor, learner=self.learner, relation_type='mentor')

        # Create Courses
        self.course1 = Course.objects.create(title="Course 1", institute=self.institute, description="test", created_by=self.teacher)
        self.course2 = Course.objects.create(title="Course 2", institute=self.institute, description="test", created_by=self.teacher)

        # Assign coordinator to Course 1 only
        self.course1.coordinators.add(self.coordinator)

    def test_course_coordinator_permissions(self):
        self.client.force_authenticate(user=self.coordinator)
        
        # Course Coordinator should only see Course 1 in their managed list
        response = self.client.get('/api/v1/courses/')
        self.assertEqual(response.status_code, 200)
        # Assuming the view filters by coordinator for course_coordinator role
        # We need to verify if the queryset logic works.
        courses = [c['id'] for c in response.json()['results']]
        self.assertIn(self.course1.id, courses)
        
        # Can they see course 2? Depending on implementation, they might see it if it's public,
        # but they can't MANAGE it. Let's test enrolling a user.
        enroll_data = {'learner_id': self.other_learner.id}
        
        # Coordinator enrolling into Course 1 (Should Succeed)
        res1 = self.client.post(f'/api/v1/courses/{self.course1.id}/enroll/', enroll_data)
        self.assertIn(res1.status_code, [200, 201])
        
        # Coordinator enrolling into Course 2 (Should Fail because they are not coordinator of course 2)
        res2 = self.client.post(f'/api/v1/courses/{self.course2.id}/enroll/', enroll_data)
        self.assertEqual(res2.status_code, 404)

    def test_mentor_proactive_enrollment(self):
        self.client.force_authenticate(user=self.mentor)

        # Mentor enrolling their linked learner (Should Succeed)
        res = self.client.post(f'/api/v1/courses/{self.course1.id}/enroll/', {'learner_id': self.learner.id})
        self.assertIn(res.status_code, [200, 201])

        # Mentor enrolling an unlinked learner (Should Fail)
        res2 = self.client.post(f'/api/v1/courses/{self.course1.id}/enroll/', {'learner_id': self.other_learner.id})
        self.assertEqual(res2.status_code, 403)

    def test_teacher_ai_tools(self):
        self.client.force_authenticate(user=self.teacher)

        res = self.client.post('/api/v1/ai/teacher-tools/', {
            'action': 'generate_course',
            'topic': 'Machine Learning'
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('status', res.json())

        # Learner trying to access teacher AI tools (Should Fail)
        self.client.force_authenticate(user=self.learner)
        res2 = self.client.post('/api/v1/ai/teacher-tools/', {
            'action': 'generate_course',
            'topic': 'Machine Learning'
        })
        self.assertEqual(res2.status_code, 403)

    def test_rbac_matrix_admin(self):
        self.client.force_authenticate(user=self.admin)

        # Get matrix
        res = self.client.get('/api/v1/rbac-matrix/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('roles', data)
        self.assertIn('permissions', data)
        self.assertIn('matrix', data)

        # Update matrix
        new_perms = ['can_view_courses', 'can_enroll_learners']
        res2 = self.client.post('/api/v1/rbac-matrix/', {
            'role': 'mentor',
            'permissions': new_perms
        }, format='json')
        self.assertEqual(res2.status_code, 200)

        # Verify update
        group = Group.objects.get(name='mentor')
        group_perms = [p.codename for p in group.permissions.all()]
        self.assertIn('can_enroll_learners', group_perms)
