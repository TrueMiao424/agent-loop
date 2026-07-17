from django.urls import path

from apps.webhook.controller.views import WebhookListCreateView

urlpatterns = [
    path("", WebhookListCreateView.as_view()),
]
