from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from .models import ContactMessage


class ContactApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.data = dict(name="Runner", email="RUNNER@example.com", phone="9812345678", country_code="+977", message="Is this ball available?")

    def csrf(self):
        token = self.client.get("/api/auth/csrf/").data["csrfToken"]
        self.client.credentials(HTTP_X_CSRFTOKEN=token)

    def test_guest_csrf_duplicates_and_private_listing(self):
        self.assertEqual(self.client.post("/api/messages/", self.data, format="json").status_code, 403)
        self.csrf()
        result = self.client.post("/api/messages/", self.data, format="json")
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.data["email"], "runner@example.com")
        self.assertIsNone(ContactMessage.objects.get().user)
        self.assertEqual(self.client.post("/api/messages/", self.data, format="json").status_code, 400)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(self.client.get("/api/messages/").status_code, 405)

    def test_authenticated_ownership_and_input_validation(self):
        user = User.objects.create_user(username="runner", email="runner@example.com")
        self.client.force_login(user)
        self.csrf()
        for values in [{"user": user.pk}, {"email": "bad"}, {"phone": "123"}, {"country_code": "+1"}, {"message": " "}, {"message": "x" * 501}]:
            self.assertEqual(self.client.post("/api/messages/", {**self.data, **values}, format="json").status_code, 400)
        self.assertFalse(ContactMessage.objects.exists())
        self.assertEqual(self.client.post("/api/messages/", self.data, format="json").status_code, 201)
        self.assertEqual(ContactMessage.objects.get().user, user)

    def test_contact_throttle(self):
        self.csrf()
        for index in range(10):
            self.assertEqual(self.client.post("/api/messages/", {**self.data, "message": str(index)}, format="json").status_code, 201)
        self.assertEqual(self.client.post("/api/messages/", {**self.data, "message": "blocked"}, format="json").status_code, 429)
