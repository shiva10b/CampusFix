"""Top-level URL routing for CampusFix.

Account routes intentionally come before the public core routes so Batch 2
authentication and dashboard paths are resolved by the active project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Batch 2: registration, authentication, dashboards, and profile pages.
    path("", include("accounts.urls")),
    # Batch 3: student complaint submission and ticket tracking.
    path("", include("complaints.urls")),
    # Batch 1: landing page and health endpoint.
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "core.views.custom_404"
handler403 = "core.views.custom_403"
