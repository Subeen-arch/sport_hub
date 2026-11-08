from rest_framework import serializers
from common.serializers import StrictSerializer
from .serializers import CheckoutInputSerializer, OrderSerializer
from .khalti import valid_payment_url
from .models import Payment


class PaymentInputSerializer(CheckoutInputSerializer):
    request_key = serializers.UUIDField()


class VerifyPaymentSerializer(StrictSerializer):
    pidx = serializers.RegexField(r'\A[A-Za-z0-9_-]{1,100}\Z')


class PaymentSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='purchase_order_id', read_only=True)
    order = OrderSerializer(read_only=True)
    payment_url = serializers.SerializerMethodField()
    retry_allowed = serializers.SerializerMethodField()

    def get_payment_url(self, payment):
        from django.utils import timezone
        if payment.needs_review or payment.status not in {Payment.Status.INITIATED, Payment.Status.PENDING}:
            return ''
        if not payment.expires_at or payment.expires_at <= timezone.now():
            return ''
        return payment.payment_url if valid_payment_url(payment.payment_url, payment.pidx, payment.environment) else ''

    def get_retry_allowed(self, payment):
        return not payment.needs_review and not payment.settled_at and payment.status in {Payment.Status.FAILED, Payment.Status.CANCELED, Payment.Status.EXPIRED, Payment.Status.REFUNDED}

    class Meta:
        model = Payment
        fields = ['id', 'pidx', 'environment', 'status', 'provider_status', 'amount_paisa', 'payment_url', 'expires_at', 'needs_review', 'failure_code', 'retry_allowed', 'order', 'created_at']
        read_only_fields = fields
