from rest_framework import serializers
from common.serializers import StrictSerializer
from catalog.serializers import ProductSerializer
from .models import CartItem, WishlistItem, Order, OrderItem


class QuantityInputSerializer(StrictSerializer):
    quantity = serializers.IntegerField(min_value=1, max_value=2147483647)


class CartInputSerializer(QuantityInputSerializer):
    product_id = serializers.IntegerField(min_value=1)


class WishlistInputSerializer(StrictSerializer):
    product_id = serializers.IntegerField(min_value=1)


class CartSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    subtotal = serializers.SerializerMethodField()

    def get_subtotal(self, item):
        return format(item.product.price * item.quantity, '.2f')

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'subtotal']


class WishlistSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = ['id', 'product']


class CheckoutInputSerializer(StrictSerializer):
    cart_item_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False, max_length=100)
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField(max_length=254)
    phone = serializers.RegexField(r'\A[0-9]{10}\Z', max_length=10)
    country_code = serializers.ChoiceField(choices=['+977', '+91'])
    flat = serializers.CharField(max_length=100)
    street = serializers.CharField(max_length=250)
    city = serializers.CharField(max_length=100)
    region = serializers.CharField(max_length=100)
    postal_code = serializers.RegexField(r'\A[A-Za-z0-9][A-Za-z0-9 -]{0,19}\Z', max_length=20)
    country = serializers.CharField(max_length=100)

    def validate_cart_item_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError('Select each cart item only once.')
        return value

    def validate_email(self, value):
        return value.lower()


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=24, decimal_places=2, read_only=True)
    image = serializers.SerializerMethodField()

    def get_image(self, item):
        if not item.image:
            return ''
        from django.core.files.storage import default_storage
        return default_storage.url(item.image)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'name', 'image', 'unit_price', 'quantity', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'reference', 'name', 'email', 'phone', 'country_code', 'flat', 'street', 'city', 'region', 'postal_code', 'country', 'method', 'fulfillment_status', 'payment_status', 'total', 'currency', 'transaction_id', 'payment_ref', 'created_at', 'items']
        read_only_fields = fields


class FulfillmentInputSerializer(StrictSerializer):
    fulfillment_status = serializers.ChoiceField(choices=Order.Fulfillment.choices)


class OrderQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Fulfillment.choices, required=False)
