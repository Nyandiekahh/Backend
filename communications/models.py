import uuid

from django.conf import settings
from django.db import models

from properties.models import Property


class TimeStampedModel(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True


class Announcement(TimeStampedModel):
	class Type(models.TextChoices):
		GENERAL = "general", "General"
		MAINTENANCE = "maintenance", "Maintenance"
		PAYMENT = "payment", "Payment"
		EMERGENCY = "emergency", "Emergency"

	class Status(models.TextChoices):
		DRAFT = "draft", "Draft"
		SENT = "sent", "Sent"
		FAILED = "failed", "Failed"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	sender = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		related_name="sent_announcements",
	)
	property = models.ForeignKey(
		Property,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="announcements",
	)
	type = models.CharField(max_length=20, choices=Type.choices, default=Type.GENERAL)
	subject = models.CharField(max_length=255)
	message = models.TextField()
	recipients = models.JSONField(default=list, blank=True)
	sent_count = models.PositiveIntegerField(default=0)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
	sent_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return self.subject


class Notice(TimeStampedModel):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	tenant = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="notices",
	)
	property = models.ForeignKey(
		Property,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="notices",
	)
	type = models.CharField(max_length=20, default="general")
	subject = models.CharField(max_length=255)
	message = models.TextField()
	is_read = models.BooleanField(default=False)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.tenant.email} - {self.subject}"


class EmailLog(TimeStampedModel):
	class Status(models.TextChoices):
		SENT = "sent", "Sent"
		FAILED = "failed", "Failed"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	announcement = models.ForeignKey(
		Announcement,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="email_logs",
	)
	recipient_email = models.EmailField()
	subject = models.CharField(max_length=255)
	body = models.TextField()
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.SENT)
	error_message = models.TextField(blank=True)
	sent_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.recipient_email} - {self.status}"


class EmailTemplate(TimeStampedModel):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	name = models.CharField(max_length=120, unique=True)
	subject_template = models.CharField(max_length=255)
	body_template = models.TextField()
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ["name"]

	def __str__(self):
		return self.name
