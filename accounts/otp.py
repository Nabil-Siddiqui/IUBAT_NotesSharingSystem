import math
import secrets
import string
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db.models import F
from django.utils import timezone

from .models import EmailOTP, User

CODE_LENGTH = 6
CODE_LIFETIME = timedelta(minutes=10)
MAX_ATTEMPTS = 5
RESEND_COOLDOWN = timedelta(seconds=60)


def generate_code():
    return "".join(secrets.choice(string.digits) for _ in range(CODE_LENGTH))


def seconds_until_resend(user):
    latest = user.email_codes.order_by("-created_at").first()
    if latest is None:
        return 0
    wait = latest.created_at + RESEND_COOLDOWN - timezone.now()
    return max(0, math.ceil(wait.total_seconds()))


def send_code(user):
    """Cancel any older codes, make a new one, and email it to the user."""
    user.email_codes.filter(is_used=False).update(is_used=True)
    code = generate_code()
    EmailOTP.objects.create(
        user=user,
        code_hash=make_password(code),
        expires_at=timezone.now() + CODE_LIFETIME,
    )
    minutes = int(CODE_LIFETIME.total_seconds() // 60)
    send_mail(
        subject="Your IUBAT Notes confirmation code",
        message=(
            f"Your confirmation code is {code}.\n\n"
            f"It expires in {minutes} minutes. "
            "If you did not register, you can ignore this email."
        ),
        from_email=None,  # None means use DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
    )


def check_code(user, submitted):
    """Return 'ok', 'wrong', 'expired', 'locked' or 'none'."""
    code = user.email_codes.filter(is_used=False).order_by("-created_at").first()
    if code is None:
        return "none"
    if code.expires_at <= timezone.now():
        return "expired"

    # Claim one attempt BEFORE comparing. The database does this in a single
    # step, so many requests sent at the same moment cannot get extra guesses.
    claimed = EmailOTP.objects.filter(pk=code.pk, attempts__lt=MAX_ATTEMPTS).update(
        attempts=F("attempts") + 1
    )
    if not claimed:
        return "locked"

    if check_password(submitted, code.code_hash):
        EmailOTP.objects.filter(pk=code.pk).update(is_used=True)
        return "ok"

    code.refresh_from_db()
    return "locked" if code.attempts >= MAX_ATTEMPTS else "wrong"


def confirm_user(user):
    """Activate the account after a correct code."""
    user.email_codes.update(is_used=True)
    user.is_active = True
    if user.role == User.Role.STUDENT:
        user.is_verified = True  # faculty also need admin approval (Module 7)
    user.save(update_fields=["is_active", "is_verified"])