from django.conf import settings as django_settings
from django.db import models


class SystemSetting(models.Model):
    key = models.CharField(max_length=128, primary_key=True)
    value = models.TextField(blank=True, default="")

    class Meta:
        db_table = "system_settings"


class UserLlmSetting(models.Model):
    """每个用户独立的 Agent LLM 配置。"""

    user = models.OneToOneField(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="llm_setting",
    )
    anthropic_auth_token = models.TextField(blank=True, default="")
    anthropic_base_url = models.CharField(max_length=512, blank=True, default="")
    anthropic_model = models.CharField(max_length=128, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_llm_settings"
