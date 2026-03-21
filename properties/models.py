import uuid

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True


class Property(TimeStampedModel):
	class PropertyType(models.TextChoices):
		APARTMENT = "apartment", "Apartment Block"
		BUNGALOW_COMPLEX = "bungalow_complex", "Bungalow Complex"
		TOWNHOUSE_COMPLEX = "townhouse_complex", "Townhouse Complex"
		MIXED_USE = "mixed_use", "Mixed Use"
		COMMERCIAL = "commercial", "Commercial Building"
		STANDALONE = "standalone", "Standalone House"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	owner = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="owned_properties",
	)
	name = models.CharField(max_length=255)
	type = models.CharField(max_length=50, choices=PropertyType.choices)
	address = models.CharField(max_length=255, blank=True)
	city = models.CharField(max_length=120, blank=True)
	county = models.CharField(max_length=120, blank=True)
	description = models.TextField(blank=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return self.name


class Unit(TimeStampedModel):
	class UnitType(models.TextChoices):
		BEDSITTER = "bedsitter", "Bedsitter"
		STUDIO = "studio", "Studio"
		BEDROOM_1 = "1_bedroom", "1 Bedroom"
		BEDROOM_2 = "2_bedroom", "2 Bedroom"
		BEDROOM_3 = "3_bedroom", "3 Bedroom"
		BEDROOM_4 = "4_bedroom", "4 Bedroom"
		PENTHOUSE = "penthouse", "Penthouse"
		BUNGALOW = "bungalow", "Bungalow"
		TOWNHOUSE = "townhouse", "Townhouse"
		VILLA = "villa", "Villa"
		SHOP = "shop", "Shop / Commercial"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="units")
	name = models.CharField(max_length=80)
	floor = models.IntegerField(default=1)
	unit_type = models.CharField(max_length=30, choices=UnitType.choices)
	rent_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

	class Meta:
		ordering = ["name"]
		constraints = [
			models.UniqueConstraint(fields=["property", "name"], name="uniq_unit_name_per_property"),
		]

	def __str__(self):
		return f"{self.property.name} - {self.name}"


class PaymentConfig(TimeStampedModel):
	class FineType(models.TextChoices):
		FLAT = "flat", "Flat Fee"
		PERCENTAGE = "percentage", "Percentage"
		PER_DAY = "per_day", "Per Day"
		PERCENTAGE_PER_DAY = "percentage_per_day", "Percentage Per Day"
		NONE = "none", "No Fine"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	property = models.OneToOneField(
		Property,
		on_delete=models.CASCADE,
		related_name="payment_config",
	)
	due_day = models.PositiveSmallIntegerField(default=5)
	fine_type = models.CharField(max_length=30, choices=FineType.choices, default=FineType.NONE)
	fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	fine_percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0)
	fine_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	additional_charges = models.JSONField(default=list, blank=True)
	water_bill = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	garbage_bill = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	security_levy = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	custom_charges = models.JSONField(default=list, blank=True)

	def __str__(self):
		return f"Payment config - {self.property.name}"


class PropertyDocument(TimeStampedModel):
	class DocumentType(models.TextChoices):
		LEASE_AGREEMENT = "lease_agreement", "Lease Agreement"
		TENANCY = "tenancy", "Tenancy"
		OTHER = "other", "Other"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	property = models.ForeignKey(
		Property,
		on_delete=models.CASCADE,
		related_name="documents",
	)
	document_type = models.CharField(max_length=40, choices=DocumentType.choices, default=DocumentType.OTHER)
	file = models.FileField(upload_to="property_documents/%Y/%m/")
	uploaded_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="uploaded_property_documents",
	)

	def __str__(self):
		return f"{self.property.name} - {self.document_type}"
