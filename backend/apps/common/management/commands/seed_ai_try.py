from django.core.management.base import BaseCommand

from apps.auth_app.dao.user_dao import UserDao
from apps.common.constant.task_constants import TaskStatus, TaskStep
from apps.project.dao.project_dao import ProjectDao
from apps.task.dao.task_dao import TaskDao

TITLE = "【AI测试】看板空列显示引导提示"

PRD = """## 背景
新用户打开需求看板时，空的阶段列只有「暂无任务」，不够友好。

## 验收标准
1. Kanban 每个空列显示简短引导文案（如「拖拽或新建需求到此阶段」）
2. 有任务时仍显示任务卡片，不受影响
3. 文案使用中文，样式与现有看板一致
4. 仅改 frontend/src/views/KanbanView.vue 及必要样式

## 约束
- 不改动后端 API
- 不引入新依赖"""


class Command(BaseCommand):
    help = "Create one AI test task (Requirement_Refinement / Init)"

    def handle(self, *args, **options):
        project = ProjectDao.list_all().first()
        if not project:
            self.stderr.write("请先运行: python manage.py seed_demo")
            return

        if TaskDao.list_by_project(project.id).filter(title=TITLE).exists():
            task = TaskDao.list_by_project(project.id).filter(title=TITLE).first()
            self.stdout.write(self.style.WARNING(f"任务已存在: #{task.id} {TITLE}"))
            self.stdout.write("如需重来，请在前端删除该任务或改标题后重新运行")
            return

        admin = UserDao.get_by_username("admin")

        task = TaskDao.create(
            project=project,
            created_by=admin,
            title=TITLE,
            acceptance_criteria=PRD,
            current_step=TaskStep.REQUIREMENT_REFINEMENT,
            current_status=TaskStatus.INIT,
            affected_files={"predicted_by_agent": [], "confirmed_by_human": []},
            sub_tasks=[],
            execution_logs="",
        )
        self.stdout.write(self.style.SUCCESS(f"已创建 AI 测试任务 #{task.id}"))
        self.stdout.write(f"项目: {project.project_name}")
        self.stdout.write("打开看板 → 等待约 15~30 秒 → PM Agent 自动拆解 → 进入人工 Review 1")
