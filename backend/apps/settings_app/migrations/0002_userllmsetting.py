# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("settings_app", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserLlmSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("anthropic_auth_token", models.TextField(blank=True, default="")),
                ("anthropic_base_url", models.CharField(blank=True, default="", max_length=512)),
                ("anthropic_model", models.CharField(blank=True, default="", max_length=128)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="llm_setting",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "user_llm_settings",
            },
        ),
    ]
