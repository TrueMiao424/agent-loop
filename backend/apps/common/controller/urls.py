from django.urls import path

from apps.common.controller.health_views import HealthView
from apps.common.controller.metrics_views import MetricsView

urlpatterns = [
    path("health/", HealthView.as_view()),
    path("", MetricsView.as_view()),
]
