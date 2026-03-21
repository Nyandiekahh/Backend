from django.urls import path

from .views import (
    AvailableUnitListView,
    OccupancyReportView,
    PaymentConfigUpdateView,
    PropertyDetailView,
    PropertyDocumentDetailView,
    PropertyDocumentListCreateView,
    PropertyListCreateView,
    PropertyStatsView,
    UnitBulkCreateView,
    UnitDetailView,
    UnitListCreateView,
)

urlpatterns = [
    path("properties/", PropertyListCreateView.as_view()),
    path("properties/<uuid:property_id>/", PropertyDetailView.as_view()),
    path("properties/<uuid:property_id>/units/", UnitListCreateView.as_view()),
    path("properties/<uuid:property_id>/units/bulk/", UnitBulkCreateView.as_view()),
    path("properties/<uuid:property_id>/units/available/", AvailableUnitListView.as_view()),
    path("properties/<uuid:property_id>/units/<uuid:unit_id>/", UnitDetailView.as_view()),
    path("properties/<uuid:property_id>/documents/", PropertyDocumentListCreateView.as_view()),
    path("properties/<uuid:property_id>/documents/<uuid:doc_id>/", PropertyDocumentDetailView.as_view()),
    path("properties/<uuid:property_id>/stats/", PropertyStatsView.as_view()),
    path("properties/<uuid:property_id>/occupancy/", OccupancyReportView.as_view()),
    path("properties/<uuid:property_id>/payment-config/", PaymentConfigUpdateView.as_view()),
]
