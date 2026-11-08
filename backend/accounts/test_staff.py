from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

from django.core.cache import cache
from django.db import connections, close_old_connections
from django.test import TestCase, TransactionTestCase
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from catalog.models import Category, Product
from commerce.models import CartItem, WishlistItem, Order, Payment, InventoryReservation
from commerce.services import CheckoutService
from commerce.test_api import delivery
from support.models import ContactMessage
from .models import User
from .staff_services import StaffAccountService


class StaffApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.staff = User.objects.create_user(username='coach', email='coach@example.com', is_staff=True)
        self.customer = User.objects.create_user(username='runner', email='runner@example.com')
        self.client = APIClient(enforce_csrf_checks=True)
        self.authorize(self.staff)

    def authorize(self, user):
        self.client.force_login(user)
        self.client.credentials(HTTP_X_CSRFTOKEN=self.client.get('/api/auth/csrf/').data['csrfToken'])

    def order(self):
        product = Product.objects.create(name='Ball', category=Category.objects.create(name='Balls'), details='Ball', original_price='10', quantity=3, image='products/test.png')
        cart = CartItem.objects.create(user=self.customer, product=product)
        return CheckoutService().place_cod(self.customer, delivery([cart.pk]))

    def test_all_staff_resources_reject_customers_and_guests(self):
        for user in [self.customer, None]:
            if user:
                self.authorize(user)
            else:
                self.client.logout()
            for path in ['/api/admin/dashboard/', '/api/admin/users/', '/api/admin/accounts/', '/api/admin/messages/', '/api/admin/orders/', '/api/admin/users/1/', '/api/admin/accounts/1/', '/api/admin/messages/1/', '/api/admin/orders/1/']:
                for method in ['get', 'post', 'patch', 'delete']:
                    with self.subTest(path=path, method=method):
                        self.assertEqual(getattr(self.client, method)(path).status_code, 403)

    def test_dashboard_uses_actual_order_values(self):
        empty = self.client.get('/api/admin/dashboard/')
        self.assertEqual(empty.data['order_count'], 0)
        self.assertEqual(empty.data['pending_total'], '0.00')
        self.assertEqual(empty.data['admin_count'], 1)
        self.assertEqual(empty.data['customer_count'], 1)
        order = self.order()
        summary = self.client.get('/api/admin/dashboard/').data
        self.assertEqual(summary['order_count'], 1)
        self.assertEqual(summary['pending_total'], '10.00')
        self.assertEqual(summary['completed_total'], '0.00')
        self.client.patch(f'/api/admin/orders/{order.pk}/', {'fulfillment_status': 'completed'}, format='json')
        self.assertEqual(self.client.get('/api/admin/dashboard/').data['completed_total'], '10.00')

    def test_order_status_and_payment_boundaries(self):
        order = self.order()
        path = f'/api/admin/orders/{order.pk}/'
        self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.client.patch(path, {'payment_status': 'paid'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(path, {'fulfillment_status': 'bad'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(path, {'fulfillment_status': 'Dispatched'}, format='json').status_code, 200)
        self.assertEqual(self.client.get('/api/admin/orders/?status=pending').data['count'], 0)
        self.assertEqual(self.client.get('/api/admin/orders/?status=Dispatched').data['count'], 1)
        completed = self.client.patch(path, {'fulfillment_status': 'completed'}, format='json')
        self.assertEqual(completed.data['payment_status'], 'paid')
        self.assertEqual(self.client.patch(path, {'fulfillment_status': 'pending'}, format='json').status_code, 400)
        Order.objects.filter(pk=order.pk).update(method='khalti', fulfillment_status='pending', payment_status='pending')
        self.assertEqual(self.client.patch(path, {'fulfillment_status': 'completed'}, format='json').data['payment_status'], 'pending')
        self.assertEqual(self.client.delete(path).status_code, 204)
        self.assertEqual(Product.objects.get().quantity, 2)

    def test_staff_creation_validation_and_session_preservation(self):
        data = dict(username='newcoach', name='New Coach', email='NEW@example.com', password='Summit!8426River', password_confirm='Summit!8426River')
        for bad in [{'is_superuser': True}, {'password_confirm': 'different'}, {'password': 'short', 'password_confirm': 'short'}, {'username': 'coach'}, {'email': 'COACH@example.com'}]:
            with self.subTest(bad=bad):
                self.assertEqual(self.client.post('/api/admin/accounts/', {**data, **bad}, format='json').status_code, 400)
        result = self.client.post('/api/admin/accounts/', data, format='json')
        self.assertEqual(result.status_code, 201, result.data)
        self.assertNotIn('password', result.data)
        created = User.objects.get(pk=result.data['id'])
        self.assertTrue(created.is_staff)
        self.assertFalse(created.is_superuser)
        self.assertTrue(created.check_password(data['password']))
        self.assertEqual(created.email, 'new@example.com')
        self.assertEqual(self.client.get('/api/auth/me/').data['id'], self.staff.pk)
        self.assertEqual(self.client.get('/api/admin/accounts/').data['count'], 2)

    def test_staff_delete_self_role_boundary_and_customer_cascade(self):
        self.assertEqual(self.client.delete(f'/api/admin/accounts/{self.staff.pk}/').status_code, 400)
        self.assertEqual(self.client.delete(f'/api/admin/users/{self.staff.pk}/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/admin/accounts/{self.customer.pk}/').status_code, 404)
        order = self.order()
        product = Product.objects.get()
        CartItem.objects.create(user=self.customer, product=product)
        WishlistItem.objects.create(user=self.customer, product=product)
        ContactMessage.objects.create(user=self.customer, name='Runner', email=self.customer.email, phone='9812345678', message='Hi')
        Payment.objects.create(user=self.customer, order=order, amount_paisa=1000)
        self.assertEqual(self.client.delete(f'/api/admin/users/{self.customer.pk}/').status_code, 204)
        for model in [CartItem, WishlistItem, Order, Payment, ContactMessage]:
            self.assertFalse(model.objects.exists())
        self.assertTrue(Product.objects.exists())
        second = User.objects.create_user(username='second', email='second@example.com', is_staff=True)
        self.assertEqual(self.client.delete(f'/api/admin/accounts/{second.pk}/').status_code, 204)

    def test_active_reservations_block_account_deletion(self):
        self.order()
        payment = Payment.objects.create(user=self.customer, amount_paisa=1000)
        InventoryReservation.objects.create(payment=payment, product=Product.objects.get(), quantity=1)
        self.assertEqual(self.client.delete(f'/api/admin/users/{self.customer.pk}/').status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.customer.pk).exists())

    def test_messages_listing_deletion_and_csrf(self):
        message = ContactMessage.objects.create(name='Guest', email='guest@example.com', phone='9812345678', message='Question')
        self.assertEqual(self.client.get('/api/admin/messages/').data['results'][0]['message'], 'Question')
        self.client.credentials()
        self.assertEqual(self.client.delete(f'/api/admin/messages/{message.pk}/').status_code, 403)
        self.authorize(self.staff)
        self.assertEqual(self.client.delete(f'/api/admin/messages/{message.pk}/').status_code, 204)
        self.assertEqual(self.client.get('/api/admin/messages/').data['count'], 0)


class StaffConcurrencyTests(TransactionTestCase):
    def test_concurrent_staff_deletion_keeps_one_active_account(self):
        staff = [User.objects.create_user(username=f'coach{i}', email=f'coach{i}@example.com', is_staff=True) for i in range(2)]
        barrier = Barrier(2)
        def remove_other(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    StaffAccountService(SimpleNamespace(user=staff[index])).delete_user(staff[1 - index].pk, staff=True)
                    return 'deleted'
                except PermissionDenied:
                    return 'denied'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(remove_other, range(2)))
        self.assertCountEqual(result, ['deleted', 'denied'])
        self.assertEqual(User.objects.filter(is_staff=True, is_active=True).count(), 1)
