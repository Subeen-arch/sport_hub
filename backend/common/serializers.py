from collections.abc import Mapping

from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    """Writable contracts reject unexpected keys, including role/owner injection."""

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError({key: ["This field is not accepted."] for key in sorted(unknown)})
        return super().to_internal_value(data)
