from django.contrib import admin

from .models import MaintenanceRequest


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
	list_display = (
		"title",
		"tenancy",
		"unit",
		"priority",
		"status",
		"assigned_to",
		"created_at",
	)
	list_filter = ("priority", "status")
	search_fields = ("title", "description", "tenancy__user__email", "unit__name")

# Register your models here.
