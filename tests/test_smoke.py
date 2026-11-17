import os
import tempfile
import unittest
from app import create_app


class SmokeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["SQLITE_PATH"] = os.path.join(self.tmp.name, "test.db")
        os.environ["INITIAL_STUDENT_PASSWORD"] = "test-password-123"
        os.environ["SECRET_KEY"] = "test-secret"
        self.app = create_app()
        self.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("SQLITE_PATH", None)
        os.environ.pop("INITIAL_STUDENT_PASSWORD", None)

    def test_public_pages(self):
        for path in ['/', '/about', '/academics', '/facilities', '/library',
                     '/admissions', '/news', '/contact']:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_student_login(self):
        response = self.client.post(
            '/student-portal',
            data={'full_name': 'Emmanuel Darko', 'password': 'test-password-123'},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/change-password', response.location)

    def test_admin_login_and_dashboard(self):
        response = self.client.post('/admin/login', data={
            'username': 'admin', 'password': 'ChangeMe123!'
        })
        self.assertEqual(response.status_code, 302)
        dashboard = self.client.get('/admin')
        self.assertEqual(dashboard.status_code, 200)


if __name__ == '__main__':
    unittest.main()
