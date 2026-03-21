import uuid
from decimal import Decimal

from django.db import models

from properties.models import Property, Unit
from tenancies.models import Tenancy


class TimeStampedModel(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True


class Payment(TimeStampedModel):
	class Status(models.TextChoices):
		PENDING = "pending", "Pending"
		PAID = "paid", "Paid"
		OVERDUE = "overdue", "Overdue"
		PARTIAL = "partial", "Partial"
		WAIVED = "waived", "Waived"

	class Method(models.TextChoices):
		MPESA = "mpesa", "M-Pesa"
		MANUAL = "manual", "Manual"
		BANK_TRANSFER = "bank_transfer", "Bank Transfer"

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	tenancy = models.ForeignKey(Tenancy, on_delete=models.CASCADE, related_name="payments")
	property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="payments")
	unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
	period = models.CharField(max_length=7, blank=True)
	amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	fine = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	payment_method = models.CharField(max_length=20, choices=Method.choices, default=Method.MPESA)
	receipt_number = models.CharField(max_length=100, blank=True)
	mpesa_checkout_request_id = models.CharField(max_length=120, blank=True)
	paid_at = models.DateTimeField(null=True, blank=True)
	metadata = models.JSONField(default=dict, blank=True)

	class Meta:
		ordering = ["-created_at"]

	def save(self, *args, **kwargs):
		self.amount = self.amount or Decimal("0")
		self.fine = self.fine or Decimal("0")
		self.total = self.amount + self.fine
		super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.tenancy.user.email} - {self.period or 'payment'}"


class MpesaTransaction(TimeStampedModel):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="mpesa_transaction")
	merchant_request_id = models.CharField(max_length=120, blank=True)
	checkout_request_id = models.CharField(max_length=120, unique=True)
	result_code = models.IntegerField(default=0)
	result_desc = models.TextField(blank=True)
	mpesa_receipt_number = models.CharField(max_length=100, blank=True)
	phone_number = models.CharField(max_length=20, blank=True)
	transaction_date = models.CharField(max_length=30, blank=True)
	raw_callback = models.JSONField(default=dict, blank=True)

	def __str__(self):
		return self.checkout_request_id
