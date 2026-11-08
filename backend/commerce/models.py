from uuid import uuid4

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="cart_user_product_unique"),
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="cart_quantity_positive"),
        ]


class WishlistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="wishlist_items")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="wishlist_user_product_unique")]


class Order(models.Model):
    class Method(models.TextChoices):
        COD = "cod", "Cash on delivery"
        KHALTI = "khalti", "Khalti"

    class Fulfillment(models.TextChoices):
        PENDING = "pending", "Pending"
        DISPATCHED = "Dispatched", "Dispatched"
        COMPLETED = "completed", "Completed"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        REFUNDED = "refunded", "Refunded"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially refunded"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    reference = models.UUIDField(default=uuid4, unique=True, editable=False)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=10, validators=[RegexValidator(r"^\d{10}$", "Enter a 10-digit phone number.")])
    country_code = models.CharField(max_length=5, default="+977")
    flat = models.CharField(max_length=100)
    street = models.CharField(max_length=250)
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="Nepal")
    method = models.CharField(max_length=10, choices=Method.choices)
    fulfillment_status = models.CharField(max_length=20, choices=Fulfillment.choices, default=Fulfillment.PENDING, db_index=True)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="NPR", editable=False)
    transaction_id = models.CharField(max_length=100, blank=True)
    payment_ref = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(total__gte=0), name="order_total_nonnegative"),
            models.CheckConstraint(condition=models.Q(method__in=["cod", "khalti"]), name="order_method_valid"),
            models.CheckConstraint(condition=models.Q(fulfillment_status__in=["pending", "Dispatched", "completed"]), name="order_fulfillment_valid"),
            models.CheckConstraint(condition=models.Q(payment_status__in=["pending", "paid", "refunded", "partially_refunded"]), name="order_payment_status_valid"),
            models.CheckConstraint(condition=models.Q(currency="NPR"), name="order_currency_npr"),
        ]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.SET_NULL, null=True, related_name="order_items")
    name = models.CharField(max_length=100)
    image = models.CharField(max_length=500, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="orderitem_quantity_positive"),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="orderitem_price_nonnegative"),
        ]

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class Payment(models.Model):
    class Status(models.TextChoices):
        INITIATED = "Initiated", "Initiated"
        PENDING = "Pending", "Pending"
        COMPLETED = "Completed", "Completed"
        FAILED = "Failed", "Failed"
        CANCELED = "User canceled", "User canceled"
        EXPIRED = "Expired", "Expired"
        REFUNDED = "Refunded", "Refunded"
        PARTIALLY_REFUNDED = "Partially refunded", "Partially refunded"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")
    order = models.OneToOneField(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="payment")
    purchase_order_id = models.UUIDField(default=uuid4, unique=True, editable=False)
    request_key = models.UUIDField(null=True, blank=True, unique=True)
    environment = models.CharField(max_length=10, choices=[('sandbox', 'Sandbox'), ('live', 'Live')], default='sandbox')
    pidx = models.CharField(max_length=100, unique=True, null=True, blank=True)
    amount_paisa = models.PositiveBigIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)
    provider_status = models.CharField(max_length=40, blank=True)
    needs_review = models.BooleanField(default=False)
    failure_code = models.CharField(max_length=50, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    khalti_transaction_id = models.CharField(max_length=100, blank=True)
    checkout_snapshot = models.JSONField(default=dict)
    cart_item_ids = models.JSONField(default=list)
    payment_url = models.URLField(max_length=1000, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount_paisa__gte=1), name="payment_amount_positive"),
            models.CheckConstraint(condition=models.Q(status__in=["Initiated", "Pending", "Completed", "Failed", "User canceled", "Expired", "Refunded", "Partially refunded"]), name="payment_status_valid"),
            models.UniqueConstraint(fields=['khalti_transaction_id'], condition=~models.Q(khalti_transaction_id=''), name='payment_transaction_unique'),
            models.CheckConstraint(condition=models.Q(environment__in=['sandbox', 'live']), name='payment_environment_valid'),
        ]


class InventoryReservation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CONSUMED = "consumed", "Consumed"
        RELEASED = "released", "Released"

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="reservations")
    product = models.ForeignKey("catalog.Product", on_delete=models.SET_NULL, null=True, related_name="reservations")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["payment", "product"], name="reservation_payment_product_unique"),
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="reservation_quantity_positive"),
            models.CheckConstraint(condition=models.Q(status__in=["active", "consumed", "released"]), name="reservation_status_valid"),
        ]
