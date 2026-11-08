from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from accounts.models import User
from catalog.models import Product
from catalog.services import CatalogService
from .models import CartItem, WishlistItem, Order, OrderItem, Payment


class BasketService:
    """Catalog lock first, then owner: shared lock order with checkout and staff deletion."""

    def lock_owner(self, user):
        CatalogService()._lock_catalog()
        return get_object_or_404(User.objects.select_for_update(), pk=user.pk, is_active=True)

    def available_stock(self, product):
        reserved = product.reservations.filter(status='active').aggregate(total=Sum('quantity'))['total'] or 0
        return max(0, product.quantity - reserved)

    def assert_no_payment(self, user, cart_ids):
        from .payment_services import PaymentConflict
        attempts = Payment.objects.filter(user=user).filter(Q(reservations__status='active') | Q(needs_review=True) | Q(status__in=['Initiated', 'Pending'])).distinct()
        for payment in attempts:
            if set(payment.cart_item_ids).intersection(cart_ids):
                raise PaymentConflict({'detail': 'These cart items have an unresolved payment. Check that payment before changing them or paying again.', 'payment_id': str(payment.purchase_order_id)})

    def validate_stock(self, product, quantity):
        available = self.available_stock(product)
        if quantity < 1 or quantity > available:
            raise ValidationError({'quantity': [f'{product.name}: only {available} units are available.']})

    @transaction.atomic
    def add_cart(self, user, product_id, quantity):
        self.lock_owner(user)
        product = get_object_or_404(Product.objects.select_for_update(), pk=product_id)
        if CartItem.objects.filter(user=user, product=product).exists():
            raise ValidationError({'detail': 'This product is already in your cart. Update its quantity there.'})
        self.validate_stock(product, quantity)
        item = CartItem.objects.create(user=user, product=product, quantity=quantity)
        WishlistItem.objects.filter(user=user, product=product).delete()
        return item

    @transaction.atomic
    def update_cart(self, user, pk, quantity):
        self.lock_owner(user)
        item = get_object_or_404(CartItem.objects.select_for_update(), user=user, pk=pk)
        self.assert_no_payment(user, [item.pk])
        product = get_object_or_404(Product.objects.select_for_update(), pk=item.product_id)
        self.validate_stock(product, quantity)
        item.quantity = quantity
        item.save(update_fields=['quantity'])
        return item

    @transaction.atomic
    def add_wishlist(self, user, product_id):
        self.lock_owner(user)
        product = get_object_or_404(Product, pk=product_id)
        if CartItem.objects.filter(user=user, product=product).exists():
            raise ValidationError({'detail': 'This product is already in your cart.'})
        if WishlistItem.objects.filter(user=user, product=product).exists():
            raise ValidationError({'detail': 'This product is already in your wishlist.'})
        return WishlistItem.objects.create(user=user, product=product)

    @transaction.atomic
    def remove(self, user, model, pk=None):
        self.lock_owner(user)
        queryset = model.objects.filter(user=user)
        if model is CartItem:
            self.assert_no_payment(user, list(queryset.filter(pk=pk).values_list('pk', flat=True)) if pk is not None else list(queryset.values_list('pk', flat=True)))
        if pk is not None:
            get_object_or_404(queryset, pk=pk).delete()
        else:
            queryset.delete()


class CheckoutService(BasketService):
    @transaction.atomic
    def place_cod(self, user, data):
        self.lock_owner(user)
        selected = data['cart_item_ids']
        self.assert_no_payment(user, selected)
        if not selected or len(selected) != len(set(selected)):
            raise ValidationError({'cart_item_ids': ['Select distinct cart items.']})
        items = list(CartItem.objects.select_for_update().filter(user=user, pk__in=selected).order_by('product_id'))
        if len(items) != len(selected):
            raise ValidationError({'cart_item_ids': ['Some selected items are missing from your cart. Refresh your cart and select again.']})
        products = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=[i.product_id for i in items]).order_by('pk')}
        total = Decimal('0.00')
        for item in items:
            product = products[item.product_id]
            self.validate_stock(product, item.quantity)
            total += product.price * item.quantity
        if total > Decimal('999999999999.99'):
            raise ValidationError({'detail': 'The order total is too large. Reduce the selected quantities.'})
        delivery = {key: value for key, value in data.items() if key != 'cart_item_ids'}
        order = Order.objects.create(user=user, method=Order.Method.COD, total=total, **delivery)
        for item in items:
            product = products[item.product_id]
            OrderItem.objects.create(order=order, product=product, name=product.name, image=product.image.name, unit_price=product.price, quantity=item.quantity)
            product.quantity -= item.quantity
            product.save(update_fields=['quantity', 'updated_at'])
        CartItem.objects.filter(user=user, pk__in=selected).delete()
        return order


class StaffOrderService:
    @transaction.atomic
    def update(self, pk, status):
        order = get_object_or_404(Order.objects.select_for_update(), pk=pk)
        if order.fulfillment_status == Order.Fulfillment.COMPLETED and status != order.fulfillment_status:
            raise ValidationError({'fulfillment_status': ['Completed orders cannot be reopened.']})
        order.fulfillment_status = status
        if order.method == Order.Method.COD and status == Order.Fulfillment.COMPLETED:
            order.payment_status = Order.PaymentStatus.PAID
        order.save(update_fields=['fulfillment_status', 'payment_status', 'updated_at'])
        return order

    @transaction.atomic
    def delete(self, pk):
        # Deleting a record is not a cancellation, stock adjustment or refund.
        order = get_object_or_404(Order.objects.select_for_update(), pk=pk)
        order.delete()
