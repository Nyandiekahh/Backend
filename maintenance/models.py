import uuid

from django.conf import settings
from django.db import models

from properties.models import Unit
from tenancies.models import Tenancy


class TimeStampedModel(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True


class MaintenanceRequest(TimeStampedModel):
	class Status(models.TextChoices):
		OPEN = "open", "Open"
		IN_PROGRESS = "in_progress", "In Progress"
		RESOLVED = "resolved", "Resolved"
		CLOSED = "closed", "Closed"

	class Priority(models.TextChoices):
		LOW = "low", "Low"
		MEDIUM = "medium", "Medium"
		HIGH = "high", "High"
		URGENT = "urgent", "Urgent"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	tenancy = models.ForeignKey(Tenancy, on_delete=models.CASCADE, related_name="maintenance_requests")
	unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_requests")
	title = models.CharField(max_length=255)
	description = models.TextField(blank=True)
	priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
	assigned_to = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="assigned_maintenance_requests",
	)
	notes = models.TextField(blank=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return self.title
