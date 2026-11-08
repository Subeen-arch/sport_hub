from decimal import Decimal

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Round
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from .models import Category, Product


class CatalogQueryService:
    def products(self, filters):
        # PostgreSQL rounds NUMERIC halves away from zero, matching positive NPR ROUND_HALF_UP.
        price = Round(ExpressionWrapper(F("original_price") * (100 - F("discount_percent")) / Decimal("100"), output_field=DecimalField(max_digits=12, decimal_places=2)), 2)
        queryset = Product.objects.select_related("category").annotate(sale_price=price)
        if filters.get("search"):
            term = filters["search"]
            queryset = queryset.filter(Q(name__icontains=term) | Q(details__icontains=term) | Q(brand__icontains=term))
        for key, lookup in [("category", "category_id"), ("category_name", "category__name__icontains"), ("brand", "brand__iexact"), ("min_price", "sale_price__gte"), ("max_price", "sale_price__lte"), ("featured", "featured")]:
            if key in filters:
                queryset = queryset.filter(**{lookup: filters[key]})
        if filters.get("stock") == "in_stock":
            queryset = queryset.filter(quantity__gt=0)
        elif filters.get("stock") == "out_of_stock":
            queryset = queryset.filter(quantity=0)
        if "discounted" in filters:
            queryset = queryset.filter(discount_percent__gt=0) if filters["discounted"] else queryset.filter(discount_percent=0)
        ordering = filters.get("ordering", "-id").replace("price", "sale_price")
        return queryset.order_by(ordering, "id")


class CatalogService:
    """Serialize staff catalog writes and lock stock rows shared with checkout."""

    lock_id = 73482001

    def _lock_catalog(self):
        # One transaction-scoped lock also covers an empty catalog and concurrent creates.
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [self.lock_id])

    def _validate(self, entity):
        try:
            entity.full_clean()
        except ModelValidationError as exc:
            raise ValidationError(exc.message_dict) from exc

    def _save(self, entity):
        self._validate(entity)
        try:
            with transaction.atomic():
                entity.save()
        except IntegrityError as exc:
            constraint = getattr(getattr(exc.__cause__, "diag", None), "constraint_name", "")
            if constraint in {"product_name_case_insensitive_unique", "category_name_case_insensitive_unique", "catalog_product_name_key", "catalog_category_name_key"}:
                raise ValidationError({"name": ["This name is already in use."]}) from exc
            raise
        return entity

    @transaction.atomic
    def save_category(self, data, pk=None):
        self._lock_catalog()
        category = get_object_or_404(Category.objects.select_for_update(), pk=pk) if pk else Category()
        category.name = data.get("name", category.name)
        return self._save(category)

    @transaction.atomic
    def delete_category(self, pk):
        self._lock_catalog()
        category = get_object_or_404(Category.objects.select_for_update(), pk=pk)
        try:
            category.delete()
        except ProtectedError as exc:
            raise ValidationError({"detail": "Move or delete this category's products before deleting it."}) from exc

    @transaction.atomic
    def save_product(self, data, pk=None):
        self._lock_catalog()
        product = get_object_or_404(Product.objects.select_for_update(), pk=pk) if pk else Product()
        for field, value in data.items():
            setattr(product, field, value)
        if product.featured and Product.objects.filter(featured=True).exclude(pk=product.pk).count() >= 6:
            raise ValidationError({"featured": ["Only six products can be featured. Unfeature another product first."]})
        if product.pk:
            reserved = product.reservations.filter(status="active").aggregate(total=Sum("quantity"))["total"] or 0
            if product.quantity < reserved:
                raise ValidationError({"quantity": [f"At least {reserved} units are reserved for active payments."]})
        # Old image files remain available to immutable order snapshots.
        return self._save(product)

    @transaction.atomic
    def delete_product(self, pk):
        self._lock_catalog()
        product = get_object_or_404(Product.objects.select_for_update(), pk=pk)
        if product.reservations.filter(status="active").exists():
            raise ValidationError({"detail": "This product has active payment reservations and cannot be deleted."})
        product.delete()
