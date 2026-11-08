from io import BytesIO
import warnings

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers

from common.serializers import StrictSerializer
from .models import Category, Product


class RasterImageField(serializers.ImageField):
    """Decode and re-encode allowed raster content, discarding metadata/trailing data."""

    def to_internal_value(self, data):
        if getattr(data, "size", 0) > 2_000_000:
            raise serializers.ValidationError("Image must be no larger than 2 MB.")
        upload = super().to_internal_value(data)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                upload.seek(0)
                with Image.open(upload) as original:
                    if original.format not in {"JPEG", "PNG", "WEBP"}:
                        raise serializers.ValidationError("Use a JPEG, PNG or WebP image.")
                    if original.width * original.height > 20_000_000:
                        raise serializers.ValidationError("Image must contain no more than 20 million pixels.")
                    image_format = original.format
                    cleaned = ImageOps.exif_transpose(original)
                    cleaned = cleaned.convert("RGBA" if image_format != "JPEG" and "A" in cleaned.getbands() else "RGB")
                    output = BytesIO()
                    cleaned.save(output, format=image_format)
            if output.tell() > 2_000_000:
                raise serializers.ValidationError("The processed image exceeds 2 MB. Upload a smaller image.")
            extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[image_format]
            return ContentFile(output.getvalue(), name=f"upload.{extension}")
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning, ValueError) as exc:
            raise serializers.ValidationError("Upload a valid JPEG, PNG or WebP image.") from exc


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class CategoryInputSerializer(StrictSerializer):
    name = serializers.CharField(max_length=100)


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    stock_status = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "category", "category_name", "brand", "details", "original_price", "discount_percent", "price", "quantity", "featured", "image", "stock_status", "created_at", "updated_at"]
        read_only_fields = fields


class ProductInputSerializer(StrictSerializer):
    name = serializers.CharField(max_length=100)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    brand = serializers.CharField(max_length=100, allow_blank=True, required=False)
    details = serializers.CharField(max_length=500)
    original_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    discount_percent = serializers.IntegerField(min_value=0, max_value=100, required=False)
    quantity = serializers.IntegerField(min_value=0, max_value=2147483647, required=False)
    featured = serializers.BooleanField(required=False)
    image = RasterImageField()


class ProductQuerySerializer(serializers.Serializer):
    search = serializers.CharField(max_length=100, required=False, allow_blank=True)
    category = serializers.IntegerField(min_value=1, required=False)
    category_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    brand = serializers.CharField(max_length=100, required=False, allow_blank=True)
    min_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    max_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    stock = serializers.ChoiceField(choices=["in_stock", "out_of_stock"], required=False)
    featured = serializers.BooleanField(required=False)
    discounted = serializers.BooleanField(required=False)
    ordering = serializers.ChoiceField(choices=["-id", "id", "price", "-price", "name", "-name", "-discount_percent"], default="-id")

    def validate(self, attrs):
        if "min_price" in attrs and "max_price" in attrs and attrs["min_price"] > attrs["max_price"]:
            raise serializers.ValidationError({"max_price": ["Maximum price must be at least the minimum price."]})
        return attrs
