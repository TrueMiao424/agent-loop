from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.auth_app.dao.user_dao import UserDao
from apps.project.dao.project_dao import ProjectDao
from apps.project.util.project_path_util import ensure_project_directory
from apps.settings_app.dao.settings_dao import SettingsDao

DEFAULT_DEMO_REPO = Path(settings.BASE_DIR).parent / "demo-repo"


class Command(BaseCommand):
    help = "Seed demo data"

    def handle(self, *args, **options):
        if not UserDao.get_by_username("admin"):
            UserDao.create_user("admin", "admin123", "管理员", "admin")
            self.stdout.write("Created admin/admin123")

        demo_path = str(DEFAULT_DEMO_REPO.resolve())
        ensure_project_directory(demo_path)

        if not ProjectDao.list_all().exists():
            ProjectDao.create(
                project_name="Agent Loop Demo",
                project_path=demo_path,
                chat_group_id="oc_demo_group_001",
                convention_path=".github/coding_style.md",
            )
            self.stdout.write(f"Created demo project -> {demo_path}")
        else:
            project = ProjectDao.list_all().first()
            if project.project_path != demo_path:
                ProjectDao.update(project, project_path=demo_path)
                self.stdout.write(f"Updated demo project path -> {demo_path}")

        SettingsDao.set_many({
            "feishu_app_id": "",
            "feishu_app_secret": "",
        })
        self.stdout.write(self.style.SUCCESS("Seed complete"))
