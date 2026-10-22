from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core import views as core_views
from apps.core import website

api_v1 = [
    path("health/", core_views.health, name="health"),
    path("health/ready/", core_views.ready, name="health-ready"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.organizations.urls")),
    path("", include("apps.people.urls")),
    path("", include("apps.events.urls")),
    path("", include("apps.funds.urls")),
    path("", include("apps.contributions.urls")),
    path("", include("apps.payments.urls")),
    path("", include("apps.receipts.urls")),
    path("", include("apps.expenses.urls")),
    path("", include("apps.reports.urls")),
    path("", include("apps.audit.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.portal.urls")),
    path("", include("apps.gateway.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

urlpatterns = [
    path("api/v1/", include(api_v1)),
    path("django-admin/", admin.site.urls),
]

if settings.STORAGE_BACKEND == "database":
    urlpatterns.append(
        re_path(r"^media/orgs/(?P<org_id>[0-9a-f-]+)/logo/(?P<filename>[0-9a-f]+\.png)$", website.logo, name="logo"),
    )
elif settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.WEBSITE_DIR:
    # Last: anything that is not the API, the admin or an uploaded file is a website page.
    urlpatterns.append(re_path(r"^(?!api/|django-admin/|media/|static/).*$", website.index, name="website"))
