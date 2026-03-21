from django.contrib import admin

from .models import Lease


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
	list_display = (
		"tenancy",
		"property",
		"unit",
		"start_date",
		"end_date",
		"rent_amount",
		"status",
		"signed_at",
	)
	list_filter = ("status", "property")
	search_fields = ("tenancy__user__email", "property__name", "unit__name")

# Register your models here.
