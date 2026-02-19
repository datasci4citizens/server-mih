from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


class AuthSessionToJWTTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', email='tester@example.com', password='pwd123')
        self.client = APIClient()

    def test_session_to_jwt_token(self):
        logged = self.client.login(username='tester', password='pwd123')
        self.assertTrue(logged)
        resp = self.client.post('/api/auth/token/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)

    def test_current_user(self):
        self.client.login(username='tester', password='pwd123')
        resp = self.client.get('/api/auth/user/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get('username'), 'tester')
