from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MapEdge, MapNode, Shop


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'address', 'latitude', 'longitude', 'phone', 'rating', 'opening_hours', 'is_active']


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapNode
        fields = ['id', 'name', 'latitude', 'longitude']


class EdgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapEdge
        fields = ['id', 'from_node', 'to_node', 'road_name']
        validators = []

    def validate(self, attrs):
        start = attrs.get('from_node', getattr(self.instance, 'from_node', None))
        end = attrs.get('to_node', getattr(self.instance, 'to_node', None))
        if start and end:
            if start.pk == end.pk:
                raise serializers.ValidationError('A road must connect two different nodes.')
            duplicates = MapEdge.objects.filter(Q(from_node=start, to_node=end) | Q(from_node=end, to_node=start))
            if self.instance:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError('This road already exists.')
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError('The road could not be saved; its nodes or another road may have changed.')

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError('The road could not be saved; its nodes or another road may have changed.')


class PublicShops(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ShopSerializer
    pagination_class = None

    def get_queryset(self):
        search = self.request.query_params.get('search', '').strip()
        if len(search) > 100:
            raise serializers.ValidationError({'search': 'Ensure this value has at most 100 characters.'})
        return Shop.objects.filter(is_active=True).filter(Q(name__icontains=search) | Q(address__icontains=search))


class PublicGraph(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'nodes': NodeSerializer(MapNode.objects.all(), many=True).data,
                         'edges': EdgeSerializer(MapEdge.objects.all(), many=True).data})


class StaffList(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    pagination_class = None


class StaffDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]


class StaffShops(StaffList):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer


class StaffShop(StaffDetail):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer


class StaffNodes(StaffList):
    queryset = MapNode.objects.all()
    serializer_class = NodeSerializer


class StaffNode(StaffDetail):
    queryset = MapNode.objects.all()
    serializer_class = NodeSerializer


class StaffEdges(StaffList):
    queryset = MapEdge.objects.all()
    serializer_class = EdgeSerializer


class StaffEdge(StaffDetail):
    queryset = MapEdge.objects.all()
    serializer_class = EdgeSerializer
