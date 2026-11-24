from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "IUBAT Notes")

    def test_logged_out_visitor_sees_login_and_register(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Log in")
        self.assertContains(response, "Register")