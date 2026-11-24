from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import User


class UserRuleTests(TestCase):
    def test_student_username_must_be_8_digits(self):
        user = User(username="1234", role=User.Role.STUDENT, full_name="Test")
        with self.assertRaises(ValidationError):
            user.clean()

    def test_student_email_is_built_from_the_id(self):
        user = User.objects.create_user(username="12345678", password="x", full_name="Test")
        self.assertEqual(user.email, "12345678@iubat.edu")

    def test_faculty_username_must_be_their_email(self):
        user = User(username="teacher", email="teacher@iubat.edu",
                    role=User.Role.FACULTY, full_name="Test")
        with self.assertRaises(ValidationError):
            user.clean()

    def test_faculty_must_use_the_university_domain(self):
        user = User(username="t@gmail.com", email="t@gmail.com",
                    role=User.Role.FACULTY, full_name="Test")
        with self.assertRaises(ValidationError):
            user.clean()