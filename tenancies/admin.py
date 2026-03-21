from django.contrib import admin

from .models import Tenancy, TenantRating


@admin.register(Tenancy)
class TenancyAdmin(admin.ModelAdmin):
	list_display = ("user", "property", "unit", "status", "move_in_date", "move_out_date")
	list_filter = ("status", "property")
	search_fields = ("user__email", "user__full_name", "property__name", "unit__name")


@admin.register(TenantRating)
class TenantRatingAdmin(admin.ModelAdmin):
	list_display = ("tenancy", "rating", "rated_by", "created_at")
	list_filter = ("rating",)
	search_fields = ("tenancy__user__email", "comment")

# Register your models here.
