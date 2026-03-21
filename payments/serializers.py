from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    tenant_id = serializers.UUIDField(source="tenancy.id", read_only=True)
    tenant_name = serializers.CharField(source="tenancy.user.full_name", read_only=True)
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    property_id = serializers.UUIDField(source="property.id", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "tenant_id",
            "property_id",
            "unit_name",
            "tenant_name",
            "period",
            "amount",
            "fine",
            "total",
            "paid_amount",
            "status",
            "payment_method",
            "receipt_number",
            "mpesa_checkout_request_id",
            "paid_at",
            "created_at",
            "updated_at",
        ]
