from django.db import models


class Project(models.Model):
    project_name = models.CharField(max_length=255)
    project_path = models.CharField(max_length=512)
    chat_group_id = models.CharField(max_length=128, db_index=True)
    convention_path = models.CharField(max_length=512, blank=True, default="")
    git_remote_url = models.CharField(max_length=512, blank=True, default="")
    git_branch = models.CharField(max_length=128, blank=True, default="main")
    git_push_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "projects"
        indexes = [models.Index(fields=["chat_group_id"])]
