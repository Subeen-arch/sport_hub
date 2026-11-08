from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower


def product_image_path(instance, filename):
    return f"products/{uuid4().hex}{Path(filename).suffix.lower()}"


def validate_image_size(value):
    if value.size > 2_000_000:
        raise ValidationError("Image must be no larger than 2 MB.")


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(Lower("name"), name="category_name_case_insensitive_unique")]

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=100, unique=True)
    brand = models.CharField(max_length=100, blank=True)
    details = models.CharField(max_length=500)
    original_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    discount_percent = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    quantity = models.PositiveIntegerField(default=0)
    featured = models.BooleanField(default=False, db_index=True)
    image = models.ImageField(upload_to=product_image_path, validators=[validate_image_size])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(Lower("name"), name="product_name_case_insensitive_unique"),
            models.CheckConstraint(condition=models.Q(original_price__gte=0), name="product_price_nonnegative"),
            models.CheckConstraint(condition=models.Q(discount_percent__gte=0, discount_percent__lte=100), name="product_discount_valid"),
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name="product_quantity_nonnegative"),
        ]

    @property
    def price(self):
        return (self.original_price * (100 - self.discount_percent) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def stock_status(self):
        return "out_of_stock" if self.quantity == 0 else "low_stock" if self.quantity <= 3 else "in_stock"

    def __str__(self):
        return self.name
