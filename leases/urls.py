from django.urls import path

from .views import (
    LeaseDetailView,
    LeaseDocumentView,
    LeaseListCreateView,
    renew_lease,
    sign_lease,
    terminate_lease,
)

urlpatterns = [
    path("leases/", LeaseListCreateView.as_view()),
    path("leases/<uuid:lease_id>/", LeaseDetailView.as_view()),
    path("leases/<uuid:lease_id>/sign/", sign_lease),
    path("leases/<uuid:lease_id>/terminate/", terminate_lease),
    path("leases/<uuid:lease_id>/renew/", renew_lease),
    path("leases/<uuid:lease_id>/documents/", LeaseDocumentView.as_view()),
]
