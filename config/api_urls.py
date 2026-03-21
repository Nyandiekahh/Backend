from django.urls import include, path

urlpatterns = [
    path("auth/", include("users.urls")),
    path("", include("properties.urls")),
    path("", include("tenancies.urls")),
    path("", include("leases.urls")),
    path("", include("payments.urls")),
    path("", include("maintenance.urls")),
    path("", include("communications.urls")),
]
