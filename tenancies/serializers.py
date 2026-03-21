from django.db.models import Sum
from rest_framework import serializers

from communications.models import Notice
from leases.models import Lease
from maintenance.models import MaintenanceRequest
from payments.models import Payment

from .models import Tenancy, TenantRating


class TenancySerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True)
    property_id = serializers.UUIDField(source="property.id", read_only=True)
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    unit_id = serializers.UUIDField(source="unit.id", read_only=True)
    rent_amount = serializers.SerializerMethodField()
    total_due = serializers.SerializerMethodField()
    fine_amount = serializers.SerializerMethodField()
    lease_status = serializers.SerializerMethodField()
    lease_end_date = serializers.SerializerMethodField()

    class Meta:
        model = Tenancy
        fields = [
            "id",
            "user_id",
            "full_name",
            "email",
            "phone",
            "property_id",
            "property_name",
            "unit_id",
            "unit_name",
            "status",
            "move_in_date",
            "move_out_date",
            "rent_amount",
            "total_due",
            "fine_amount",
            "lease_status",
            "lease_end_date",
            "created_at",
            "updated_at",
        ]

    def get_rent_amount(self, obj):
        return obj.unit.rent_amount if obj.unit else 0

    def get_total_due(self, obj):
        total = (
            obj.payments.exclude(status=Payment.Status.PAID)
            .aggregate(total=Sum("total"))
            .get("total")
        )
        return total or 0

    def get_fine_amount(self, obj):
        fine = (
            obj.payments.exclude(status=Payment.Status.PAID)
            .aggregate(total=Sum("fine"))
            .get("total")
        )
        return fine or 0

    def get_lease_status(self, obj):
        lease = obj.leases.exclude(status=Lease.Status.TERMINATED).order_by("-created_at").first()
        return lease.status if lease else None

    def get_lease_end_date(self, obj):
        lease = obj.leases.exclude(status=Lease.Status.TERMINATED).order_by("-created_at").first()
        return lease.end_date if lease else None


class TenantRatingSerializer(serializers.ModelSerializer):
    rated_by = serializers.CharField(source="rated_by.full_name", read_only=True)

    class Meta:
        model = TenantRating
        fields = ["id", "rating", "comment", "rated_by", "created_at"]


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRequest
        fields = [
            "id",
            "title",
            "description",
            "priority",
            "status",
            "created_at",
            "updated_at",
        ]


class NoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ["id", "type", "subject", "message", "is_read", "created_at"]
