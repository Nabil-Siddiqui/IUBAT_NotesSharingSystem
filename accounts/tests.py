from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Department, User

BENGALI_DIGITS = "\u09e7\u09e8\u09e9\u09ea\u09eb\u09ec\u09ed\u09ee"  # 12345678 in Bengali


class UserRuleTests(TestCase):
    def test_student_username_must_be_8_digits(self):
        user = User(username="1234", role=User.Role.STUDENT, full_name="Test")
        with self.assertRaises(ValidationError):
            user.clean()

    def test_student_username_rejects_non_ascii_digits(self):
        user = User(username=BENGALI_DIGITS, role=User.Role.STUDENT, full_name="Test")
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


class StudentRegistrationTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="Computer Science and Engineering", code="CSE"
        )
        self.url = reverse("register")

    def valid_data(self, **changes):
        data = {
            "username": "12345678",
            "full_name": "Test Student",
            "department": self.department.id,
            "password1": "a-Strong-pass-472",
            "password2": "a-Strong-pass-472",
        }
        data.update(changes)
        return data

    def assert_rejected(self, response, message):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, message)
        self.assertEqual(User.objects.count(), 0)

    def test_register_page_loads(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_department_dropdown_shows_names_and_has_no_blank_option(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Computer Science and Engineering")
        self.assertNotContains(response, "Select your department")
        self.assertNotContains(response, "---------")

    def test_batch_is_not_asked(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, 'name="batch"')

    def test_valid_registration_creates_an_inactive_student(self):
        response = self.client.post(self.url, self.valid_data())
        self.assertRedirects(response, reverse("registration_pending"))
        user = User.objects.get(username="12345678")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_verified)
        self.assertEqual(user.email, "12345678@iubat.edu")
        self.assertTrue(user.check_password("a-Strong-pass-472"))

    def test_id_with_letters_is_rejected(self):
        response = self.client.post(self.url, self.valid_data(username="1234abcd"))
        self.assert_rejected(response, "digits only")

    def test_bengali_digits_are_rejected(self):
        response = self.client.post(self.url, self.valid_data(username=BENGALI_DIGITS))
        self.assert_rejected(response, "digits only")

    def test_id_that_is_too_short_is_rejected(self):
        response = self.client.post(self.url, self.valid_data(username="1234"))
        self.assert_rejected(response, "exactly 8 digits")

    def test_id_that_is_too_long_is_rejected(self):
        response = self.client.post(self.url, self.valid_data(username="123456789"))
        self.assert_rejected(response, "exactly 8 digits")

    def test_empty_id_is_rejected(self):
        response = self.client.post(self.url, self.valid_data(username=""))
        self.assert_rejected(response, "Enter your student ID.")

    def test_duplicate_id_is_rejected(self):
        self.client.post(self.url, self.valid_data())
        response = self.client.post(self.url, self.valid_data(full_name="Someone Else"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already registered")
        self.assertEqual(User.objects.filter(username="12345678").count(), 1)

    def test_passwords_must_match(self):
        response = self.client.post(self.url, self.valid_data(password2="different-pass-999"))
        self.assert_rejected(response, "do not match")