import uuid

from django.conf import settings
from django.db import models

from properties.models import Property, Unit


class TimeStampedModel(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True


class Tenancy(TimeStampedModel):
	class Status(models.TextChoices):
		INVITED = "invited", "Invited"
		ACTIVE = "active", "Active"
		VACATED = "vacated", "Vacated"
		DEFAULTING = "defaulting", "Defaulting"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="tenancy",
	)
	property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="tenancies")
	unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name="tenancies")
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.INVITED)
	move_in_date = models.DateField(null=True, blank=True)
	move_out_date = models.DateField(null=True, blank=True)
	invited_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="tenant_invites",
	)
	notes = models.TextField(blank=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.user.email} @ {self.property.name}"


class TenantRating(TimeStampedModel):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	tenancy = models.ForeignKey(Tenancy, on_delete=models.CASCADE, related_name="ratings")
	rated_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="tenant_ratings_given",
	)
	rating = models.PositiveSmallIntegerField()
	comment = models.TextField(blank=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.tenancy.user.email} - {self.rating}/5"
