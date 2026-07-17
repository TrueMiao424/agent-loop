from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("project", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="git_remote_url",
            field=models.CharField(blank=True, default="", max_length=512),
        ),
        migrations.AddField(
            model_name="project",
            name="git_branch",
            field=models.CharField(blank=True, default="main", max_length=128),
        ),
        migrations.AddField(
            model_name="project",
            name="git_push_enabled",
            field=models.BooleanField(default=False),
        ),
    ]
