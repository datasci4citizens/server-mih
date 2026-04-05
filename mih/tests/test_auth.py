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

    def test_users_upsert_compat(self):
        self.client.login(username='tester', password='pwd123')
        payload = {
            'name': 'Tester Name',
            'email': 'tester@example.com',
            'role': 'responsible',
            'is_allowed': True,
            'phone_number': '11999999999',
            'state': 'SP',
            'city': 'Sao Paulo',
            'neighborhood': 'Centro',
            'accept_tcle': True,
        }
        resp = self.client.put('/users/', payload, format='json')
        self.assertEqual(resp.status_code, 200)
        # role must not be client-settable (security hardening)
        self.assertIsNone(resp.data.get('role'))
        self.assertEqual(resp.data.get('name'), 'Tester Name')

        me = self.client.get('/user/me/')
        self.assertEqual(me.status_code, 200)
        # role remains unset for non-staff updates
        self.assertIsNone(me.data.get('role'))
