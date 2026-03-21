import uuid

from django.db import models

from properties.models import Property, Unit
from tenancies.models import Tenancy


class TimeStampedModel(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True


class Lease(TimeStampedModel):
	class Status(models.TextChoices):
		PENDING_SIGNATURE = "pending_signature", "Pending Signature"
		ACTIVE = "active", "Active"
		EXPIRED = "expired", "Expired"
		TERMINATED = "terminated", "Terminated"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	tenancy = models.ForeignKey(Tenancy, on_delete=models.CASCADE, related_name="leases")
	property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="leases")
	unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="leases")
	start_date = models.DateField()
	end_date = models.DateField()
	rent_amount = models.DecimalField(max_digits=12, decimal_places=2)
	status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING_SIGNATURE)
	signed_at = models.DateTimeField(null=True, blank=True)
	document = models.FileField(upload_to="lease_documents/%Y/%m/", null=True, blank=True)
	termination_reason = models.TextField(blank=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.tenancy.user.email} - {self.property.name}"
