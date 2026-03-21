from rest_framework import serializers

from tenancies.models import Tenancy

from .models import PaymentConfig, Property, PropertyDocument, Unit


class PropertySerializer(serializers.ModelSerializer):
    owner_id = serializers.UUIDField(source="owner.id", read_only=True)
    total_units = serializers.IntegerField(source="units.count", read_only=True)

    class Meta:
        model = Property
        fields = [
            "id",
            "owner_id",
            "name",
            "type",
            "address",
            "city",
            "county",
            "description",
            "total_units",
            "created_at",
            "updated_at",
        ]


class UnitSerializer(serializers.ModelSerializer):
    property_id = serializers.UUIDField(source="property.id", read_only=True)
    is_occupied = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()
    tenant_id = serializers.SerializerMethodField()

    class Meta:
        model = Unit
        fields = [
            "id",
            "property_id",
            "name",
            "floor",
            "unit_type",
            "rent_amount",
            "is_occupied",
            "tenant_name",
            "tenant_id",
            "created_at",
            "updated_at",
        ]

    def _active_tenancy(self, obj):
        return (
            Tenancy.objects.filter(unit=obj, status=Tenancy.Status.ACTIVE)
            .select_related("user")
            .first()
        )

    def get_is_occupied(self, obj):
        return self._active_tenancy(obj) is not None

    def get_tenant_name(self, obj):
        tenancy = self._active_tenancy(obj)
        if not tenancy:
            return None
        return tenancy.user.full_name or tenancy.user.email

    def get_tenant_id(self, obj):
        tenancy = self._active_tenancy(obj)
        return str(tenancy.id) if tenancy else None


class PaymentConfigSerializer(serializers.ModelSerializer):
    property_id = serializers.UUIDField(source="property.id", read_only=True)

    class Meta:
        model = PaymentConfig
        fields = [
            "id",
            "property_id",
            "due_day",
            "fine_type",
            "fine_amount",
            "fine_percentage",
            "fine_per_day",
            "additional_charges",
            "water_bill",
            "garbage_bill",
            "security_levy",
            "custom_charges",
            "created_at",
            "updated_at",
        ]


class PropertyDocumentSerializer(serializers.ModelSerializer):
    property_id = serializers.UUIDField(source="property.id", read_only=True)
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = PropertyDocument
        fields = [
            "id",
            "property_id",
            "document_type",
            "file",
            "file_url",
            "file_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "property_id", "file_url", "file_name", "created_at", "updated_at"]

    def get_file_url(self, obj):
        return obj.file.url if obj.file else None

    def get_file_name(self, obj):
        if not obj.file:
            return ""
        return obj.file.name.split("/")[-1]
