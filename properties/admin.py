from django.contrib import admin

from .models import PaymentConfig, Property, PropertyDocument, Unit


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
	list_display = ("name", "owner", "type", "city", "county", "created_at")
	list_filter = ("type", "city", "county")
	search_fields = ("name", "owner__email", "address")


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
	list_display = ("name", "property", "unit_type", "floor", "rent_amount", "created_at")
	list_filter = ("unit_type", "property")
	search_fields = ("name", "property__name")


@admin.register(PaymentConfig)
class PaymentConfigAdmin(admin.ModelAdmin):
	list_display = ("property", "due_day", "fine_type", "fine_amount", "fine_percentage")
	list_filter = ("fine_type",)


@admin.register(PropertyDocument)
class PropertyDocumentAdmin(admin.ModelAdmin):
	list_display = ("property", "document_type", "uploaded_by", "created_at")
	list_filter = ("document_type",)
	search_fields = ("property__name", "uploaded_by__email")

# Register your models here.
