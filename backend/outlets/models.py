from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Greatest, Least


class Coordinates(models.Model):
    latitude = models.DecimalField(max_digits=10, decimal_places=7, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.DecimalField(max_digits=10, decimal_places=7, validators=[MinValueValidator(-180), MaxValueValidator(180)])

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(condition=models.Q(latitude__gte=-90, latitude__lte=90), name="%(class)s_latitude_valid"),
            models.CheckConstraint(condition=models.Q(longitude__gte=-180, longitude__lte=180), name="%(class)s_longitude_valid"),
        ]


class Shop(Coordinates):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    rating = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(5)])
    opening_hours = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(Coordinates.Meta):
        abstract = False
        ordering = ["name"]
        constraints = Coordinates.Meta.constraints + [models.CheckConstraint(condition=models.Q(rating__isnull=True) | models.Q(rating__gte=0, rating__lte=5), name="shop_rating_valid")]

    def __str__(self):
        return self.name


class MapNode(Coordinates):
    name = models.CharField(max_length=100)

    class Meta(Coordinates.Meta):
        abstract = False
        ordering = ["id"]

    def __str__(self):
        return self.name


class MapEdge(models.Model):
    from_node = models.ForeignKey(MapNode, on_delete=models.CASCADE, related_name="outgoing_edges")
    to_node = models.ForeignKey(MapNode, on_delete=models.CASCADE, related_name="incoming_edges")
    road_name = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["from_node", "to_node"], name="map_edge_unique"),
            models.UniqueConstraint(Least("from_node", "to_node"), Greatest("from_node", "to_node"), name="map_edge_undirected_unique"),
            models.CheckConstraint(condition=~models.Q(from_node=models.F("to_node")), name="map_edge_distinct_nodes"),
        ]

    def clean(self):
        if self.from_node_id == self.to_node_id:
            raise ValidationError("A road must connect two different nodes.")
