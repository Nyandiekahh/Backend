from datetime import date
from decimal import Decimal

from django.db.models import Sum
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import Payment
from tenancies.models import Tenancy

from .models import PaymentConfig, Property, PropertyDocument, Unit
from .serializers import (
	PaymentConfigSerializer,
	PropertyDocumentSerializer,
	PropertySerializer,
	UnitSerializer,
)


def _owner_property_or_404(user, property_id):
	queryset = Property.objects.all()
	if user.role == "owner":
		queryset = queryset.filter(owner=user)
	return queryset.filter(id=property_id).first()


class PropertyListCreateView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		queryset = Property.objects.select_related("owner")
		if request.user.role == "owner":
			queryset = queryset.filter(owner=request.user)
		search = request.query_params.get("search")
		if search:
			queryset = queryset.filter(name__icontains=search)
		serializer = PropertySerializer(queryset, many=True)
		return Response(serializer.data)

	def post(self, request):
		serializer = PropertySerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		prop = serializer.save(owner=request.user)
		PaymentConfig.objects.get_or_create(property=prop)
		return Response(PropertySerializer(prop).data, status=status.HTTP_201_CREATED)


class PropertyDetailView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get_object(self, request, property_id):
		prop = _owner_property_or_404(request.user, property_id)
		if not prop:
			return None
		return prop

	def get(self, request, property_id):
		prop = self.get_object(request, property_id)
		if not prop:
			return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)
		return Response(PropertySerializer(prop).data)

	def patch(self, request, property_id):
		prop = self.get_object(request, property_id)
		if not prop:
			return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)
		serializer = PropertySerializer(prop, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data)

	def delete(self, request, property_id):
		prop = self.get_object(request, property_id)
		if not prop:
			return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)
		if prop.tenancies.filter(status=Tenancy.Status.ACTIVE).exists():
			return Response(
				{"detail": "Cannot delete property with active tenancies."},
				status=status.HTTP_400_BAD_REQUEST,
			)
		prop.delete()
		return Response({"success": True})


class UnitListCreateView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get_property(self, request, property_id):
		return _owner_property_or_404(request.user, property_id)

	def get(self, request, property_id):
		prop = self.get_property(request, property_id)
		if not prop:
			return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)
		units = prop.units.all().order_by("name")
		return Response(UnitSerializer(units, many=True).data)

	def post(self, request, property_id):
		prop = self.get_property(request, property_id)
		if not prop:
			return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)
		serializer = UnitSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		unit = serializer.save(property=prop)
		return Response(UnitSerializer(unit).data, status=status.HTTP_201_CREATED)


class UnitBulkCreateView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request, property_id):
		prop = _owner_property_or_404(request.user, property_id)
		if not prop:
			return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

		units_data = request.data.get("units", [])
		if not isinstance(units_data, list):
			return Response({"detail": "Units must be a list."}, status=status.HTTP_400_BAD_REQUEST)

		created = []
		for unit_data in units_data:
			serializer = UnitSerializer(data=unit_data)
			serializer.is_valid(raise_exception=True)
			created.append(serializer.save(property=prop))

		return Response(
			{
				"created_count": len(created),
				"units": UnitSerializer(created, many=True).data,
			},
			status=status.HTTP_201_CREATED,
		)


class UnitDetailView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get_unit(self, request, property_id, unit_id):
		prop = _owner_property_or_404(request.user, property_id)
		if not prop:
			return None
		return prop.units.filter(id=unit_id).first()

	def get(self, request, property_id, unit_id):
		unit = self.get_unit(request, property_id, unit_id)
		if not unit:
			return Response({"detail": "Unit not found."}, status=status.HTTP_404_NOT_FOUND)
		return Response(UnitSerializer(unit).data)

	def patch(self, request, property_id, unit_id):
		unit = self.get_unit(request, property_id, unit_id)
		if not unit:
			return Response({"detail": "Unit not found."}, status=status.HTTP_404_NOT_FOUND)
		serializer = UnitSerializer(unit, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data)

	def delete(self, request, property_id, unit_id):
		unit = self.get_unit(request, property_id, unit_id)
		if not unit:
			return Response({"detail": "Unit not found."}, status=status.HTTP_404_NOT_FOUND)
		if unit.tenancies.filter(status=Tenancy.Status.ACTIVE).exists():
			return Response(
				{"detail": "Cannot delete unit with active tenancy."},
				status=status.HTTP_400_BAD_REQUEST,
			)
		unit.delete()
		return Response({"success": True})


