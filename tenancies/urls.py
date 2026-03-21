from django.urls import path

from .views import (
    TenantDetailView,
    TenantLeaseView,
    TenantMaintenanceDetailView,
    TenantMaintenanceListCreateView,
    TenantPaymentsView,
    TenantRatingsView,
    TenantTerminateView,
    TenantsInviteView,
    TenantsListView,
    me_lease,
    me_notices,
    me_payments,
    me_profile,
    send_overdue_reminders,
    send_reminders,
)

urlpatterns = [
    path("tenants/", TenantsListView.as_view()),
    path("tenants/invite/", TenantsInviteView.as_view()),
    path("tenants/send-reminders/", send_reminders),
    path("tenants/send-overdue-reminders/", send_overdue_reminders),
    path("tenants/me/", me_profile),
    path("tenants/me/lease/", me_lease),
    path("tenants/me/payments/", me_payments),
    path("tenants/me/notices/", me_notices),
    path("tenants/<tenant_id>/", TenantDetailView.as_view()),
    path("tenants/<tenant_id>/terminate/", TenantTerminateView.as_view()),
    path("tenants/<tenant_id>/payments/", TenantPaymentsView.as_view()),
    path("tenants/<tenant_id>/lease/", TenantLeaseView.as_view()),
    path("tenants/<tenant_id>/maintenance/", TenantMaintenanceListCreateView.as_view()),
    path(
        "tenants/<tenant_id>/maintenance/<uuid:request_id>/",
        TenantMaintenanceDetailView.as_view(),
    ),
    path("tenants/<tenant_id>/ratings/", TenantRatingsView.as_view()),
]
