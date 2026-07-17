from rest_framework import serializers

from apps.session.entity.models import AgentSession


class SessionSerializer(serializers.ModelSerializer):
    sessionId = serializers.CharField(source="session_id")
    taskId = serializers.IntegerField(source="task_id")
    projectName = serializers.CharField(source="project_name")
    projectPath = serializers.CharField(source="project_path")
    commandLine = serializers.CharField(source="command_line")
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = AgentSession
        fields = [
            "sessionId", "taskId", "pid", "projectName", "projectPath",
            "commandLine", "inputs", "logs", "status", "createdAt", "updatedAt",
        ]
