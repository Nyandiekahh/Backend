from django.http import FileResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from properties.models import Property, Unit
from tenancies.models import Tenancy
from users.models import User

from .models import Lease
from .serializers import LeaseSerializer


def _lease_queryset_for_user(user):
	qs = Lease.objects.select_related("tenancy", "property", "unit", "tenancy__user")
	if user.role == User.Role.OWNER:
		qs = qs.filter(property__owner=user)
	elif user.role == User.Role.TENANT:
		qs = qs.filter(tenancy__user=user)
	return qs


class LeaseListCreateView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		qs = _lease_queryset_for_user(request.user)
		status_filter = request.query_params.get("status")
		tenant_id = request.query_params.get("tenant_id")
		if status_filter:
			qs = qs.filter(status=status_filter)
		if tenant_id:
			qs = qs.filter(tenancy_id=tenant_id)
		return Response(LeaseSerializer(qs, many=True).data)

	def post(self, request):
		tenant_id = request.data.get("tenant_id")
		property_id = request.data.get("property_id")
		unit_id = request.data.get("unit_id")

		tenancy = Tenancy.objects.filter(id=tenant_id).first()
		prop = Property.objects.filter(id=property_id).first()
		unit = Unit.objects.filter(id=unit_id).first()

		if not tenancy or not prop or not unit:
			return Response({"detail": "Invalid tenant, property, or unit."}, status=status.HTTP_400_BAD_REQUEST)

		if request.user.role == User.Role.OWNER and prop.owner_id != request.user.id:
			return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

		lease = Lease.objects.create(
			tenancy=tenancy,
			property=prop,
			unit=unit,
			start_date=request.data.get("start_date"),
			end_date=request.data.get("end_date"),
			rent_amount=request.data.get("rent_amount") or unit.rent_amount,
			status=Lease.Status.PENDING_SIGNATURE,
		)
		return Response(LeaseSerializer(lease).data, status=status.HTTP_201_CREATED)


class LeaseDetailView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get_object(self, request, lease_id):
		return _lease_queryset_for_user(request.user).filter(id=lease_id).first()

	def get(self, request, lease_id):
		lease = self.get_object(request, lease_id)
		if not lease:
			return Response({"detail": "Lease not found."}, status=status.HTTP_404_NOT_FOUND)
		return Response(LeaseSerializer(lease).data)

	def patch(self, request, lease_id):
		lease = self.get_object(request, lease_id)
		if not lease:
			return Response({"detail": "Lease not found."}, status=status.HTTP_404_NOT_FOUND)
		serializer = LeaseSerializer(lease, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def sign_lease(request, lease_id):
	lease = _lease_queryset_for_user(request.user).filter(id=lease_id).first()
	if not lease:
		return Response({"detail": "Lease not found."}, status=status.HTTP_404_NOT_FOUND)
	lease.status = Lease.Status.ACTIVE
	lease.signed_at = timezone.now()
	lease.save(update_fields=["status", "signed_at", "updated_at"])
	tenancy = lease.tenancy
	if tenancy.status != Tenancy.Status.ACTIVE:
		tenancy.status = Tenancy.Status.ACTIVE
		tenancy.move_in_date = tenancy.move_in_date or timezone.now().date()
		tenancy.save(update_fields=["status", "move_in_date", "updated_at"])
	return Response(LeaseSerializer(lease).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def terminate_lease(request, lease_id):
	lease = _lease_queryset_for_user(request.user).filter(id=lease_id).first()
	if not lease:
		return Response({"detail": "Lease not found."}, status=status.HTTP_404_NOT_FOUND)
	lease.status = Lease.Status.TERMINATED
	lease.termination_reason = request.data.get("reason", "")
	lease.save(update_fields=["status", "termination_reason", "updated_at"])
	return Response(LeaseSerializer(lease).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def renew_lease(request, lease_id):
	lease = _lease_queryset_for_user(request.user).filter(id=lease_id).first()
	if not lease:
		return Response({"detail": "Lease not found."}, status=status.HTTP_404_NOT_FOUND)
	renewed = Lease.objects.create(
		tenancy=lease.tenancy,
		property=lease.property,
		unit=lease.unit,
		start_date=request.data.get("new_start_date") or lease.end_date,
		end_date=request.data.get("new_end_date") or lease.end_date,
		rent_amount=request.data.get("rent_amount") or lease.rent_amount,
		status=Lease.Status.PENDING_SIGNATURE,
		document=lease.document,
	)
	return Response(LeaseSerializer(renewed).data, status=status.HTTP_201_CREATED)


class LeaseDocumentView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request, lease_id):
		lease = _lease_queryset_for_user(request.user).filter(id=lease_id).first()
		if not lease:
			return Response({"detail": "Lease not found."}, status=status.HTTP_404_NOT_FOUND)
		uploaded_file = request.FILES.get("file")
		if not uploaded_file:
			return Response({"detail": "file is required."}, status=status.HTTP_400_BAD_REQUEST)
		lease.document = uploaded_file
		lease.save(update_fields=["document", "updated_at"])
		return Response(LeaseSerializer(lease).data)

	def get(self, request, lease_id):
		lease = _lease_queryset_for_user(request.user).filter(id=lease_id).first()
		if not lease or not lease.document:
			return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)
		return FileResponse(lease.document.open("rb"), as_attachment=True, filename=lease.document.name.split("/")[-1])
