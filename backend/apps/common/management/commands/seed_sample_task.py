import json

from django.core.management.base import BaseCommand

from apps.auth_app.dao.user_dao import UserDao
from apps.common.constant.task_constants import TaskStatus, TaskStep
from apps.project.dao.project_dao import ProjectDao
from apps.task.dao.task_dao import TaskDao


SAMPLE_REVIEW1 = {
    "title": "示例：登录页增加「记住我」",
    "acceptance_criteria": """## 背景
用户在登录页希望勾选「记住我」后，下次打开站点自动填充用户名。

## 验收标准
1. 登录表单增加「记住我」复选框，默认不勾选
2. 勾选并登录成功后，localStorage 保存 username（不保存密码）
3. 再次打开登录页时自动填充 username
4. 取消勾选后清除 localStorage 中的 username
5. 补充前端单元测试或手工测试说明""",
    "current_step": TaskStep.HUMAN_REVIEW_1,
    "current_status": TaskStatus.INIT,
    "affected_files": {
        "predicted_by_agent": [
            "frontend/src/views/LoginView.vue",
            "frontend/src/stores/auth.ts",
        ],
        "confirmed_by_human": [],
    },
    "sub_tasks": [
        {"id": "st-1", "title": "LoginView 增加 rememberMe 复选框", "completed": False},
        {"id": "st-2", "title": "auth store 读写 localStorage username", "completed": False},
        {"id": "st-3", "title": "页面加载时自动填充用户名", "completed": False},
    ],
    "execution_logs": (
        "[14:00:01] PM Agent: 开始需求拆解...\n"
        "[14:00:03] PM Agent: 拆解完成，等待人工 Review 1\n"
    ),
}

SAMPLE_AUTO = {
    "title": "示例：看板任务卡片显示负责人",
    "acceptance_criteria": """## 需求
Kanban 看板每个任务卡片右下角显示负责人昵称（暂无则显示「未分配」）。

## 验收标准
1. 任务模型增加 assignee 字段（可选）
2. 看板卡片展示 assignee
3. 新建需求时可留空，默认「未分配」""",
    "current_step": TaskStep.REQUIREMENT_REFINEMENT,
    "current_status": TaskStatus.INIT,
    "affected_files": {"predicted_by_agent": [], "confirmed_by_human": []},
    "sub_tasks": [],
    "execution_logs": "",
}


class Command(BaseCommand):
    help = "Seed sample tasks for quick functional testing"

    def handle(self, *args, **options):
        project = ProjectDao.list_all().first()
        if not project:
            self.stderr.write("请先运行: python manage.py seed_demo")
            return

        admin = UserDao.get_by_username("admin")
        created = 0
        for spec in (SAMPLE_REVIEW1, SAMPLE_AUTO):
            exists = TaskDao.list_by_project(project.id).filter(title=spec["title"]).exists()
            if exists:
                self.stdout.write(f"Skip (exists): {spec['title']}")
                continue
            TaskDao.create(
                project=project,
                created_by=admin,
                title=spec["title"],
                acceptance_criteria=spec["acceptance_criteria"],
                current_step=spec["current_step"],
                current_status=spec["current_status"],
                affected_files=spec["affected_files"],
                sub_tasks=spec["sub_tasks"],
                execution_logs=spec["execution_logs"],
            )
            created += 1
            self.stdout.write(f"Created: {spec['title']}")

        self.stdout.write(self.style.SUCCESS(f"Sample tasks ready ({created} new). Project: {project.project_name}"))
