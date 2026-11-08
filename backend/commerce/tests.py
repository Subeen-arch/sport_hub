from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User
from catalog.models import Category, Product
from commerce.models import CartItem, InventoryReservation, Order, OrderItem, Payment, WishlistItem


class CommerceSchemaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="shopper", email="shopper@example.com", password="independent-test-password")
        self.product = Product.objects.create(name="Ball", category=Category.objects.create(name="Balls"), original_price="25.50", details="Training ball", quantity=4, image="products/test.png")

    def order(self):
        return Order.objects.create(user=self.user, name="Shopper", email=self.user.email, phone="9800000000", flat="1", street="Road", city="Kathmandu", region="Bagmati", postal_code="44600", method="cod", total="51.00")

    def test_cart_and_wishlist_unique_and_positive(self):
        CartItem.objects.create(user=self.user, product=self.product)
        WishlistItem.objects.create(user=self.user, product=self.product)
        for model in [CartItem, WishlistItem]:
            with self.subTest(model=model.__name__), self.assertRaises(IntegrityError), transaction.atomic():
                model.objects.create(user=self.user, product=self.product)
        CartItem.objects.all().delete()
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.create(user=self.user, product=self.product, quantity=0)

    def test_product_deletion_preserves_order_snapshot(self):
        order = self.order()
        item = OrderItem.objects.create(order=order, product=self.product, name=self.product.name, image=self.product.image.name, unit_price="25.50", quantity=2)
        CartItem.objects.create(user=self.user, product=self.product)
        WishlistItem.objects.create(user=self.user, product=self.product)
        self.product.delete()
        item.refresh_from_db()
        self.assertIsNone(item.product_id)
        self.assertEqual(item.name, "Ball")
        self.assertEqual(str(item.subtotal), "51.00")
        self.assertFalse(CartItem.objects.exists())
        self.assertFalse(WishlistItem.objects.exists())

    def test_order_statuses_are_database_constrained(self):
        order = self.order()
        for field in ["fulfillment_status", "payment_status", "method"]:
            with self.subTest(field=field), self.assertRaises(IntegrityError), transaction.atomic():
                Order.objects.filter(pk=order.pk).update(**{field: "forged"})

    def test_payment_reference_uniqueness_and_positive_amount(self):
        Payment.objects.create(user=self.user, pidx="unique-provider-reference", amount_paisa=1000)
        for data in [{"pidx": "unique-provider-reference", "amount_paisa": 1000}, {"pidx": "other", "amount_paisa": 0}]:
            with self.subTest(data=data), self.assertRaises(IntegrityError), transaction.atomic():
                Payment.objects.create(user=self.user, **data)

    def test_user_deletion_cascades_commerce(self):
        order = self.order()
        OrderItem.objects.create(order=order, product=self.product, name="Ball", unit_price="25.50", quantity=2)
        payment = Payment.objects.create(user=self.user, order=order, amount_paisa=5100)
        InventoryReservation.objects.create(payment=payment, product=self.product, quantity=2)
        self.user.delete()
        for model in [Order, OrderItem, Payment, InventoryReservation]:
            self.assertFalse(model.objects.exists())
        self.assertTrue(Product.objects.exists())
