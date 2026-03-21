from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import Payment
from tenancies.models import Tenancy

from .models import Announcement, EmailLog, EmailTemplate, Notice
from .serializers import AnnouncementSerializer, EmailLogSerializer, EmailTemplateSerializer


def _ensure_default_templates():
	defaults = [
		{
			"name": "invitation",
			"subject_template": "You are invited to join NestFlow",
			"body_template": "You have been invited to your property portal. Use your OTP to continue.",
		},
		{
			"name": "payment_reminder",
			"subject_template": "Rent Payment Reminder",
			"body_template": "This is a reminder to complete your rent payment.",
		},
		{
			"name": "overdue_notice",
			"subject_template": "Urgent: Overdue Rent Notice",
			"body_template": "Your rent payment is overdue. Please settle as soon as possible.",
		},
	]
	for template in defaults:
		EmailTemplate.objects.get_or_create(name=template["name"], defaults=template)


def _tenants_for_scope(user, property_id=None, overdue_only=False):
	tenancies = Tenancy.objects.select_related("user", "property").filter(status=Tenancy.Status.ACTIVE)
	if user.role == "owner":
		tenancies = tenancies.filter(property__owner=user)
	if property_id:
		tenancies = tenancies.filter(property_id=property_id)
	if overdue_only:
		overdue_tenancy_ids = Payment.objects.filter(
			tenancy__in=tenancies,
			status=Payment.Status.OVERDUE,
		).values_list("tenancy_id", flat=True)
		tenancies = tenancies.filter(id__in=overdue_tenancy_ids).distinct()
	return tenancies


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def send_announcement(request):
	serializer = AnnouncementSerializer(data=request.data)
	serializer.is_valid(raise_exception=True)

	announcement = serializer.save(sender=request.user, status=Announcement.Status.SENT, sent_at=timezone.now())
	tenancies = _tenants_for_scope(request.user, property_id=request.data.get("property_id"))
	recipients = []
	for tenancy in tenancies:
		recipients.append(str(tenancy.user.id))
		Notice.objects.create(
			tenant=tenancy.user,
			property=tenancy.property,
			type=announcement.type,
			subject=announcement.subject,
			message=announcement.message,
		)
		EmailLog.objects.create(
			announcement=announcement,
			recipient_email=tenancy.user.email,
			subject=announcement.subject,
			body=announcement.message,
			status=EmailLog.Status.SENT,
			sent_at=timezone.now(),
		)

	announcement.recipients = recipients
	announcement.sent_count = len(recipients)
	announcement.save(update_fields=["recipients", "sent_count", "updated_at"])
	return Response(AnnouncementSerializer(announcement).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def send_bulk_reminder(request):
	_ensure_default_templates()
	template = EmailTemplate.objects.filter(name="payment_reminder", is_active=True).first()
	tenancies = _tenants_for_scope(request.user, property_id=request.data.get("property_id"))
	sent_count = 0
	for tenancy in tenancies:
		EmailLog.objects.create(
			recipient_email=tenancy.user.email,
			subject=template.subject_template if template else "Rent Payment Reminder",
			body=template.body_template if template else "Please complete your rent payment.",
			status=EmailLog.Status.SENT,
			sent_at=timezone.now(),
		)
		sent_count += 1
	return Response({"sent_count": sent_count})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def send_overdue_reminder(request):
	_ensure_default_templates()
	template = EmailTemplate.objects.filter(name="overdue_notice", is_active=True).first()
	tenancies = _tenants_for_scope(
		request.user,
		property_id=request.data.get("property_id"),
		overdue_only=True,
	)
	sent_count = 0
	for tenancy in tenancies:
		EmailLog.objects.create(
			recipient_email=tenancy.user.email,
			subject=template.subject_template if template else "Overdue Rent Notice",
			body=template.body_template if template else "Your payment is overdue.",
			status=EmailLog.Status.SENT,
			sent_at=timezone.now(),
		)
		sent_count += 1
	return Response({"sent_count": sent_count})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def send_invitation(request):
	email = request.data.get("email")
	if not email:
		return Response({"detail": "email is required."}, status=status.HTTP_400_BAD_REQUEST)
	EmailLog.objects.create(
		recipient_email=email,
		subject="NestFlow Invitation",
		body=request.data.get("message", "You have been invited to join NestFlow."),
		status=EmailLog.Status.SENT,
		sent_at=timezone.now(),
	)
	return Response({"status": "sent"}, status=status.HTTP_201_CREATED)


class EmailLogsView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		logs = EmailLog.objects.all()
		status_filter = request.query_params.get("status")
		if status_filter:
			logs = logs.filter(status=status_filter)
		return Response(EmailLogSerializer(logs, many=True).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def resend_email(request, email_id):
	log = EmailLog.objects.filter(id=email_id).first()
	if not log:
		return Response({"detail": "Email log not found."}, status=status.HTTP_404_NOT_FOUND)
	resent = EmailLog.objects.create(
		announcement=log.announcement,
		recipient_email=log.recipient_email,
		subject=log.subject,
		body=log.body,
		status=EmailLog.Status.SENT,
		sent_at=timezone.now(),
	)
	return Response(EmailLogSerializer(resent).data)


class EmailTemplatesView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		_ensure_default_templates()
		templates = EmailTemplate.objects.all()
		return Response(EmailTemplateSerializer(templates, many=True).data)


class EmailTemplateDetailView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def patch(self, request, template_id):
		template = EmailTemplate.objects.filter(id=template_id).first()
		if not template:
			return Response({"detail": "Template not found."}, status=status.HTTP_404_NOT_FOUND)
		serializer = EmailTemplateSerializer(template, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data)
