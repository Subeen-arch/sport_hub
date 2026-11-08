from django.db import IntegrityError, connection, transaction
from django.test import TestCase

from accounts.models import User

from django.core.cache import cache
from rest_framework.test import APIClient


class AccountSchemaTests(TestCase):
    def test_postgresql_only(self):
        self.assertEqual(connection.vendor, "postgresql")
        self.assertEqual(connection.settings_dict["NAME"], "test_sporthub_next")

    def test_password_hash_and_email_normalization(self):
        user = User.objects.create_user(username="customer", name="Customer", email="Person@EXAMPLE.com", password="independent-test-password")
        self.assertEqual(user.email, "person@example.com")
        self.assertNotEqual(user.password, "independent-test-password")
        self.assertTrue(user.check_password("independent-test-password"))
        self.assertFalse(user.is_staff)

    def test_email_and_username_uniqueness_is_case_insensitive(self):
        User.objects.create_user(username="customer", email="customer@example.com", password="independent-test-password")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username="other", email="CUSTOMER@example.com", password="independent-test-password")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username="CUSTOMER", email="different@example.com", password="independent-test-password")


class AccountApiTests(TestCase):
    password = "River!Trail8426"

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.registration = {
            "name": "Trail Runner", "email": "runner@example.com", "phone": "9812345678",
            "country_code": "+977", "password": self.password, "password_confirm": self.password,
        }

    def csrf(self, client=None):
        client = client or self.client
        response = client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        client.credentials(HTTP_X_CSRFTOKEN=response.data["csrfToken"])
        return response.data["csrfToken"]

    def register(self):
        self.csrf()
        response = self.client.post("/api/auth/register/", self.registration, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.csrf()
        return response

    def test_guest_mutations_require_csrf(self):
        for endpoint in ["register", "login", "logout", "password"]:
            with self.subTest(endpoint=endpoint):
                response = self.client.post(f"/api/auth/{endpoint}/", self.registration, format="json")
                self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_starts_session_and_returns_only_public_fields(self):
        self.registration["email"] = "RUNNER@EXAMPLE.COM"
        response = self.register()
        self.assertEqual(response.data["email"], "runner@example.com")
        self.assertFalse(response.data["is_staff"])
        self.assertEqual(set(response.data), {"id", "username", "name", "email", "phone", "country_code", "is_staff"})
        self.assertEqual(self.client.get("/api/auth/me/").data["id"], response.data["id"])
        self.assertTrue(User.objects.get().check_password(self.password))
        self.assertTrue(self.client.cookies["sessionid"]["httponly"])
        self.assertTrue(self.client.cookies["csrftoken"]["httponly"])
        self.assertIn("no-store", response["Cache-Control"])

    def test_registration_rejects_privilege_fields(self):
        self.csrf()
        for field in ["is_staff", "is_superuser", "username", "id"]:
            with self.subTest(field=field):
                response = self.client.post("/api/auth/register/", {**self.registration, field: True}, format="json")
                self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_registration_validation(self):
        self.csrf()
        for invalid in [
            {"phone": "123"}, {"phone": "９８１２３４５６７８"}, {"country_code": "+1"},
            {"password_confirm": "different"}, {"name": "   "}, {"email": "broken"},
            {"password": "Abc12345", "password_confirm": "Abc12345"},
            {"password": "Ab1!", "password_confirm": "Ab1!"},
        ]:
            with self.subTest(invalid=invalid):
                response = self.client.post("/api/auth/register/", {**self.registration, **invalid}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(User.objects.exists())

    def test_duplicate_email_case_insensitive(self):
        self.register()
        response = self.client.post("/api/auth/register/", {**self.registration, "email": "RUNNER@example.com"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_login_rotates_csrf_and_logout_ends_session(self):
        self.register()
        self.assertEqual(self.client.post("/api/auth/logout/", {}, format="json").status_code, 204)
        old_token = self.csrf()
        response = self.client.post("/api/auth/login/", {"email": "RUNNER@EXAMPLE.COM", "password": self.password}, format="json")
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_X_CSRFTOKEN=old_token)
        self.assertEqual(self.client.patch("/api/auth/profile/", {"name": "Updated"}, format="json").status_code, 403)
        self.csrf()
        self.assertEqual(self.client.patch("/api/auth/profile/", {"name": "Updated"}, format="json").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/logout/", {}, format="json").status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 403)

    def test_staff_username_login_and_server_permission(self):
        self.register()
        self.assertEqual(self.client.get("/api/admin/session/").status_code, 403)
        self.client.post("/api/auth/logout/", {}, format="json")
        staff = User.objects.create_user(username="Coach", email="coach@example.com", password=self.password, is_staff=True)
        self.csrf()
        response = self.client.post("/api/auth/login/", {"username": "COACH", "password": self.password}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/admin/session/").data["id"], staff.pk)
        self.csrf()
        response = self.client.patch("/api/auth/profile/", {"username": "NewCoach"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "NewCoach")

    def test_login_rejects_inactive_wrong_password_and_customer_username(self):
        user = User.objects.create_user(username="runner", email="runner@example.com", password=self.password)
        self.csrf()
        for credentials in [
            {"email": user.email, "password": "wrong"},
            {"email": "missing@example.com", "password": self.password},
            {"username": user.username, "password": self.password},
            {"email": user.email, "username": user.username, "password": self.password},
        ]:
            response = self.client.post("/api/auth/login/", credentials, format="json")
            self.assertEqual(response.status_code, 400)
        user.is_active = False
        user.save()
        response = self.client.post("/api/auth/login/", {"email": user.email, "password": self.password}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_profile_cannot_change_another_user_or_privileges(self):
        self.register()
        other = User.objects.create_user(username="other", email="other@example.com", password=self.password)
        for data in [{"id": other.pk}, {"is_staff": True}, {"username": "stolen"}, {"email": "OTHER@example.com"}]:
            response = self.client.patch("/api/auth/profile/", data, format="json")
            self.assertEqual(response.status_code, 400)
        response = self.client.patch("/api/auth/profile/", {"name": "New Name", "email": "NEW@example.com"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "new@example.com")
        other.refresh_from_db()
        self.assertEqual(other.email, "other@example.com")

    def test_password_change_retains_current_session_invalidates_other_session(self):
        self.register()
        other_client = APIClient(enforce_csrf_checks=True)
        self.csrf(other_client)
        other_client.post("/api/auth/login/", {"email": self.registration["email"], "password": self.password}, format="json")
        new_password = "New!Summit8426"
        response = self.client.post("/api/auth/password/", {
            "old_password": self.password, "new_password": new_password, "password_confirm": new_password,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)
        self.assertEqual(other_client.get("/api/auth/me/").status_code, 403)
        self.assertTrue(User.objects.get().check_password(new_password))
        self.csrf()
        self.assertEqual(self.client.patch("/api/auth/profile/", {"name": "Still signed in"}, format="json").status_code, 200)

    def test_password_rejects_wrong_current_weak_or_mismatched(self):
        self.register()
        payload = {"old_password": self.password, "new_password": "Next!Summit8426", "password_confirm": "Next!Summit8426"}
        for invalid in [
            {"old_password": "wrong"}, {"password_confirm": "different"},
            {"new_password": "abc", "password_confirm": "abc"},
            {"new_password": "NextSummit8426", "password_confirm": "NextSummit8426"},
        ]:
            response = self.client.post("/api/auth/password/", {**payload, **invalid}, format="json")
            self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.get().check_password(self.password))

    def test_anonymous_cannot_read_or_update_profile(self):
        self.csrf()
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 403)
        self.assertEqual(self.client.get("/api/admin/session/").status_code, 403)
        self.assertEqual(self.client.patch("/api/auth/profile/", {"name": "No session"}, format="json").status_code, 403)

    def test_untrusted_origin_rejected(self):
        self.csrf()
        response = self.client.post("/api/auth/register/", self.registration, format="json", HTTP_ORIGIN="https://untrusted.example")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.exists())

    def test_login_rate_limit(self):
        self.csrf()
        for _ in range(10):
            response = self.client.post("/api/auth/login/", {}, format="json")
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post("/api/auth/login/", {}, format="json").status_code, 429)
