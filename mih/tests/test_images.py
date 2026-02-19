from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


class ImageUploadTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='imguser', password='pwd123')
        self.client = APIClient()

    def test_upload_image(self):
        self.client.login(username='imguser', password='pwd123')
        content = b"hello world"
        f = SimpleUploadedFile('photo.jpg', content, content_type='image/jpeg')
        resp = self.client.post('/api/images/', {'file': f}, format='multipart')
        self.assertEqual(resp.status_code, 201)
        self.assertIn('id', resp.data)
