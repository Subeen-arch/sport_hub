from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Product
from .serializers import CategoryInputSerializer, CategorySerializer, ProductInputSerializer, ProductQuerySerializer, ProductSerializer
from .services import CatalogQueryService, CatalogService


class CategoryListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer
    query_service_class = CatalogQueryService

    def get_queryset(self):
        # Query flags are optional filters, not HTML checkboxes: an omitted flag
        # must not become False and hide featured/discounted products.
        filters = ProductQuerySerializer(data=self.request.query_params.dict())
        filters.is_valid(raise_exception=True)
        return self.query_service_class().products(filters.validated_data)


class ProductDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    queryset = Product.objects.select_related("category")
    serializer_class = ProductSerializer


class CatalogMutationMixin:
    service_class = CatalogService

    def serialize_product(self, product):
        return ProductSerializer(product, context={"request": self.request}).data


class AdminProductListView(CatalogMutationMixin, ProductListView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = ProductInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = self.service_class().save_product(serializer.validated_data)
        return Response(self.serialize_product(product), status=status.HTTP_201_CREATED)


class AdminProductDetailView(CatalogMutationMixin, ProductDetailView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        self.get_object()
        serializer = ProductInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = self.service_class().save_product(serializer.validated_data, pk=pk)
        return Response(self.serialize_product(product))

    def delete(self, request, pk):
        self.service_class().delete_product(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminCategoryListView(CatalogMutationMixin, CategoryListView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = CategoryInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(CategorySerializer(self.service_class().save_category(serializer.validated_data)).data, status=status.HTTP_201_CREATED)


class AdminCategoryDetailView(CatalogMutationMixin, generics.RetrieveAPIView):
    permission_classes = [IsAdminUser]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def patch(self, request, pk):
        serializer = CategoryInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(CategorySerializer(self.service_class().save_category(serializer.validated_data, pk)).data)

    def delete(self, request, pk):
        self.service_class().delete_category(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CatalogOptionsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"brands": list(Product.objects.exclude(brand="").order_by("brand").values_list("brand", flat=True).distinct())})
