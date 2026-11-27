from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import otp
from .forms import ConfirmEmailForm, StudentRegistrationForm
from .models import User

PENDING_SESSION_KEY = "pending_user_id"

CODE_ERRORS = {
    "wrong": "That code is not correct. Check your email and try again.",
    "expired": "That code has expired. Ask for a new one.",
    "locked": "Too many wrong attempts. Ask for a new code.",
    "none": "There is no active code. Ask for a new one.",
}


def register_student(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        # An unconfirmed account for this ID is replaced, not rejected.
        unconfirmed = User.objects.filter(
            username=username, role=User.Role.STUDENT,
            is_active=False, is_verified=False,
        ).first()
        form = StudentRegistrationForm(request.POST, instance=unconfirmed)
        if form.is_valid():
            user = form.save()
            if otp.seconds_until_resend(user) == 0:
                otp.send_code(user)
            request.session[PENDING_SESSION_KEY] = user.pk
            return redirect("confirm_email")
    else:
        form = StudentRegistrationForm()
    return render(request, "accounts/register_student.html", {"form": form})


def _pending_user(request):
    user_id = request.session.get(PENDING_SESSION_KEY)
    if user_id is None:
        return None
    return User.objects.filter(pk=user_id, is_active=False).first()


def confirm_email(request):
    user = _pending_user(request)
    if user is None:
        messages.error(request, "Please register first.")
        return redirect("register")

    if request.method == "POST":
        form = ConfirmEmailForm(request.POST)
        if form.is_valid():
            result = otp.check_code(user, form.cleaned_data["code"])
            if result == "ok":
                otp.confirm_user(user)
                del request.session[PENDING_SESSION_KEY]
                messages.success(request, "Your email is confirmed and your account is active.")
                return redirect("home")
            form.add_error("code", CODE_ERRORS[result])
    else:
        form = ConfirmEmailForm()

    context = {
        "form": form,
        "email": user.email,
        "minutes": int(otp.CODE_LIFETIME.total_seconds() // 60),
    }
    return render(request, "accounts/confirm_email.html", context)


@require_POST
def resend_code(request):
    user = _pending_user(request)
    if user is None:
        return redirect("register")
    wait = otp.seconds_until_resend(user)
    if wait > 0:
        messages.error(request, f"Please wait {wait} seconds before asking for another code.")
    else:
        otp.send_code(user)
        messages.success(request, "A new code has been sent.")
    return redirect("confirm_email")