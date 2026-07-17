from rest_framework import serializers

from apps.project.dto.serializers import ProjectSerializer
from apps.task.entity.models import Task


class TaskSerializer(serializers.ModelSerializer):
    projectId = serializers.IntegerField(source="project_id")
    acceptanceCriteria = serializers.CharField(source="acceptance_criteria", required=False, allow_blank=True)
    currentStep = serializers.CharField(source="current_step", read_only=True)
    currentStatus = serializers.CharField(source="current_status", read_only=True)
    affectedFiles = serializers.JSONField(source="affected_files", required=False)
    subTasks = serializers.JSONField(source="sub_tasks", required=False)
    executionLogs = serializers.CharField(source="execution_logs", read_only=True)
    codeDiffs = serializers.JSONField(source="code_diffs", required=False)
    manualEdits = serializers.JSONField(source="manual_edits", required=False)
    failReason = serializers.CharField(source="fail_reason", read_only=True)
    reviewOpinion = serializers.CharField(source="review_opinion", required=False, allow_blank=True)
    createdById = serializers.IntegerField(source="created_by_id", read_only=True, allow_null=True)
    createdByUsername = serializers.SerializerMethodField()
    agentMeta = serializers.SerializerMethodField()
    reviewAudit = serializers.SerializerMethodField()
    executionHistory = serializers.SerializerMethodField()
    autoReview = serializers.SerializerMethodField()
    opinionHistory = serializers.SerializerMethodField()
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    project = ProjectSerializer(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id", "projectId", "title", "acceptanceCriteria", "currentStep", "currentStatus",
            "affectedFiles", "subTasks", "executionLogs", "codeDiffs", "manualEdits",
            "failReason", "reviewOpinion", "createdById", "createdByUsername", "agentMeta", "reviewAudit",
            "executionHistory", "autoReview", "opinionHistory",
            "createdAt", "updatedAt", "project",
        ]

    def get_agentMeta(self, obj):
        return (obj.checkpoint or {}).get("agent_meta", {})

    def get_reviewAudit(self, obj):
        return (obj.checkpoint or {}).get("review_audit", [])

    def get_executionHistory(self, obj):
        return (obj.checkpoint or {}).get("execution_history", [])

    def get_autoReview(self, obj):
        return (obj.checkpoint or {}).get("auto_review", {})

    def get_opinionHistory(self, obj):
        return (obj.checkpoint or {}).get("opinion_history", [])

    def get_createdByUsername(self, obj):
        if obj.created_by_id and obj.created_by:
            return obj.created_by.username
        return None

    def to_internal_value(self, data):
        mapped = dict(data)
        field_map = {
            "projectId": "project_id",
            "acceptanceCriteria": "acceptance_criteria",
            "affectedFiles": "affected_files",
            "subTasks": "sub_tasks",
            "manualEdits": "manual_edits",
            "reviewOpinion": "review_opinion",
        }
        for src, dst in field_map.items():
            if src in mapped:
                mapped[dst] = mapped.pop(src)
        return super().to_internal_value(mapped)
