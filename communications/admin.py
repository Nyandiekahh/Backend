from django.contrib import admin

from .models import Announcement, EmailLog, EmailTemplate, Notice


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
	list_display = ("subject", "type", "sender", "property", "status", "sent_count", "sent_at")
	list_filter = ("type", "status")
	search_fields = ("subject", "message", "sender__email", "property__name")


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
	list_display = ("subject", "tenant", "type", "property", "is_read", "created_at")
	list_filter = ("type", "is_read")
	search_fields = ("subject", "message", "tenant__email", "property__name")


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
	list_display = ("recipient_email", "subject", "status", "sent_at", "created_at")
	list_filter = ("status",)
	search_fields = ("recipient_email", "subject", "error_message")


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
	list_display = ("name", "is_active", "updated_at")
	list_filter = ("is_active",)
	search_fields = ("name", "subject_template", "body_template")

# Register your models here.
