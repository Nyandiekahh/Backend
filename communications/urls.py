from django.urls import path

from .views import (
    EmailLogsView,
    EmailTemplateDetailView,
    EmailTemplatesView,
    resend_email,
    send_announcement,
    send_bulk_reminder,
    send_invitation,
    send_overdue_reminder,
)

urlpatterns = [
    path("emails/announcement/", send_announcement),
    path("emails/bulk-reminder/", send_bulk_reminder),
    path("emails/overdue-reminder/", send_overdue_reminder),
    path("emails/invitation/", send_invitation),
    path("emails/logs/", EmailLogsView.as_view()),
    path("emails/logs/<uuid:email_id>/resend/", resend_email),
    path("emails/templates/", EmailTemplatesView.as_view()),
    path("emails/templates/<uuid:template_id>/", EmailTemplateDetailView.as_view()),
]
