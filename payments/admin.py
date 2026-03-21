from django.contrib import admin

from .models import MpesaTransaction, Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
	list_display = (
		"tenancy",
		"period",
		"amount",
		"fine",
		"total",
		"paid_amount",
		"status",
		"payment_method",
		"receipt_number",
	)
	list_filter = ("status", "payment_method", "property")
	search_fields = (
		"tenancy__user__email",
		"tenancy__user__full_name",
		"receipt_number",
		"unit__name",
	)


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
	list_display = (
		"checkout_request_id",
		"payment",
		"result_code",
		"mpesa_receipt_number",
		"phone_number",
		"created_at",
	)
	search_fields = ("checkout_request_id", "merchant_request_id", "mpesa_receipt_number")

# Register your models here.