class AvailableUnitListView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request, property_id):
		prop = _owner_property_or_404(request.user, property_id)
		if not prop:
			return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

		unit_type = request.query_params.get("unit_type")
		active_unit_ids = Tenancy.objects.filter(
			property=prop,
			status=Tenancy.Status.ACTIVE,
			unit__isnull=False,
		).values_list("unit_id", flat=True)

		units = prop.units.exclude(id__in=active_unit_ids)
		if unit_type:
			units = units.filter(unit_type=unit_type)
		return Response(UnitSerializer(units.order_by("name"), many=True).data)


class PropertyDocumentListCreateView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request, property_id):
		prop = _owner_property_or_404(request.user, property_id)
		if not prop:
			return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)
		docs = prop.documents.all()
		return Response(PropertyDocumentSerializer(docs, many=True, context={"request": request}).data)

	def post(self, request, property_id):
		prop = _owner_property_or_404(request.user, property_id)
		if not prop:
			return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

		serializer = PropertyDocumentSerializer(data=request.data, context={"request": request})
		serializer.is_valid(raise_exception=True)
		doc = serializer.save(property=prop, uploaded_by=request.user)
		return Response(PropertyDocumentSerializer(doc, context={"request": request}).data, status=status.HTTP_201_CREATED)


class PropertyDocumentDetailView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def delete(self, request, property_id, doc_id):
		prop = _owner_property_or_404(request.user, property_id)
		if not prop:
			return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)
		doc = prop.documents.filter(id=doc_id).first()
		if not doc:
			return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)
		doc.delete()
		return Response({"success": True})


class PropertyStatsView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request, property_id):
		prop = _owner_property_or_404(request.user, property_id)
		if not prop:
			return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

		total_units = prop.units.count()
		occupied = prop.tenancies.filter(status=Tenancy.Status.ACTIVE, unit__isnull=False).count()
		vacant = max(total_units - occupied, 0)
		occupancy_rate = round((occupied / total_units) * 100, 2) if total_units else 0

		payment_qs = Payment.objects.filter(property=prop)
		monthly_revenue = prop.units.aggregate(total=Sum("rent_amount")).get("total") or Decimal("0")
		collected = payment_qs.filter(status=Payment.Status.PAID).aggregate(total=Sum("paid_amount")).get("total") or Decimal("0")
		pending = payment_qs.exclude(status=Payment.Status.PAID).aggregate(total=Sum("total")).get("total") or Decimal("0")

		return Response(
			{
				"total_units": total_units,
				"occupied": occupied,
				"vacant": vacant,
				"occupancy_rate": occupancy_rate,
				"monthly_revenue": monthly_revenue,
				"collected": collected,
				"pending": pending,
			}
		)


class OccupancyReportView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request, property_id):
		prop = _owner_property_or_404(request.user, property_id)
		if not prop:
			return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

		total_units = prop.units.count()
		occupied = prop.tenancies.filter(status=Tenancy.Status.ACTIVE, unit__isnull=False).count()
		current_rate = round((occupied / total_units) * 100, 2) if total_units else 0

		today = date.today()
		months = []
		for offset in range(5, -1, -1):
			month = (today.month - offset - 1) % 12 + 1
			year = today.year + ((today.month - offset - 1) // 12)
			months.append({"month": f"{year}-{month:02d}", "rate": current_rate})

		return Response({"monthly": months, "current_rate": current_rate})


class PaymentConfigUpdateView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def patch(self, request, property_id):
		prop = _owner_property_or_404(request.user, property_id)
		if not prop:
			return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

		config, _ = PaymentConfig.objects.get_or_create(property=prop)
		serializer = PaymentConfigSerializer(config, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data)
