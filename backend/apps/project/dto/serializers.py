from rest_framework import serializers

from apps.project.entity.models import Project


class ProjectSerializer(serializers.ModelSerializer):
    projectName = serializers.CharField(source="project_name")
    projectPath = serializers.CharField(source="project_path")
    chatGroupId = serializers.CharField(source="chat_group_id")
    conventionPath = serializers.CharField(source="convention_path", required=False, allow_blank=True)
    gitRemoteUrl = serializers.CharField(source="git_remote_url", required=False, allow_blank=True)
    gitBranch = serializers.CharField(source="git_branch", required=False, allow_blank=True)
    gitPushEnabled = serializers.BooleanField(source="git_push_enabled", required=False)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "projectName", "projectPath", "chatGroupId", "conventionPath",
            "gitRemoteUrl", "gitBranch", "gitPushEnabled", "createdAt",
        ]
