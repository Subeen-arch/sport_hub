from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from catalog.models import Category, Product, validate_image_size


class CatalogSchemaTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Football")

    def product(self, **overrides):
        data = dict(name="Football", category=self.category, details="Match ball", original_price=Decimal("99.95"), quantity=3, image="products/test.png")
        data.update(overrides)
        return Product.objects.create(**data)

    def test_discount_rounding_and_stock_threshold(self):
        product = self.product(discount_percent=10)
        self.assertEqual(product.price, Decimal("89.96"))
        self.assertEqual(product.stock_status, "low_stock")
        product.quantity = 0
        self.assertEqual(product.stock_status, "out_of_stock")
        product.quantity = 4
        self.assertEqual(product.stock_status, "in_stock")

    def test_database_rejects_invalid_prices_discounts_and_inventory(self):
        for data in [{"original_price": -1}, {"discount_percent": 101}, {"quantity": -1}]:
            with self.subTest(data=data), self.assertRaises(IntegrityError), transaction.atomic():
                self.product(**data)

    def test_category_cannot_be_deleted_with_products(self):
        self.product()
        with self.assertRaises(ProtectedError):
            self.category.delete()

    def test_case_insensitive_product_and_category_names(self):
        self.product()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.product(name="FOOTBALL")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.create(name="FOOTBALL")

    def test_upload_size_boundary(self):
        class Uploaded:
            size = 2_000_001
        with self.assertRaises(ValidationError):
            validate_image_size(Uploaded())
        Uploaded.size = 2_000_000
        validate_image_size(Uploaded())
