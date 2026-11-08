from decimal import Decimal

from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import generics
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CartItem, WishlistItem, Order
from .serializers import CartInputSerializer, CartSerializer, CheckoutInputSerializer, FulfillmentInputSerializer, OrderQuerySerializer, OrderSerializer, QuantityInputSerializer, WishlistInputSerializer, WishlistSerializer
from .services import BasketService, CheckoutService, StaffOrderService


@method_decorator(never_cache, name='dispatch')
class BasketView(APIView):
    service_class = BasketService

    def serialize(self, serializer, instance):
        return serializer(instance, context={'request': self.request}).data


class CartView(BasketView):
    def get(self, request):
        items = list(CartItem.objects.filter(user=request.user).select_related('product__category'))
        total = sum((i.product.price * i.quantity for i in items), Decimal('0.00'))
        return Response({'items': CartSerializer(items, many=True, context={'request': request}).data, 'count': len(items), 'total': format(total, '.2f')})

    def post(self, request):
        serializer = CartInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = self.service_class().add_cart(request.user, **serializer.validated_data)
        return Response(self.serialize(CartSerializer, item), status=201)


class CartDetailView(BasketView):
    def patch(self, request, pk):
        serializer = QuantityInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = self.service_class().update_cart(request.user, pk, **serializer.validated_data)
        return Response(self.serialize(CartSerializer, item))

    def delete(self, request, pk):
        self.service_class().remove(request.user, CartItem, pk)
        return Response(status=204)


class CartClearView(BasketView):
    def delete(self, request):
        self.service_class().remove(request.user, CartItem)
        return Response(status=204)


class WishlistView(BasketView):
    def get(self, request):
        items = list(WishlistItem.objects.filter(user=request.user).select_related('product__category'))
        return Response({'items': WishlistSerializer(items, many=True, context={'request': request}).data, 'count': len(items)})

    def post(self, request):
        serializer = WishlistInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = self.service_class().add_wishlist(request.user, **serializer.validated_data)
        return Response(self.serialize(WishlistSerializer, item), status=201)


class WishlistDetailView(BasketView):
    def delete(self, request, pk):
        self.service_class().remove(request.user, WishlistItem, pk)
        return Response(status=204)


class WishlistClearView(BasketView):
    def delete(self, request):
        self.service_class().remove(request.user, WishlistItem)
        return Response(status=204)


class CheckoutView(BasketView):
    service_class = CheckoutService

    def post(self, request):
        serializer = CheckoutInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = self.service_class().place_cod(request.user, serializer.validated_data)
        return Response(self.serialize(OrderSerializer, order), status=201)


@method_decorator(never_cache, name='dispatch')
class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


class OrderDetailView(OrderListView, generics.RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class AdminOrderListView(OrderListView):
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        filters = OrderQuerySerializer(data=self.request.query_params.dict())
        filters.is_valid(raise_exception=True)
        queryset = Order.objects.prefetch_related('items')
        if 'status' in filters.validated_data:
            queryset = queryset.filter(fulfillment_status=filters.validated_data['status'])
        return queryset


class AdminOrderDetailView(AdminOrderListView, generics.RetrieveAPIView):
    service_class = StaffOrderService

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def patch(self, request, pk):
        serializer = FulfillmentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = self.service_class().update(pk, serializer.validated_data['fulfillment_status'])
        return Response(OrderSerializer(order).data)

    def delete(self, request, pk):
        self.service_class().delete(pk)
        return Response(status=204)
