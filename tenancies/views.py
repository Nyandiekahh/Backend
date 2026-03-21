from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from communications.models import Notice
from leases.models import Lease
from maintenance.models import MaintenanceRequest
from payments.models import Payment
from properties.models import Property, Unit
from users.models import OTPCode, User

from .models import Tenancy, TenantRating
from .serializers import (
	MaintenanceRequestSerializer,
	NoticeSerializer,
	TenancySerializer,
	TenantRatingSerializer,
)


def _owner_tenancies(user):
	qs = Tenancy.objects.select_related("user", "property", "unit")
	if user.role == User.Role.OWNER:
		qs = qs.filter(property__owner=user)
	elif user.role == User.Role.TENANT:
		qs = qs.filter(user=user)
	return qs


def _resolve_tenancy(user, tenant_id):
	if tenant_id == "me":
		return Tenancy.objects.filter(user=user).first()
	return _owner_tenancies(user).filter(id=tenant_id).first()


class TenantsListView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		qs = _owner_tenancies(request.user)
		status_filter = request.query_params.get("status")
		property_id = request.query_params.get("property_id")
		search = request.query_params.get("search")

		if status_filter:
			qs = qs.filter(status=status_filter)
		if property_id:
			qs = qs.filter(property_id=property_id)
		if search:
			qs = qs.filter(
				Q(user__full_name__icontains=search)
				| Q(user__email__icontains=search)
				| Q(unit__name__icontains=search)
			)

		return Response(TenancySerializer(qs, many=True).data)


class TenantsInviteView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		if request.user.role not in [User.Role.OWNER, User.Role.ADMIN]:
			return Response({"detail": "Only owners can invite tenants."}, status=status.HTTP_403_FORBIDDEN)

		email = request.data.get("email")
		property_id = request.data.get("property_id")
		full_name = request.data.get("full_name", "")
		phone = request.data.get("phone", "")
		unit_id = request.data.get("unit_id")
		unit_type = request.data.get("unit_type")

		if not email or not property_id:
			return Response(
				{"detail": "email and property_id are required."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		prop = Property.objects.filter(id=property_id).first()
		if not prop or (request.user.role == User.Role.OWNER and prop.owner_id != request.user.id):
			return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

		unit = None
		if unit_id:
			unit = Unit.objects.filter(id=unit_id, property=prop).first()
		elif unit_type:
			occupied_unit_ids = Tenancy.objects.filter(
				property=prop,
				status=Tenancy.Status.ACTIVE,
				unit__isnull=False,
			).values_list("unit_id", flat=True)
			unit = (
				prop.units.filter(unit_type=unit_type)
				.exclude(id__in=occupied_unit_ids)
				.order_by("name")
				.first()
			)

		user, created = User.objects.get_or_create(
			email=email,
			defaults={
				"full_name": full_name or email.split("@")[0],
				"phone": phone,
				"role": User.Role.TENANT,
				"is_active": True,
			},
		)
		if not created:
			if full_name:
				user.full_name = full_name
			if phone:
				user.phone = phone
			user.role = User.Role.TENANT
			user.save(update_fields=["full_name", "phone", "role", "updated_at"])

		tenancy, _ = Tenancy.objects.update_or_create(
			user=user,
			defaults={
				"property": prop,
				"unit": unit,
				"status": Tenancy.Status.INVITED,
				"invited_by": request.user,
			},
		)

		otp = OTPCode.create_for_user(user, OTPCode.Purpose.INVITATION)
		Notice.objects.create(
			tenant=user,
			property=prop,
			type="general",
			subject="Invitation to NestFlow",
			message=f"You have been invited to join {prop.name}. Use OTP {otp.code} to continue.",
		)

		payload = TenancySerializer(tenancy).data
		payload["otp_debug"] = otp.code
		return Response(payload, status=status.HTTP_201_CREATED)


class TenantDetailView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request, tenant_id):
		tenancy = _resolve_tenancy(request.user, tenant_id)
		if not tenancy:
			return Response({"detail": "Tenant not found."}, status=status.HTTP_404_NOT_FOUND)
		return Response(TenancySerializer(tenancy).data)

	def patch(self, request, tenant_id):
		tenancy = _resolve_tenancy(request.user, tenant_id)
		if not tenancy:
			return Response({"detail": "Tenant not found."}, status=status.HTTP_404_NOT_FOUND)

		user = tenancy.user
		for field in ["full_name", "phone", "email"]:
			if field in request.data:
				setattr(user, field, request.data.get(field) or "")
		user.save(update_fields=["full_name", "phone", "email", "updated_at"])
		return Response(TenancySerializer(tenancy).data)


class TenantTerminateView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request, tenant_id):
		tenancy = _resolve_tenancy(request.user, tenant_id)
		if not tenancy:
			return Response({"detail": "Tenant not found."}, status=status.HTTP_404_NOT_FOUND)

		move_out_date = request.data.get("move_out_date")
		tenancy.status = Tenancy.Status.VACATED
		tenancy.move_out_date = move_out_date or timezone.now().date()
		tenancy.notes = request.data.get("notes") or tenancy.notes
		tenancy.save(update_fields=["status", "move_out_date", "notes", "updated_at"])
		return Response(TenancySerializer(tenancy).data)


