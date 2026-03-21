from rest_framework import serializers

from .models import Lease


class LeaseSerializer(serializers.ModelSerializer):
    tenant_id = serializers.UUIDField(source="tenancy.id")
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True)
    document_url = serializers.SerializerMethodField()

    class Meta:
        model = Lease
        fields = [
            "id",
            "tenant_id",
            "property_id",
            "unit_id",
            "unit_name",
            "property_name",
            "start_date",
            "end_date",
            "rent_amount",
            "status",
            "signed_at",
            "document_url",
            "created_at",
            "updated_at",
        ]

    def get_document_url(self, obj):
        return obj.document.url if obj.document else None
