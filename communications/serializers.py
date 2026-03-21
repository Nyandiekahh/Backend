from rest_framework import serializers

from .models import Announcement, EmailLog, EmailTemplate


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = [
            "id",
            "property",
            "type",
            "subject",
            "message",
            "recipients",
            "sent_count",
            "status",
            "sent_at",
            "created_at",
        ]


class EmailLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailLog
        fields = [
            "id",
            "announcement",
            "recipient_email",
            "subject",
            "body",
            "status",
            "error_message",
            "sent_at",
            "created_at",
        ]


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = ["id", "name", "subject_template", "body_template", "is_active", "updated_at"]
