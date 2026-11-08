from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import User
from commerce.models import InventoryReservation, Payment
from .models import Category, Product


def raster_upload(image_format="PNG", suffix="png", extra=b""):
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "green").save(buffer, format=image_format)
    return SimpleUploadedFile(f"unsafe-name.{suffix}", buffer.getvalue() + extra, content_type=f"image/{suffix}")


class CatalogApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        override = override_settings(MEDIA_ROOT=self.media.name)
        override.enable()
        self.addCleanup(override.disable)
        self.category = Category.objects.create(name="Football")
        self.staff = User.objects.create_user(username="coach", email="coach@example.com", is_staff=True)
        self.customer = User.objects.create_user(username="runner", email="runner@example.com")
        self.client = APIClient(enforce_csrf_checks=True)

    def authorize(self, user=None):
        self.client.force_login(user or self.staff)
        token = self.client.get("/api/auth/csrf/").data["csrfToken"]
        self.client.credentials(HTTP_X_CSRFTOKEN=token)

    def payload(self, **overrides):
        data = dict(name="Match ball", category=self.category.pk, details="Outdoor practice", original_price="99.95", discount_percent=10, quantity=5, featured=False, image=raster_upload())
        data.update(overrides)
        return data

    def product(self, **overrides):
        data = dict(name="Match ball", category=self.category, details="Outdoor practice", original_price="99.95", discount_percent=10, quantity=5, image=raster_upload())
        data.update(overrides)
        return Product.objects.create(**data)

    def test_public_filters_price_rounding_ordering_and_detail(self):
        ball = self.product(brand="Sport Brand", featured=True)
        self.product(name="Boots", quantity=0, original_price="200.00", discount_percent=0)
        query = {"search": "practice", "category": self.category.pk, "brand": "sport brand", "stock": "in_stock", "featured": "true", "discounted": "true", "min_price": "89.96", "max_price": "89.96", "ordering": "price"}
        response = self.client.get("/api/products/", query)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["price"], "89.96")
        self.assertEqual(self.client.get(f"/api/products/{ball.pk}/").data["category_name"], "Football")
        descending = self.client.get("/api/products/", {"ordering": "-price"}).data["results"]
        self.assertEqual([row["name"] for row in descending], ["Boots", "Match ball"])
        self.assertEqual(self.client.get("/api/catalog/options/").data, {"brands": ["Sport Brand"]})

    def test_invalid_filters_and_missing_product(self):
        for query in [{"min_price": "5", "max_price": "4"}, {"ordering": "password"}, {"stock": "bad"}, {"category": "0"}, {"min_price": "NaN"}]:
            with self.subTest(query=query):
                self.assertEqual(self.client.get("/api/products/", query).status_code, 400)
        self.assertEqual(self.client.get("/api/products/9999/").status_code, 404)

    def test_pagination_and_empty_results(self):
        self.assertEqual(self.client.get("/api/products/").data["results"], [])
        for index in range(25):
            self.product(name=f"Ball {index}")
        first = self.client.get("/api/products/").data
        self.assertEqual(first["count"], 25)
        self.assertEqual(len(first["results"]), 24)
        self.assertIsNotNone(first["next"])
        self.assertEqual(len(self.client.get("/api/products/?page=2").data["results"]), 1)

    def test_staff_permissions_and_csrf(self):
        ball = self.product()
        for user in [None, self.customer]:
            if user:
                self.authorize(user)
            for path in ["/api/admin/products/", f"/api/admin/products/{ball.pk}/", "/api/admin/categories/", f"/api/admin/categories/{self.category.pk}/"]:
                with self.subTest(user=user, path=path):
                    self.assertEqual(self.client.get(path).status_code, 403)
                    self.assertEqual(self.client.patch(path, {}, format="json").status_code, 403)
                    self.assertEqual(self.client.delete(path).status_code, 403)
        self.client.force_login(self.staff)
        self.client.credentials()
        self.assertEqual(self.client.post("/api/admin/categories/", {"name": "Fitness"}, format="json").status_code, 403)

    def test_product_create_update_delete_and_image_sanitization(self):
        self.authorize()
        response = self.client.post("/api/admin/products/", self.payload(image=raster_upload(extra=b"<script>bad</script>")), format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        product = Product.objects.get(pk=response.data["id"])
        self.assertNotIn("unsafe-name", product.image.name)
        self.assertNotIn(b"<script>", Path(product.image.path).read_bytes())
        url = f"/api/admin/products/{product.pk}/"
        updated = self.client.patch(url, {"quantity": 2, "discount_percent": 100, "featured": True}, format="json")
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["price"], "0.00")
        self.assertEqual(updated.data["stock_status"], "low_stock")
        self.assertTrue(updated.data["featured"])
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(Product.objects.exists())

    def test_upload_content_and_size_validation(self):
        self.authorize()
        uploads = [SimpleUploadedFile("bad.png", b"not an image"), raster_upload("GIF", "gif"), SimpleUploadedFile("large.png", b"x" * 2_000_001)]
        for upload in uploads:
            with self.subTest(upload=upload.name):
                response = self.client.post("/api/admin/products/", self.payload(image=upload), format="multipart")
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn("image", response.data)
        self.assertFalse(Product.objects.exists())
        self.assertEqual(list(Path(self.media.name).rglob("*")), [])

    def test_product_rejects_duplicate_unknown_and_invalid_values(self):
        self.authorize()
        self.product()
        for overrides in [{"name": "MATCH BALL"}, {"name": "New", "price": "1.00"}, {"quantity": -1}, {"discount_percent": 101}, {"original_price": "-1"}, {"category": 9999}]:
            with self.subTest(overrides=overrides):
                response = self.client.post("/api/admin/products/", self.payload(**overrides), format="multipart")
                self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Product.objects.count(), 1)

    def test_featured_limit_allows_edit_and_replacement(self):
        self.authorize()
        featured = [self.product(name=f"Featured {index}", featured=True) for index in range(6)]
        extra = self.product(name="Extra")
        url = f"/api/admin/products/{extra.pk}/"
        self.assertEqual(self.client.patch(url, {"featured": True}, format="json").status_code, 400)
        first_url = f"/api/admin/products/{featured[0].pk}/"
        self.assertEqual(self.client.patch(first_url, {"details": "Updated"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(first_url, {"featured": False}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(url, {"featured": True}, format="json").status_code, 200)

    def test_active_reservations_block_stock_reduction_and_deletion(self):
        self.authorize()
        product = self.product()
        payment = Payment.objects.create(user=self.customer, amount_paisa=100)
        reservation = InventoryReservation.objects.create(product=product, payment=payment, quantity=3)
        url = f"/api/admin/products/{product.pk}/"
        self.assertEqual(self.client.patch(url, {"quantity": 2}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 400)
        product.refresh_from_db()
        self.assertEqual(product.quantity, 5)
        reservation.status = "released"
        reservation.save()
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_category_lifecycle_and_protected_deletion(self):
        self.authorize()
        response = self.client.post("/api/admin/categories/", {"name": "Fitness"}, format="json")
        self.assertEqual(response.status_code, 201)
        url = f"/api/admin/categories/{response.data['id']}/"
        self.assertEqual(self.client.patch(url, {"name": "Gym"}, format="json").data["name"], "Gym")
        self.assertEqual(self.client.post("/api/admin/categories/", {"name": "GYM"}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.product()
        self.assertEqual(self.client.delete(f"/api/admin/categories/{self.category.pk}/").status_code, 400)
