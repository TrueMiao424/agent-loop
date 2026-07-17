from rest_framework import serializers

from apps.webhook.entity.models import WebhookMessage


class WebhookSerializer(serializers.ModelSerializer):
    projectId = serializers.IntegerField(source="project_id", allow_null=True)
    taskId = serializers.IntegerField(source="task_id", allow_null=True)
    webhookUrl = serializers.CharField(source="webhook_url")
    isHuman = serializers.BooleanField(source="is_human")
    senderName = serializers.CharField(source="sender_name")
    timestamp = serializers.DateTimeField()

    class Meta:
        model = WebhookMessage
        fields = ["id", "timestamp", "projectId", "taskId", "webhookUrl", "title", "message", "status", "isHuman", "senderName"]
