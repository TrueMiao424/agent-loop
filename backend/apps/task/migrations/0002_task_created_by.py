from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_tasks_to_admin(apps, schema_editor):
    Task = apps.get_model("task", "Task")
    User = apps.get_model("auth_app", "User")
    admin = User.objects.filter(username="admin").first()
    if admin:
        Task.objects.filter(created_by__isnull=True).update(created_by=admin)


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0001_initial"),
        ("task", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_tasks",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(assign_tasks_to_admin, migrations.RunPython.noop),
    ]
