from decimal import Decimal
import re

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import APIException, ValidationError

from catalog.models import Product
from catalog.services import CatalogService
from .models import CartItem, InventoryReservation, Order, OrderItem, Payment
from .services import BasketService
from .khalti import GatewayError, KhaltiClient, valid_payment_url


class PaymentConflict(APIException):
    status_code = 409


class PaymentService(BasketService):
    client_class = KhaltiClient
    terminal = {Payment.Status.FAILED, Payment.Status.CANCELED, Payment.Status.EXPIRED, Payment.Status.REFUNDED}

    def initiate(self, user, data):
        client = self.client_class()
        payment, created = self.prepare(user, data)
        if not created:
            return payment
        # The intent and reservations are durable before contacting the provider.
        # Never retry this POST after a timeout or hold database locks over HTTP.
        try:
            response = client.initiate(payment)
        except GatewayError as exc:
            return self.initiation_error(payment.pk, exc)
        return self.record_initiation(payment.pk, response)

    @transaction.atomic
    def prepare(self, user, data):
        self.lock_owner(user)
        request_key = data['request_key']
        original = {key: value for key, value in data.items() if key != 'request_key'}
        original['cart_item_ids'] = sorted(original['cart_item_ids'])
        previous = Payment.objects.filter(request_key=request_key).first()
        if previous:
            if previous.user_id != user.pk or previous.checkout_snapshot.get('input') != original:
                raise ValidationError({'detail': 'This payment request identifier has already been used. Review your payments before starting another attempt.'})
            return previous, False
        selected = original['cart_item_ids']
        self.assert_no_payment(user, selected)
        items = list(CartItem.objects.select_for_update().filter(user=user, pk__in=selected).select_related('product').order_by('product_id'))
        if not selected or len(items) != len(selected) or len(selected) != len(set(selected)):
            raise ValidationError({'cart_item_ids': ['Some selected cart items are missing. Return to your cart and select again.']})
        total = Decimal('0.00')
        lines = []
        for item in items:
            self.validate_stock(item.product, item.quantity)
            total += item.product.price * item.quantity
            lines.append({'cart_id': item.pk, 'cart_created_at': item.created_at.isoformat(), 'product_id': item.product_id, 'name': item.product.name, 'image': item.product.image.name, 'unit_price': str(item.product.price), 'quantity': item.quantity})
        if total < Decimal('10.00') or total > Decimal('999999999999.99'):
            raise ValidationError({'detail': 'Khalti orders must total at least NPR 10 and fit within the order limit. Use cash on delivery or change your cart.'})
        payment = Payment.objects.create(user=user, request_key=request_key, environment=settings.KHALTI_ENV, amount_paisa=int(total * 100),
                                         cart_item_ids=selected, checkout_snapshot={'input': original, 'delivery': {key: value for key, value in original.items() if key != 'cart_item_ids'}, 'lines': lines})
        InventoryReservation.objects.bulk_create([InventoryReservation(payment=payment, product_id=line['product_id'], quantity=line['quantity']) for line in lines])
        return payment, True

    def lock_payment(self, pk):
        CatalogService()._lock_catalog()
        return Payment.objects.select_for_update().get(pk=pk)

    @transaction.atomic
    def initiation_error(self, pk, error):
        payment = self.lock_payment(pk)
        payment.failure_code = error.code if error.definitive else 'initiation_unknown'
        payment.needs_review = not error.definitive
        if error.definitive:
            payment.status = Payment.Status.FAILED
            payment.reservations.filter(status='active').update(status='released')
        payment.save()
        return payment

    @transaction.atomic
    def record_initiation(self, pk, response):
        payment = self.lock_payment(pk)
        pidx = response.get('pidx')
        if not isinstance(pidx, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', pidx) or Payment.objects.exclude(pk=pk).filter(pidx=pidx).exists():
            payment.needs_review = True
            payment.failure_code = 'invalid_initiation'
            payment.save()
            return payment
        # Keep a valid provider identifier for lookup even if redirect data is bad.
        payment.pidx = pidx
        expires = response.get('expires_at')
        try:
            expires = parse_datetime(expires) if isinstance(expires, str) else None
        except (ValueError, TypeError):
            expires = None
        if not expires or timezone.is_naive(expires) or expires <= timezone.now() or not valid_payment_url(response.get('payment_url'), pidx, payment.environment):
            payment.needs_review = True
            payment.failure_code = 'invalid_initiation'
        else:
            payment.payment_url = response['payment_url']
            payment.expires_at = expires
        payment.save()
        return payment

    def verify(self, user, pidx):
        payment = get_object_or_404(Payment, user=user, pidx=pidx)
        return self.reconcile(payment)

    def reconcile(self, payment):
        client = self.client_class(environment=payment.environment)
        try:
            response = client.lookup(payment.pidx)
        except GatewayError as exc:
            # A lookup outage cannot prove cancellation or expiry.
            from .khalti import PaymentUnavailable
            raise PaymentUnavailable('Payment verification is unavailable. Check again shortly; do not pay again while the result is unknown.') from exc
        return self.apply_lookup(payment.pk, response)

    def review(self, payment, code):
        payment.needs_review = True
        payment.failure_code = code
        payment.save()
        return payment

    @transaction.atomic
    def apply_lookup(self, pk, response):
        payment = self.lock_payment(pk)
        status = response.get('status')
        if status == 'Partially Refunded':
            status = Payment.Status.PARTIALLY_REFUNDED
        # Lookup does not promise a purchase_order_id field. The pidx was bound
        # to our UUID on initiation. If a purchase reference is supplied, check it.
        if (response.get('pidx') != payment.pidx or type(response.get('total_amount')) is not int
                or response['total_amount'] != payment.amount_paisa
                or ('purchase_order_id' in response and str(response['purchase_order_id']) != str(payment.purchase_order_id))):
            return self.review(payment, 'verification_mismatch')
        if status not in Payment.Status.values:
            return self.review(payment, 'unknown_status')
        payment.provider_status = status
        transaction_id = response.get('transaction_id')
        if transaction_id is not None and (not isinstance(transaction_id, str) or len(transaction_id) > 100):
            return self.review(payment, 'invalid_transaction')
        if status == Payment.Status.COMPLETED and (not transaction_id or response.get('refunded') is not False):
            return self.review(payment, 'invalid_completion')
        if transaction_id:
            if payment.khalti_transaction_id and payment.khalti_transaction_id != transaction_id:
                return self.review(payment, 'transaction_mismatch')
            if Payment.objects.exclude(pk=pk).filter(khalti_transaction_id=transaction_id).exists():
                return self.review(payment, 'duplicate_transaction')
            payment.khalti_transaction_id = transaction_id

        # Never regress a settled/refunded ledger on a stale Pending/Completed lookup.
        if payment.settled_at:
            if status in {Payment.Status.REFUNDED, Payment.Status.PARTIALLY_REFUNDED}:
                if payment.status != Payment.Status.REFUNDED:
                    payment.status = status
                    if payment.order_id:
                        Order.objects.filter(pk=payment.order_id).update(payment_status='refunded' if status == Payment.Status.REFUNDED else 'partially_refunded')
                    payment.needs_review = status == Payment.Status.PARTIALLY_REFUNDED
                    payment.failure_code = 'partial_refund' if payment.needs_review else ''
            elif status != Payment.Status.COMPLETED:
                return self.review(payment, 'status_conflict')
            if not payment.order_id:
                return self.review(payment, 'order_removed')
            payment.save()
            return payment

        if payment.status == Payment.Status.PARTIALLY_REFUNDED and status != Payment.Status.REFUNDED:
            return self.review(payment, 'partial_refund')

        if status == Payment.Status.COMPLETED:
            reservations = list(payment.reservations.select_for_update().filter(status='active').order_by('product_id'))
            lines = payment.checkout_snapshot.get('lines', [])
            if not lines or len(reservations) != len(lines):
                return self.review(payment, 'reservation_missing')
            products = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=[r.product_id for r in reservations])}
            expected = {line['product_id']: line['quantity'] for line in lines}
            if any(r.product_id not in products or expected.get(r.product_id) != r.quantity or products[r.product_id].quantity < r.quantity for r in reservations):
                return self.review(payment, 'stock_conflict')
            total = sum((Decimal(line['unit_price']) * line['quantity'] for line in lines), Decimal('0.00'))
            if total * 100 != payment.amount_paisa:
                return self.review(payment, 'snapshot_mismatch')
            order = Order.objects.create(user_id=payment.user_id, method=Order.Method.KHALTI, payment_status=Order.PaymentStatus.PAID,
                                         total=total, transaction_id=transaction_id, payment_ref=payment.pidx, **payment.checkout_snapshot['delivery'])
            for line in lines:
                product = products[line['product_id']]
                OrderItem.objects.create(order=order, product=product, name=line['name'], image=line['image'], unit_price=Decimal(line['unit_price']), quantity=line['quantity'])
                product.quantity -= line['quantity']
                product.save(update_fields=['quantity', 'updated_at'])
                # Do not erase a later/replaced/changed cart row.
                CartItem.objects.filter(user_id=payment.user_id, pk=line['cart_id'], product_id=product.pk,
                                        quantity=line['quantity'], created_at=line['cart_created_at']).delete()
            payment.reservations.filter(status='active').update(status='consumed')
            payment.order = order
            payment.settled_at = timezone.now()
            payment.status = Payment.Status.COMPLETED
            payment.needs_review = False
            payment.failure_code = ''
        elif status in self.terminal:
            payment.status = status
            payment.needs_review = False
            payment.failure_code = ''
            payment.reservations.filter(status='active').update(status='released')
        elif status == Payment.Status.PARTIALLY_REFUNDED:
            payment.status = status
            return self.review(payment, 'partial_refund')
        elif payment.status not in self.terminal:
            payment.status = status
            # A validated Pending lookup resolves malformed redirect data, but
            # it never releases stock merely because the local clock expired.
            payment.needs_review = False
            payment.failure_code = ''
        payment.save()
        return payment
