from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.core.cache import cache
from django.db import connections, close_old_connections
from django.test import TestCase, TransactionTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from catalog.models import Category, Product
from .models import CartItem, WishlistItem, Order, OrderItem, Payment, InventoryReservation
from .services import BasketService, CheckoutService


def delivery(ids):
    return dict(cart_item_ids=ids, name='Runner', email='runner@example.com', phone='9812345678', country_code='+977', flat='12', street='Sports Road', city='Kathmandu', region='Bagmati', postal_code='44600', country='Nepal')


class CommerceApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='runner', email='runner@example.com')
        self.other = User.objects.create_user(username='other', email='other@example.com')
        self.category = Category.objects.create(name='Balls')
        self.ball = Product.objects.create(name='Match ball', category=self.category, details='Practice ball', original_price='99.95', discount_percent=10, quantity=5, image='products/ball.png')
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        self.csrf()

    def csrf(self):
        self.client.credentials(HTTP_X_CSRFTOKEN=self.client.get('/api/auth/csrf/').data['csrfToken'])

    def cart(self, user=None, product=None, quantity=1):
        return CartItem.objects.create(user=user or self.user, product=product or self.ball, quantity=quantity)

    def test_anonymous_and_csrf_protection(self):
        self.client.logout()
        for path in ['/api/cart/', '/api/wishlist/', '/api/orders/', '/api/orders/checkout/', '/api/cart/clear/', '/api/wishlist/clear/']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)
                self.assertEqual(self.client.post(path, {}, format='json').status_code, 403)
                self.assertEqual(self.client.delete(path).status_code, 403)
        self.client.force_login(self.user)
        self.client.credentials()
        self.assertEqual(self.client.post('/api/cart/', {'product_id': self.ball.pk, 'quantity': 1}, format='json').status_code, 403)

    def test_cart_ownership_update_clear_and_server_totals(self):
        foreign = self.cart(self.other)
        created = self.client.post('/api/cart/', {'product_id': self.ball.pk, 'quantity': 2}, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data['subtotal'], '179.92')
        self.assertEqual(self.client.get('/api/cart/').data['count'], 1)
        for method in ['patch', 'delete']:
            self.assertEqual(getattr(self.client, method)(f'/api/cart/{foreign.pk}/', {'quantity': 1}, format='json').status_code, 404)
        item_id = created.data['id']
        self.assertEqual(self.client.patch(f'/api/cart/{item_id}/', {'quantity': 3}, format='json').data['subtotal'], '269.88')
        self.assertEqual(self.client.get('/api/cart/').data['total'], '269.88')
        self.assertIn('no-store', self.client.get('/api/cart/')['Cache-Control'])
        self.assertEqual(self.client.delete('/api/cart/clear/').status_code, 204)
        self.assertEqual(list(CartItem.objects.values_list('pk', flat=True)), [foreign.pk])

    def test_cart_validation_duplicates_and_reservations(self):
        for bad in [{'quantity': 0}, {'quantity': -1}, {'quantity': 1.5}, {'quantity': 6}, {'price': '0.01'}, {'user': self.other.pk}, {'product_id': 9999}]:
            payload = {'product_id': self.ball.pk, 'quantity': 1, **bad}
            self.assertIn(self.client.post('/api/cart/', payload, format='json').status_code, [400, 404])
        payment = Payment.objects.create(user=self.other, amount_paisa=100)
        InventoryReservation.objects.create(payment=payment, product=self.ball, quantity=4)
        self.assertEqual(self.client.post('/api/cart/', {'product_id': self.ball.pk, 'quantity': 2}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/cart/', {'product_id': self.ball.pk, 'quantity': 1}, format='json').status_code, 201)
        self.assertEqual(self.client.post('/api/cart/', {'product_id': self.ball.pk, 'quantity': 1}, format='json').status_code, 400)
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 1)

    def test_wishlist_move_is_atomic_and_owner_scoped(self):
        foreign = WishlistItem.objects.create(user=self.other, product=self.ball)
        result = self.client.post('/api/wishlist/', {'product_id': self.ball.pk}, format='json')
        self.assertEqual(result.status_code, 201)
        self.assertEqual(self.client.get('/api/wishlist/').data['count'], 1)
        self.assertEqual(self.client.post('/api/wishlist/', {'product_id': self.ball.pk}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(f'/api/wishlist/{foreign.pk}/').status_code, 404)
        self.assertEqual(self.client.post('/api/cart/', {'product_id': self.ball.pk, 'quantity': 6}, format='json').status_code, 400)
        self.assertTrue(WishlistItem.objects.filter(pk=result.data['id']).exists())
        self.assertEqual(self.client.post('/api/cart/', {'product_id': self.ball.pk, 'quantity': 2}, format='json').status_code, 201)
        self.assertFalse(WishlistItem.objects.filter(pk=result.data['id']).exists())
        self.assertTrue(WishlistItem.objects.filter(pk=foreign.pk).exists())
        self.assertEqual(self.client.post('/api/wishlist/', {'product_id': self.ball.pk}, format='json').status_code, 400)
        self.assertEqual(self.client.delete('/api/wishlist/clear/').status_code, 204)
        self.assertTrue(WishlistItem.objects.filter(pk=foreign.pk).exists())

    def test_checkout_selected_only_snapshots_and_ownership(self):
        selected = self.cart(quantity=2)
        other_product = Product.objects.create(name='Boots', category=self.category, details='Boots', original_price='1000', quantity=1, image='products/boots.png')
        unselected = self.cart(product=other_product)
        result = self.client.post('/api/orders/checkout/', delivery([selected.pk]), format='json')
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.data['total'], '179.92')
        self.assertEqual(result.data['method'], 'cod')
        self.assertEqual(result.data['payment_status'], 'pending')
        self.assertEqual(len(result.data['items']), 1)
        self.ball.refresh_from_db()
        self.assertEqual(self.ball.quantity, 3)
        self.assertTrue(CartItem.objects.filter(pk=unselected.pk).exists())
        self.assertFalse(CartItem.objects.filter(pk=selected.pk).exists())
        self.assertEqual(self.client.post('/api/orders/checkout/', delivery([selected.pk]), format='json').status_code, 400)
        Product.objects.filter(pk=self.ball.pk).update(name='Renamed', original_price='500')
        self.ball.delete()
        detail = self.client.get(f"/api/orders/{result.data['id']}/")
        self.assertEqual(detail.data['items'][0]['name'], 'Match ball')
        self.assertEqual(detail.data['items'][0]['unit_price'], '89.96')
        self.assertIsNone(detail.data['items'][0]['product'])
        self.assertEqual(self.client.get('/api/orders/').data['count'], 1)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get('/api/orders/').data['count'], 0)
        self.assertEqual(self.client.get(f"/api/orders/{result.data['id']}/").status_code, 404)

    def test_checkout_rejects_invalid_selection_and_forged_fields(self):
        own = self.cart()
        foreign = self.cart(self.other)
        for changes in [{'cart_item_ids': []}, {'cart_item_ids': [own.pk, own.pk]}, {'cart_item_ids': [foreign.pk]}, {'cart_item_ids': [own.pk, 9999]}, {'total': '0.01'}, {'method': 'khalti'}, {'user': self.other.pk}, {'phone': '123'}, {'email': 'bad'}, {'flat': ' '}, {'postal_code': '<script>'}, {'country_code': '+1'}]:
            with self.subTest(changes=changes):
                self.assertEqual(self.client.post('/api/orders/checkout/', {**delivery([own.pk]), **changes}, format='json').status_code, 400)
        self.assertFalse(Order.objects.exists())
        self.assertEqual(CartItem.objects.count(), 2)
        self.ball.refresh_from_db()
        self.assertEqual(self.ball.quantity, 5)

    def test_checkout_rechecks_stock_and_reservations_without_partial_writes(self):
        selected = self.cart(quantity=2)
        Product.objects.filter(pk=self.ball.pk).update(quantity=1)
        self.assertEqual(self.client.post('/api/orders/checkout/', delivery([selected.pk]), format='json').status_code, 400)
        Product.objects.filter(pk=self.ball.pk).update(quantity=5)
        payment = Payment.objects.create(user=self.other, amount_paisa=100)
        InventoryReservation.objects.create(payment=payment, product=self.ball, quantity=4)
        self.assertEqual(self.client.post('/api/orders/checkout/', delivery([selected.pk]), format='json').status_code, 400)
        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.filter(pk=selected.pk).exists())

    def test_checkout_rolls_back_all_writes_on_storage_failure(self):
        first = self.cart(quantity=2)
        other = Product.objects.create(name='Boots', category=self.category, details='Boots', original_price='1000', quantity=2, image='products/boots.png')
        second = self.cart(product=other)
        original = OrderItem.objects.create
        calls = 0
        def fail_second(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError('Injected write failure')
            return original(**kwargs)
        with patch('commerce.services.OrderItem.objects.create', side_effect=fail_second), self.assertRaises(RuntimeError):
            CheckoutService().place_cod(self.user, delivery([first.pk, second.pk]))
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderItem.objects.exists())
        self.assertEqual(CartItem.objects.count(), 2)
        self.ball.refresh_from_db()
        self.assertEqual(self.ball.quantity, 5)


class CommerceConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Balls')
        self.product = Product.objects.create(name='Last ball', category=self.category, details='Only one', original_price=Decimal('10.00'), quantity=1, image='products/test.png')
        self.users = [User.objects.create_user(username=f'runner{i}', email=f'runner{i}@example.com') for i in range(2)]

    def parallel(self, actions):
        barrier = Barrier(len(actions))
        def run(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    action()
                    return 'ok'
                except ValidationError:
                    return 'rejected'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_simultaneous_checkouts_cannot_oversell(self):
        carts = [CartItem.objects.create(user=user, product=self.product) for user in self.users]
        result = self.parallel([lambda i=i: CheckoutService().place_cod(self.users[i], delivery([carts[i].pk])) for i in range(2)])
        self.assertCountEqual(result, ['ok', 'rejected'])
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(CartItem.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 0)

    def test_repeat_concurrent_checkout_creates_one_order(self):
        cart = CartItem.objects.create(user=self.users[0], product=self.product)
        result = self.parallel([lambda: CheckoutService().place_cod(self.users[0], delivery([cart.pk])) for _ in range(2)])
        self.assertCountEqual(result, ['ok', 'rejected'])
        self.assertEqual(Order.objects.count(), 1)

    def test_concurrent_cart_add_preserves_unique_item(self):
        result = self.parallel([lambda: BasketService().add_cart(self.users[0], self.product.pk, 1) for _ in range(2)])
        self.assertCountEqual(result, ['ok', 'rejected'])
        self.assertEqual(CartItem.objects.count(), 1)
