from apps.common.util.logging_util import log_method
from apps.project.entity.models import Project


class ProjectDao:
    @staticmethod
    @log_method
    def list_all():
        return Project.objects.all().order_by("-created_at")

    @staticmethod
    @log_method
    def get_by_id(project_id: int):
        return Project.objects.filter(id=project_id).first()

    @staticmethod
    @log_method
    def get_by_chat_group_id(chat_group_id: str):
        return Project.objects.filter(chat_group_id=chat_group_id).first()

    @staticmethod
    @log_method
    def create(**kwargs):
        return Project.objects.create(**kwargs)

    @staticmethod
    @log_method
    def update(project: Project, **kwargs):
        for k, v in kwargs.items():
            setattr(project, k, v)
        project.save()
        return project
