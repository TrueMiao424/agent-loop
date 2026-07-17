from django.urls import path

from apps.webhook.controller.views import (
    FeishuChatsListView,
    FeishuLongConnectionLogsView,
    FeishuLongConnectionRestartView,
    FeishuLongConnectionStatusView,
    FeishuWebhookView,
)

urlpatterns = [
    path("webhook/", FeishuWebhookView.as_view()),
    path("long-connection/status/", FeishuLongConnectionStatusView.as_view()),
    path("long-connection/logs/", FeishuLongConnectionLogsView.as_view()),
    path("long-connection/restart/", FeishuLongConnectionRestartView.as_view()),
    path("chats/", FeishuChatsListView.as_view(), name="feishu-chats"),
]