class TenantPaymentsView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request, tenant_id):
		tenancy = _resolve_tenancy(request.user, tenant_id)
		if not tenancy:
			return Response({"detail": "Tenant not found."}, status=status.HTTP_404_NOT_FOUND)

		payments = tenancy.payments.all().order_by("-created_at")
		status_filter = request.query_params.get("status")
		if status_filter:
			payments = payments.filter(status=status_filter)

		data = [
			{
				"id": str(p.id),
				"period": p.period,
				"amount": p.amount,
				"fine": p.fine,
				"total": p.total,
				"status": p.status,
				"receipt_number": p.receipt_number,
				"paid_at": p.paid_at,
				"tenant_name": tenancy.user.full_name or tenancy.user.email,
				"unit_name": tenancy.unit.name if tenancy.unit else None,
			}
			for p in payments
		]
		return Response(data)


class TenantLeaseView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request, tenant_id):
		tenancy = _resolve_tenancy(request.user, tenant_id)
		if not tenancy:
			return Response({"detail": "Tenant not found."}, status=status.HTTP_404_NOT_FOUND)

		lease = tenancy.leases.exclude(status=Lease.Status.TERMINATED).order_by("-created_at").first()
		if not lease:
			return Response({}, status=status.HTTP_200_OK)

		payload = {
			"id": str(lease.id),
			"tenant_id": str(tenancy.id),
			"property_id": str(lease.property_id),
			"unit_id": str(lease.unit_id),
			"unit_name": lease.unit.name,
			"property_name": lease.property.name,
			"start_date": lease.start_date,
			"end_date": lease.end_date,
			"rent_amount": lease.rent_amount,
			"status": lease.status,
			"signed_at": lease.signed_at,
			"document_url": lease.document_url,
		}
		return Response(payload)


class TenantMaintenanceListCreateView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request, tenant_id):
		tenancy = _resolve_tenancy(request.user, tenant_id)
		if not tenancy:
			return Response({"detail": "Tenant not found."}, status=status.HTTP_404_NOT_FOUND)
		requests = tenancy.maintenance_requests.all()
		return Response(MaintenanceRequestSerializer(requests, many=True).data)

	def post(self, request, tenant_id):
		tenancy = _resolve_tenancy(request.user, tenant_id)
		if not tenancy:
			return Response({"detail": "Tenant not found."}, status=status.HTTP_404_NOT_FOUND)

		serializer = MaintenanceRequestSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		maintenance = serializer.save(tenancy=tenancy, unit=tenancy.unit)
		return Response(MaintenanceRequestSerializer(maintenance).data, status=status.HTTP_201_CREATED)


class TenantMaintenanceDetailView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def patch(self, request, tenant_id, request_id):
		tenancy = _resolve_tenancy(request.user, tenant_id)
		if not tenancy:
			return Response({"detail": "Tenant not found."}, status=status.HTTP_404_NOT_FOUND)

		maintenance = tenancy.maintenance_requests.filter(id=request_id).first()
		if not maintenance:
			return Response({"detail": "Request not found."}, status=status.HTTP_404_NOT_FOUND)

		serializer = MaintenanceRequestSerializer(maintenance, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data)


class TenantRatingsView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request, tenant_id):
		tenancy = _resolve_tenancy(request.user, tenant_id)
		if not tenancy:
			return Response({"detail": "Tenant not found."}, status=status.HTTP_404_NOT_FOUND)
		ratings = tenancy.ratings.select_related("rated_by")
		return Response(TenantRatingSerializer(ratings, many=True).data)

	def post(self, request, tenant_id):
		tenancy = _resolve_tenancy(request.user, tenant_id)
		if not tenancy:
			return Response({"detail": "Tenant not found."}, status=status.HTTP_404_NOT_FOUND)
		serializer = TenantRatingSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		rating = TenantRating.objects.create(
			tenancy=tenancy,
			rating=serializer.validated_data["rating"],
			comment=serializer.validated_data.get("comment", ""),
			rated_by=request.user,
		)
		return Response(TenantRatingSerializer(rating).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def send_reminders(request):
	property_id = request.data.get("property_id")
	tenancies = _owner_tenancies(request.user).filter(status=Tenancy.Status.ACTIVE)
	if property_id:
		tenancies = tenancies.filter(property_id=property_id)
	sent_count = tenancies.count()
	return Response({"sent_count": sent_count})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def send_overdue_reminders(request):
	property_id = request.data.get("property_id")
	tenancies = _owner_tenancies(request.user).filter(status=Tenancy.Status.ACTIVE)
	if property_id:
		tenancies = tenancies.filter(property_id=property_id)
	overdue_tenancy_ids = Payment.objects.filter(
		tenancy__in=tenancies,
		status=Payment.Status.OVERDUE,
	).values_list("tenancy_id", flat=True)
	sent_count = tenancies.filter(id__in=overdue_tenancy_ids).distinct().count()
	return Response({"sent_count": sent_count})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me_profile(request):
	tenancy = Tenancy.objects.filter(user=request.user).select_related("user", "property", "unit").first()
	if not tenancy:
		return Response({}, status=status.HTTP_200_OK)
	return Response(TenancySerializer(tenancy).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me_lease(request):
	tenancy = Tenancy.objects.filter(user=request.user).first()
	if not tenancy:
		return Response({}, status=status.HTTP_200_OK)
	view = TenantLeaseView()
	return view.get(request, "me")


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me_payments(request):
	tenancy = Tenancy.objects.filter(user=request.user).first()
	if not tenancy:
		return Response([], status=status.HTTP_200_OK)
	view = TenantPaymentsView()
	return view.get(request, "me")


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me_notices(request):
	notices = Notice.objects.filter(tenant=request.user)
	return Response(NoticeSerializer(notices, many=True).data)
