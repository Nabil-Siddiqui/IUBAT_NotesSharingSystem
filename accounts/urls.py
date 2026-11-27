from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register_student, name="register"),
    path("confirm/", views.confirm_email, name="confirm_email"),
    path("confirm/resend/", views.resend_code, name="resend_code"),
]