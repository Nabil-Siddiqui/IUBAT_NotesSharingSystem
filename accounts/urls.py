from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register_student, name="register"),
    path("register/pending/", views.registration_pending, name="registration_pending"),
]