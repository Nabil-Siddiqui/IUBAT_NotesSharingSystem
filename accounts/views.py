from django.shortcuts import redirect, render

from .forms import StudentRegistrationForm


def register_student(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("registration_pending")
    else:
        form = StudentRegistrationForm()
    return render(request, "accounts/register_student.html", {"form": form})


def registration_pending(request):
    return render(request, "accounts/registration_pending.html")