from django.contrib import admin
from django.urls import include, path

from apps.common.controller.config_views import PublicConfigView
from apps.common.controller.health_views import HealthView
from apps.common.controller.metrics_views import MetricsView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthView.as_view()),
    path("api/config/", PublicConfigView.as_view()),
    path("api/metrics/", MetricsView.as_view()),
    path("api/auth/", include("apps.auth_app.controller.urls")),
    path("api/projects/", include("apps.project.controller.urls")),
    path("api/tasks/", include("apps.task.controller.urls")),
    path("api/sessions/", include("apps.session.controller.urls")),
    path("api/webhooks/", include("apps.webhook.controller.urls")),
    path("api/feishu/", include("apps.webhook.controller.feishu_urls")),
    path("api/settings/", include("apps.settings_app.controller.urls")),
]
