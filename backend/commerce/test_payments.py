"""Gateway contract tests. No real payment or operational records are created."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import Mock, patch
from uuid import uuid4

import requests
from django.core.cache import cache
from django.db import close_old_connections, connections
from django.test import TestCase, TransactionTestCase, SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import APIException
from rest_framework.test import APIClient

from accounts.models import User
from catalog.models import Category, Product
from .khalti import GatewayError, KhaltiClient, PaymentUnavailable, valid_payment_url
from .models import CartItem, InventoryReservation, Order, OrderItem, Payment
from .payment_services import PaymentService
from .services import CheckoutService
from .test_api import delivery


def initiated(payment):
    pidx = payment.purchase_order_id.hex
    return {'pidx': pidx, 'payment_url': f'https://test-pay.khalti.com/?pidx={pidx}',
            'expires_at': (timezone.now() + timedelta(minutes=30)).isoformat()}


def lookup(payment, status='Completed', **changes):
    return {'pidx': payment.pidx, 'total_amount': payment.amount_paisa, 'status': status,
            'transaction_id': f'txn_{payment.pidx}' if status in {'Completed', 'Refunded', 'Partially Refunded'} else None,
            'refunded': status == 'Refunded', **changes}


@override_settings(KHALTI_SECRET_KEY='test-only-key', KHALTI_ENV='sandbox', FRONTEND_URL='http://localhost:5173')
class PaymentApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='payer', email='payer@example.com')
        self.other = User.objects.create_user(username='other', email='other@example.com')
        category = Category.objects.create(name='Balls')
        self.product = Product.objects.create(name='Match ball', category=category, details='Ball', original_price='99.95', discount_percent=10, quantity=5, image='products/ball.png')
        self.cart = CartItem.objects.create(user=self.user, product=self.product, quantity=2)
        self.payload = {**delivery([self.cart.pk]), 'request_key': str(uuid4())}
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        self.client.credentials(HTTP_X_CSRFTOKEN=self.client.get('/api/auth/csrf/').data['csrfToken'])
        initiate_patch = patch('commerce.khalti.KhaltiClient.initiate', side_effect=initiated)
        self.initiate_mock = initiate_patch.start()
        self.addCleanup(initiate_patch.stop)
        lookup_patch = patch('commerce.khalti.KhaltiClient.lookup')
        self.lookup_mock = lookup_patch.start()
        self.addCleanup(lookup_patch.stop)

    def start(self, payload=None):
        return self.client.post('/api/payments/khalti/initiate/', payload or self.payload, format='json')

    def payment(self):
        response = self.start()
        self.assertEqual(response.status_code, 201, response.data)
        return Payment.objects.get(purchase_order_id=response.data['id'])

    def verify(self, payment, status='Completed', **changes):
        self.lookup_mock.return_value = lookup(payment, status, **changes)
        return self.client.post('/api/payments/khalti/verify/', {'pidx': payment.pidx}, format='json')

    def test_config_missing_credentials_fails_without_reserving_stock(self):
        with override_settings(KHALTI_SECRET_KEY=''):
            self.assertFalse(self.client.get('/api/payments/config/').data['khalti_enabled'])
            self.assertEqual(self.start().status_code, 503)
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(InventoryReservation.objects.exists())
        self.initiate_mock.assert_not_called()

    def test_authentication_csrf_and_owner_isolation(self):
        payment = self.payment()
        self.client.logout()
        self.assertEqual(self.start().status_code, 403)
        self.assertEqual(self.client.get('/api/payments/').status_code, 403)
        self.client.force_login(self.other)
        self.client.credentials()
        self.assertEqual(self.start().status_code, 403)
        self.client.credentials(HTTP_X_CSRFTOKEN=self.client.get('/api/auth/csrf/').data['csrfToken'])
        self.assertEqual(self.client.get(f'/api/payments/{payment.purchase_order_id}/').status_code, 404)
        self.assertEqual(self.verify(payment).status_code, 404)
        self.assertEqual(self.client.get('/api/payments/').data['count'], 0)
        self.assertEqual(self.start({**self.payload, 'request_key': str(uuid4())}).status_code, 400)
        self.lookup_mock.assert_not_called()

    def test_validation_and_server_pricing(self):
        for changes in [{'amount': 1}, {'user': self.other.pk}, {'status': 'Completed'}, {'request_key': 'bad'}, {'cart_item_ids': []}, {'cart_item_ids': [self.cart.pk, self.cart.pk]}, {'phone': 'bad'}]:
            with self.subTest(changes=changes):
                self.assertEqual(self.start({**self.payload, **changes}).status_code, 400)
        payment = self.payment()
        self.assertEqual(payment.amount_paisa, 17992)
        self.assertEqual(payment.checkout_snapshot['lines'][0]['unit_price'], '89.96')
        self.assertEqual(payment.reservations.get().quantity, 2)
        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.filter(pk=self.cart.pk).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 5)

    def test_minimum_amount_and_stock(self):
        self.product.original_price = Decimal('1.00')
        self.product.save()
        self.assertEqual(self.start().status_code, 400)
        self.product.original_price = Decimal('100.00')
        self.product.quantity = 1
        self.product.save()
        self.assertEqual(self.start().status_code, 400)
        self.assertFalse(Payment.objects.exists())

    def test_request_key_replay_and_unresolved_cart_conflict(self):
        payment = self.payment()
        self.assertEqual(self.start().data['id'], str(payment.purchase_order_id))
        self.initiate_mock.assert_called_once()
        self.assertEqual(self.start({**self.payload, 'city': 'Pokhara'}).status_code, 400)
        conflict = self.start({**self.payload, 'request_key': str(uuid4())})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(str(conflict.data['payment_id']), str(payment.purchase_order_id))
        self.assertEqual(self.client.post('/api/orders/checkout/', delivery([self.cart.pk]), format='json').status_code, 409)
        self.assertEqual(self.client.patch(f'/api/cart/{self.cart.pk}/', {'quantity': 1}, format='json').status_code, 409)
        self.assertEqual(self.client.delete('/api/cart/clear/').status_code, 409)

    def test_completed_lookup_creates_one_snapshot_order_and_preserves_unselected_cart(self):
        extra = Product.objects.create(name='Boots', category=self.product.category, details='Boots', original_price='30', quantity=1, image='products/boots.png')
        remaining = CartItem.objects.create(user=self.user, product=extra)
        payment = self.payment()
        Product.objects.filter(pk=self.product.pk).update(original_price='200', name='Renamed ball')
        first = self.verify(payment)
        self.assertEqual(first.status_code, 200, first.data)
        second = self.verify(payment)
        self.assertEqual(first.data['order']['id'], second.data['order']['id'])
        self.assertEqual(Order.objects.count(), 1)
        item = OrderItem.objects.get()
        self.assertEqual(item.name, 'Match ball')
        self.assertEqual(item.unit_price, Decimal('89.96'))
        self.assertEqual(Order.objects.get().payment_status, 'paid')
        self.assertEqual(list(CartItem.objects.values_list('pk', flat=True)), [remaining.pk])
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 3)
        self.assertEqual(payment.reservations.get().status, 'consumed')
        # Repeating an initiation after a lost response never creates another charge.
        self.assertEqual(self.start().data['order']['id'], first.data['order']['id'])
        self.initiate_mock.assert_called_once()

    def test_callback_fields_and_invalid_identifiers_cannot_forge_success(self):
        payment = self.payment()
        for body in [{'pidx': payment.pidx, 'status': 'Completed'}, {'pidx': '../bad'}, {'pidx': ''}, {'pidx': 'unknown'}]:
            self.assertIn(self.client.post('/api/payments/khalti/verify/', body, format='json').status_code, [400, 404])
        self.lookup_mock.assert_not_called()
        self.assertFalse(Order.objects.exists())

    def test_mismatched_or_malformed_lookup_retains_reservations(self):
        payment = self.payment()
        for changes in [{'total_amount': 1}, {'total_amount': '17992'}, {'pidx': 'other'}, {'purchase_order_id': str(uuid4())}, {'status': 'Surprise'}, {'transaction_id': None}, {'refunded': True}]:
            with self.subTest(changes=changes):
                result = self.verify(payment, **changes)
                self.assertTrue(result.data['needs_review'])
                self.assertFalse(result.data['retry_allowed'])
                self.assertEqual(result.data['payment_url'], '')
                self.assertIsNone(result.data['order'])
                self.assertEqual(payment.reservations.get().status, 'active')

    def test_pending_expired_clock_and_lookup_outage_do_not_release_stock(self):
        payment = self.payment()
        Payment.objects.filter(pk=payment.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        result = self.verify(payment, 'Pending')
        self.assertFalse(result.data['retry_allowed'])
        self.assertEqual(result.data['payment_url'], '')
        self.lookup_mock.side_effect = GatewayError('connection_error')
        self.assertEqual(self.client.post('/api/payments/khalti/verify/', {'pidx': payment.pidx}, format='json').status_code, 503)
        self.assertEqual(payment.reservations.get().status, 'active')
        self.assertFalse(Order.objects.exists())

    def test_provider_terminal_status_releases_stock_and_allows_new_attempt(self):
        for status in ['User canceled', 'Expired', 'Failed', 'Refunded']:
            with self.subTest(status=status):
                self.payload['request_key'] = str(uuid4())
                payment = self.payment()
                result = self.verify(payment, status)
                self.assertTrue(result.data['retry_allowed'])
                self.assertEqual(payment.reservations.get().status, 'released')
                self.assertTrue(CartItem.objects.filter(pk=self.cart.pk).exists())
                self.assertFalse(Order.objects.exists())

    def test_uncertain_initiation_stays_recoverable_and_blocks_new_charge(self):
        self.initiate_mock.side_effect = GatewayError('connection_error')
        payment = self.payment()
        self.assertTrue(payment.needs_review)
        self.assertIsNone(payment.pidx)
        self.assertEqual(payment.reservations.get().status, 'active')
        self.assertEqual(self.start().data['id'], str(payment.purchase_order_id))
        self.initiate_mock.assert_called_once()
        listing = self.client.get('/api/payments/')
        self.assertEqual(listing.data['count'], 1)
        self.assertIn('no-store', listing['Cache-Control'])

    def test_definitive_initiation_failure_releases_reservations(self):
        self.initiate_mock.side_effect = GatewayError('provider_error', definitive=True)
        result = self.start()
        self.assertEqual(result.data['status'], 'Failed')
        self.assertTrue(result.data['retry_allowed'])
        self.assertEqual(InventoryReservation.objects.get().status, 'released')

    def test_invalid_redirect_retains_pidx_for_safe_reconciliation(self):
        def bad_redirect(payment):
            return {**initiated(payment), 'payment_url': 'https://attacker.example/?pidx=forged'}
        self.initiate_mock.side_effect = bad_redirect
        payment = self.payment()
        self.assertTrue(payment.needs_review)
        self.assertTrue(payment.pidx)
        self.assertEqual(self.client.get(f'/api/payments/{payment.purchase_order_id}/').data['payment_url'], '')
        self.assertEqual(self.verify(payment).data['order']['payment_status'], 'paid')

    def test_persistence_failure_rolls_back_and_reverification_recovers(self):
        payment = self.payment()
        with patch('commerce.payment_services.OrderItem.objects.create', side_effect=RuntimeError('injected failure')):
            with self.assertRaises(RuntimeError):
                PaymentService().apply_lookup(payment.pk, lookup(payment))
        self.assertFalse(Order.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 5)
        self.assertEqual(payment.reservations.get().status, 'active')
        self.assertEqual(self.verify(payment).data['order']['payment_status'], 'paid')

    def test_refunds_and_stale_status_do_not_duplicate_or_regress_settlement(self):
        payment = self.payment()
        self.verify(payment)
        result = self.verify(payment, 'Partially Refunded')
        self.assertEqual(result.data['order']['payment_status'], 'partially_refunded')
        self.assertTrue(result.data['needs_review'])
        self.assertEqual(self.verify(payment).data['order']['payment_status'], 'partially_refunded')
        self.assertEqual(self.verify(payment, 'Refunded').data['order']['payment_status'], 'refunded')
        self.assertEqual(self.verify(payment).data['status'], 'Refunded')
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 3)

    def test_duplicate_transaction_reference_cannot_fulfill_second_payment(self):
        payment = self.payment()
        self.verify(payment)
        self.cart = CartItem.objects.create(user=self.user, product=self.product)
        self.payload = {**delivery([self.cart.pk]), 'request_key': str(uuid4())}
        second = self.payment()
        result = self.verify(second, transaction_id=f'txn_{payment.pidx}')
        self.assertEqual(result.data['failure_code'], 'duplicate_transaction')
        self.assertIsNone(result.data['order'])
        self.assertEqual(Order.objects.count(), 1)

    def test_deleted_or_replaced_cart_row_does_not_remove_new_items(self):
        payment = self.payment()
        self.cart.delete()
        replacement = CartItem.objects.create(user=self.user, product=self.product)
        self.verify(payment)
        self.assertTrue(CartItem.objects.filter(pk=replacement.pk).exists())


@override_settings(KHALTI_SECRET_KEY='test-only-key', KHALTI_ENV='sandbox', FRONTEND_URL='http://localhost:5173')
class PaymentConcurrencyTests(TransactionTestCase):
    def setUp(self):
        category = Category.objects.create(name='Balls')
        self.product = Product.objects.create(name='Last ball', category=category, details='Ball', original_price='10.00', quantity=1, image='products/ball.png')
        self.users = [User.objects.create_user(username=f'payer{i}', email=f'payer{i}@example.com') for i in range(2)]
        self.carts = [CartItem.objects.create(user=user, product=self.product) for user in self.users]

    def parallel(self, actions):
        barrier = Barrier(len(actions))
        def run(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    action()
                    return 'ok'
                except APIException:
                    return 'rejected'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_concurrent_verify_consumes_stock_once(self):
        with patch('commerce.khalti.KhaltiClient.initiate', side_effect=initiated):
            payment = PaymentService().initiate(self.users[0], {**delivery([self.carts[0].pk]), 'request_key': uuid4()})
        response = lookup(payment)
        result = self.parallel([lambda: PaymentService().apply_lookup(payment.pk, response) for _ in range(2)])
        self.assertEqual(result, ['ok', 'ok'])
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 0)

    def test_khalti_and_cod_cannot_reserve_or_buy_the_same_last_unit(self):
        with patch('commerce.khalti.KhaltiClient.initiate', side_effect=initiated):
            result = self.parallel([
                lambda: PaymentService().initiate(self.users[0], {**delivery([self.carts[0].pk]), 'request_key': uuid4()}),
                lambda: CheckoutService().place_cod(self.users[1], delivery([self.carts[1].pk])),
            ])
        self.assertCountEqual(result, ['ok', 'rejected'])
        self.assertEqual(Order.objects.count() + InventoryReservation.objects.filter(status='active').count(), 1)

    def test_concurrent_initiation_sends_one_provider_request(self):
        payload = {**delivery([self.carts[0].pk]), 'request_key': uuid4()}
        with patch('commerce.khalti.KhaltiClient.initiate', side_effect=initiated) as initiate_mock:
            result = self.parallel([lambda: PaymentService().initiate(self.users[0], payload) for _ in range(2)])
        self.assertEqual(result, ['ok', 'ok'])
        self.assertEqual(Payment.objects.count(), 1)
        initiate_mock.assert_called_once()


@override_settings(KHALTI_SECRET_KEY='test-only-key', KHALTI_ENV='sandbox', FRONTEND_URL='http://localhost:5173')
class KhaltiHttpTests(SimpleTestCase):
    @patch('commerce.khalti.requests.post')
    def test_provider_request_timeout_auth_and_no_redirects(self, post):
        post.return_value = Mock(status_code=200, json=Mock(return_value={'pidx': 'abc'}))
        KhaltiClient().lookup('abc')
        self.assertEqual(post.call_args.args[0], 'https://dev.khalti.com/api/v2/epayment/lookup/')
        self.assertEqual(post.call_args.kwargs['json'], {'pidx': 'abc'})
        self.assertEqual(post.call_args.kwargs['headers']['Authorization'], 'Key test-only-key')
        self.assertFalse(post.call_args.kwargs['allow_redirects'])
        self.assertEqual(post.call_args.kwargs['timeout'], (5, 15))
        post.side_effect = requests.Timeout()
        with self.assertRaises(GatewayError):
            KhaltiClient().lookup('abc')
        self.assertEqual(post.call_count, 2)

    @patch('commerce.khalti.requests.post')
    def test_lookup_http_400_terminal_status_is_verified_normally(self, post):
        for status in ['Expired', 'User canceled']:
            post.return_value = Mock(status_code=400, json=Mock(return_value={'status': status}))
            self.assertEqual(KhaltiClient().lookup('abc')['status'], status)
        post.return_value = Mock(status_code=401, json=Mock(return_value={'detail': 'invalid token'}))
        with self.assertRaises(GatewayError):
            KhaltiClient().lookup('abc')

    def test_redirect_allowlist_and_environment_separation(self):
        self.assertTrue(valid_payment_url('https://test-pay.khalti.com/?pidx=abc', 'abc', 'sandbox'))
        for url in ['http://test-pay.khalti.com/?pidx=abc', 'https://test-pay.khalti.com.evil.test/?pidx=abc', 'https://evil@test-pay.khalti.com/?pidx=abc', 'https://test-pay.khalti.com/?pidx=other', 'https://test-pay.khalti.com/?pidx=abc&pidx=other', 'javascript:alert(1)']:
            self.assertFalse(valid_payment_url(url, 'abc', 'sandbox'))
        with self.assertRaises(PaymentUnavailable):
            KhaltiClient(environment='live')
