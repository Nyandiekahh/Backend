from django.urls import path

from .views import (
    PaymentDetailView,
    PaymentListView,
    check_stk_status,
    generate_statement,
    get_overdue_payments,
    get_payment_summary,
    get_receipt,
    get_upcoming_payments,
    initiate_stk_push,
    record_manual_payment,
    waive_fine,
)

urlpatterns = [
    path("payments/", PaymentListView.as_view()),
    path("payments/<uuid:payment_id>/", PaymentDetailView.as_view()),
    path("payments/mpesa/stk-push/", initiate_stk_push),
    path("payments/mpesa/status/<str:checkout_request_id>/", check_stk_status),
    path("payments/manual/", record_manual_payment),
    path("payments/<uuid:payment_id>/receipt/", get_receipt),
    path("payments/<uuid:payment_id>/waive-fine/", waive_fine),
    path("payments/summary/", get_payment_summary),
    path("payments/overdue/", get_overdue_payments),
    path("payments/upcoming/", get_upcoming_payments),
    path("payments/statement/", generate_statement),
]
