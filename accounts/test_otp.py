import re
from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import otp
from .models import Department, EmailOTP, User


def latest_code():
    """Read the 6-digit code out of the newest email."""
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)


def wrong_version_of(code):
    return "000000" if code != "000000" else "111111"


def make_student(username="12345678"):
    return User.objects.create_user(
        username=username, password="a-Strong-pass-472",
        full_name="Test Student", is_active=False,
    )


class OtpFunctionTests(TestCase):
    def setUp(self):
        self.user = make_student()

    def test_code_is_emailed_to_the_university_address(self):
        otp.send_code(self.user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["12345678@iubat.edu"])

    def test_code_is_stored_hashed(self):
        otp.send_code(self.user)
        self.assertNotEqual(EmailOTP.objects.get().code_hash, latest_code())

    def test_correct_code_is_accepted(self):
        otp.send_code(self.user)
        self.assertEqual(otp.check_code(self.user, latest_code()), "ok")

    def test_wrong_code_is_rejected(self):
        otp.send_code(self.user)
        bad = wrong_version_of(latest_code())
        self.assertEqual(otp.check_code(self.user, bad), "wrong")

    def test_code_works_only_once(self):
        otp.send_code(self.user)
        code = latest_code()
        self.assertEqual(otp.check_code(self.user, code), "ok")
        self.assertEqual(otp.check_code(self.user, code), "none")

    def test_expired_code_is_rejected(self):
        otp.send_code(self.user)
        EmailOTP.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(otp.check_code(self.user, latest_code()), "expired")

    def test_five_wrong_attempts_lock_the_code(self):
        otp.send_code(self.user)
        code = latest_code()
        bad = wrong_version_of(code)
        for _ in range(otp.MAX_ATTEMPTS - 1):
            self.assertEqual(otp.check_code(self.user, bad), "wrong")
        self.assertEqual(otp.check_code(self.user, bad), "locked")
        self.assertEqual(otp.check_code(self.user, code), "locked")

    def test_a_new_code_replaces_the_old_one(self):
        otp.send_code(self.user)
        otp.send_code(self.user)
        self.assertEqual(self.user.email_codes.filter(is_used=False).count(), 1)

    def test_resend_cooldown(self):
        self.assertEqual(otp.seconds_until_resend(self.user), 0)
        otp.send_code(self.user)
        self.assertGreater(otp.seconds_until_resend(self.user), 0)
        EmailOTP.objects.update(created_at=timezone.now() - timedelta(seconds=61))
        self.assertEqual(otp.seconds_until_resend(self.user), 0)

    def test_confirming_a_student_activates_and_verifies(self):
        otp.confirm_user(self.user)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(self.user.is_verified)


class ConfirmEmailViewTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="CSE", code="03")

    def register(self, **changes):
        data = {
            "username": "12345678",
            "full_name": "Test Student",
            "department": self.department.id,
            "password1": "a-Strong-pass-472",
            "password2": "a-Strong-pass-472",
        }
        data.update(changes)
        return self.client.post(reverse("register"), data)

    def test_registering_sends_a_code_and_opens_the_confirm_page(self):
        response = self.register()
        self.assertRedirects(response, reverse("confirm_email"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["12345678@iubat.edu"])

    def test_confirm_page_needs_a_registration_first(self):
        response = self.client.get(reverse("confirm_email"))
        self.assertRedirects(response, reverse("register"))

    def test_correct_code_activates_the_account(self):
        self.register()
        response = self.client.post(reverse("confirm_email"), {"code": latest_code()})
        self.assertRedirects(response, reverse("home"))
        user = User.objects.get(username="12345678")
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_verified)

    def test_wrong_code_does_not_activate_the_account(self):
        self.register()
        bad = wrong_version_of(latest_code())
        response = self.client.post(reverse("confirm_email"), {"code": bad})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not correct")
        self.assertFalse(User.objects.get(username="12345678").is_active)

    def test_malformed_code_does_not_use_up_an_attempt(self):
        self.register()
        response = self.client.post(reverse("confirm_email"), {"code": "12ab"})
        self.assertContains(response, "exactly 6 digits")
        self.assertEqual(EmailOTP.objects.get().attempts, 0)

    def test_resend_is_blocked_during_the_cooldown(self):
        self.register()
        response = self.client.post(reverse("resend_code"))
        self.assertRedirects(response, reverse("confirm_email"))
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_works_after_the_cooldown(self):
        self.register()
        EmailOTP.objects.update(created_at=timezone.now() - timedelta(seconds=61))
        self.client.post(reverse("resend_code"))
        self.assertEqual(len(mail.outbox), 2)

    def test_resend_only_accepts_post(self):
        self.register()
        self.assertEqual(self.client.get(reverse("resend_code")).status_code, 405)

    def test_registering_again_replaces_an_unconfirmed_account(self):
        self.register()
        self.register(
            full_name="Real Owner",
            password1="another-Pass-9021",
            password2="another-Pass-9021",
        )
        self.assertEqual(User.objects.filter(username="12345678").count(), 1)
        user = User.objects.get(username="12345678")
        self.assertEqual(user.full_name, "Real Owner")
        self.assertTrue(user.check_password("another-Pass-9021"))
        self.assertEqual(len(mail.outbox), 1)  # the cooldown blocks a second email

    def test_a_confirmed_id_cannot_be_registered_again(self):
        self.register()
        User.objects.filter(username="12345678").update(is_active=True, is_verified=True)
        response = self.register(full_name="Someone Else")
        self.assertContains(response, "already registered")
        self.assertEqual(User.objects.get(username="12345678").full_name, "Test Student")