import csv
import uuid
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancies.models import Tenancy
from users.models import User

from .models import MpesaTransaction, Payment
from .serializers import PaymentSerializer


def _payments_for_user(user):
	qs = Payment.objects.select_related("tenancy", "tenancy__user", "unit", "property")
	if user.role == User.Role.OWNER:
		qs = qs.filter(property__owner=user)
	elif user.role == User.Role.TENANT:
		qs = qs.filter(tenancy__user=user)
	return qs


class PaymentListView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		qs = _payments_for_user(request.user)
		status_filter = request.query_params.get("status")
		property_id = request.query_params.get("property_id")
		period = request.query_params.get("period")
		search = request.query_params.get("search")
		ordering = request.query_params.get("ordering")

		if status_filter:
			qs = qs.filter(status=status_filter)
		if property_id:
			qs = qs.filter(property_id=property_id)
		if period:
			qs = qs.filter(period=period)
		if search:
			qs = qs.filter(tenancy__user__full_name__icontains=search) | qs.filter(unit__name__icontains=search)
		if ordering:
			qs = qs.order_by(ordering)

		return Response(PaymentSerializer(qs, many=True).data)


class PaymentDetailView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request, payment_id):
		payment = _payments_for_user(request.user).filter(id=payment_id).first()
		if not payment:
			return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
		return Response(PaymentSerializer(payment).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def initiate_stk_push(request):
	amount = Decimal(str(request.data.get("amount", 0)))
	phone = request.data.get("phone") or request.data.get("phone_number", "")
	account_ref = request.data.get("account_ref") or request.data.get("account_reference", "RENT")
	description = request.data.get("description") or request.data.get("transaction_desc", "Rent payment")

	if amount <= 0 or not phone:
		return Response(
			{"detail": "Valid amount and phone are required."},
			status=status.HTTP_400_BAD_REQUEST,
		)

	tenancy = Tenancy.objects.filter(user=request.user).first()
	if not tenancy and request.data.get("tenant_id"):
		tenancy = Tenancy.objects.filter(id=request.data.get("tenant_id")).first()
	if not tenancy:
		return Response({"detail": "Tenant profile not found."}, status=status.HTTP_400_BAD_REQUEST)

	checkout_id = f"ws_CO_{uuid.uuid4().hex[:20]}"
	payment = Payment.objects.create(
		tenancy=tenancy,
		property=tenancy.property,
		unit=tenancy.unit,
		period=timezone.now().strftime("%Y-%m"),
		amount=amount,
		fine=0,
		paid_amount=0,
		status=Payment.Status.PENDING,
		payment_method=Payment.Method.MPESA,
		mpesa_checkout_request_id=checkout_id,
		metadata={"account_ref": account_ref, "description": description, "phone": phone},
	)

	MpesaTransaction.objects.create(
		payment=payment,
		merchant_request_id=f"mr_{uuid.uuid4().hex[:16]}",
		checkout_request_id=checkout_id,
		result_code=0,
		result_desc="Pending customer authorization",
		phone_number=phone,
	)

	return Response(
		{
			"checkout_request_id": checkout_id,
			"merchant_request_id": payment.mpesa_transaction.merchant_request_id,
			"customer_message": "STK push sent. Complete payment on your phone.",
		}
	)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def check_stk_status(request, checkout_request_id):
	transaction = MpesaTransaction.objects.select_related("payment").filter(
		checkout_request_id=checkout_request_id
	).first()
	if not transaction:
		return Response({"detail": "Transaction not found."}, status=status.HTTP_404_NOT_FOUND)

	payment = transaction.payment

	# Simulate asynchronous callback completion for development parity with frontend polling.
	if payment.status == Payment.Status.PENDING and timezone.now() - payment.created_at > timedelta(seconds=8):
		receipt = f"NLF{uuid.uuid4().hex[:8].upper()}"
		payment.status = Payment.Status.PAID
		payment.paid_amount = payment.total
		payment.receipt_number = receipt
		payment.paid_at = timezone.now()
		payment.save(update_fields=["status", "paid_amount", "receipt_number", "paid_at", "updated_at"])
		transaction.mpesa_receipt_number = receipt
		transaction.transaction_date = timezone.now().strftime("%Y%m%d%H%M%S")
		transaction.result_desc = "The service request is processed successfully."
		transaction.save(update_fields=["mpesa_receipt_number", "transaction_date", "result_desc", "updated_at"])

	if payment.status == Payment.Status.PAID:
		return Response(
			{
				"status": "completed",
				"receipt_number": payment.receipt_number,
				"amount": payment.paid_amount,
			}
		)

	if payment.status in [Payment.Status.OVERDUE, Payment.Status.WAIVED]:
		return Response({"status": "failed", "result_desc": "Payment not completed."})

	return Response({"status": "pending"})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def record_manual_payment(request):
	tenant_id = request.data.get("tenant_id")
	amount = Decimal(str(request.data.get("amount", 0)))
	if not tenant_id or amount <= 0:
		return Response(
			{"detail": "tenant_id and valid amount are required."},
			status=status.HTTP_400_BAD_REQUEST,
		)

	tenancy = Tenancy.objects.filter(id=tenant_id).first()
	if not tenancy:
		return Response({"detail": "Tenant not found."}, status=status.HTTP_404_NOT_FOUND)

	payment = Payment.objects.create(
		tenancy=tenancy,
		property=tenancy.property,
		unit=tenancy.unit,
		period=timezone.now().strftime("%Y-%m"),
		amount=amount,
		fine=0,
		paid_amount=amount,
		status=Payment.Status.PAID,
		payment_method=Payment.Method.MANUAL,
		receipt_number=request.data.get("receipt_number", ""),
		paid_at=request.data.get("date") or timezone.now(),
		metadata={"notes": request.data.get("notes", "")},
	)
	return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_receipt(request, payment_id):
	payment = _payments_for_user(request.user).filter(id=payment_id).first()
	if not payment:
		return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
	return Response(
		{
			"receipt_number": payment.receipt_number,
			"date": payment.paid_at,
			"amount": payment.amount,
			"fine": payment.fine,
			"total": payment.total,
			"tenant_name": payment.tenancy.user.full_name or payment.tenancy.user.email,
			"unit_name": payment.unit.name if payment.unit else None,
			"period": payment.period,
			"payment_method": payment.payment_method,
		}
	)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def waive_fine(request, payment_id):
	payment = _payments_for_user(request.user).filter(id=payment_id).first()
	if not payment:
		return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
	payment.fine = 0
	payment.status = Payment.Status.WAIVED
	payment.save(update_fields=["fine", "status", "updated_at"])
	return Response(PaymentSerializer(payment).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_payment_summary(request):
	payments = _payments_for_user(request.user)
	property_id = request.query_params.get("property_id")
	if property_id:
		payments = payments.filter(property_id=property_id)

	total_paid = payments.filter(status=Payment.Status.PAID).aggregate(total=Sum("paid_amount")).get("total") or Decimal("0")
	total_overdue = payments.filter(status=Payment.Status.OVERDUE).aggregate(total=Sum("total")).get("total") or Decimal("0")
	total_pending = payments.filter(status=Payment.Status.PENDING).aggregate(total=Sum("total")).get("total") or Decimal("0")

	return Response(
		{
			"total_paid": total_paid,
			"total_overdue": total_overdue,
			"total_pending": total_pending,
		}
	)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_overdue_payments(request):
	overdue = _payments_for_user(request.user).filter(status=Payment.Status.OVERDUE)
	return Response(PaymentSerializer(overdue, many=True).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_upcoming_payments(request):
	upcoming = _payments_for_user(request.user).filter(status=Payment.Status.PENDING).order_by("created_at")[:20]
	return Response(PaymentSerializer(upcoming, many=True).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def generate_statement(request):
	payments = _payments_for_user(request.user).order_by("-created_at")
	tenant_id = request.query_params.get("tenant_id")
	property_id = request.query_params.get("property_id")
	if tenant_id:
		payments = payments.filter(tenancy_id=tenant_id)
	if property_id:
		payments = payments.filter(property_id=property_id)

	response = HttpResponse(content_type="text/csv")
	response["Content-Disposition"] = "attachment; filename=payment_statement.csv"

	writer = csv.writer(response)
	writer.writerow(["Tenant", "Unit", "Period", "Amount", "Fine", "Total", "Status", "Paid At", "Receipt"])
	for p in payments:
		writer.writerow(
			[
				p.tenancy.user.full_name or p.tenancy.user.email,
				p.unit.name if p.unit else "",
				p.period,
				p.amount,
				p.fine,
				p.total,
				p.status,
				p.paid_at,
				p.receipt_number,
			]
		)

	return response
