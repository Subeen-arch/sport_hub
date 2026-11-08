from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .khalti import configured
from .models import Payment
from .payment_serializers import PaymentInputSerializer, PaymentSerializer, VerifyPaymentSerializer
from .payment_services import PaymentService


@method_decorator(never_cache, name='dispatch')
class PaymentConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'khalti_enabled': configured(), 'environment': settings.KHALTI_ENV})


@method_decorator(never_cache, name='dispatch')
class PaymentMutationView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'payments'
    service_class = PaymentService


class InitiatePaymentView(PaymentMutationView):
    def post(self, request):
        serializer = PaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = self.service_class().initiate(request.user, serializer.validated_data)
        return Response(PaymentSerializer(payment).data, status=201)


class VerifyPaymentView(PaymentMutationView):
    def post(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = self.service_class().verify(request.user, serializer.validated_data['pidx'])
        return Response(PaymentSerializer(payment).data)


@method_decorator(never_cache, name='dispatch')
class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).select_related('order').prefetch_related('order__items')


class PaymentDetailView(PaymentListView, generics.RetrieveAPIView):
    lookup_field = 'purchase_order_id'
    lookup_url_kwarg = 'attempt'

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)
