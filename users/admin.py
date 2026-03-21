from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OTPCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
	model = User
	ordering = ("-created_at",)
	list_display = ("email", "full_name", "role", "is_active", "is_staff", "created_at")
	list_filter = ("role", "is_active", "is_staff", "is_superuser")
	search_fields = ("email", "full_name", "phone")
	readonly_fields = ("created_at", "updated_at", "last_login")

	fieldsets = (
		(None, {"fields": ("email", "password")}),
		(
			"Personal info",
			{"fields": ("full_name", "phone", "role", "is_email_verified")},
		),
		(
			"Permissions",
			{
				"fields": (
					"is_active",
					"is_staff",
					"is_superuser",
					"groups",
					"user_permissions",
				)
			},
		),
		("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
	)

	add_fieldsets = (
		(
			None,
			{
				"classes": ("wide",),
				"fields": ("email", "full_name", "role", "password1", "password2"),
			},
		),
	)


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
	list_display = ("user", "purpose", "code", "expires_at", "is_used", "created_at")
	list_filter = ("purpose", "is_used")
	search_fields = ("user__email", "code")
	readonly_fields = ("created_at",)

# Register your models here.
