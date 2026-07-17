from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from apps.auth_app.dao.user_dao import UserDao
from apps.common.constant.task_constants import TaskStatus, TaskStep
from apps.project.dao.project_dao import ProjectDao
from apps.task.dao.task_dao import TaskDao

TASK_TITLE = "【测试】用户注册与登录完整流程"

ACCEPTANCE = """## 背景
平台需要支持新用户注册、登录及基础资料展示，供后续 Agent Loop 全流程测试。

## 验收标准
1. 提供注册页：用户名、密码、确认密码、可选昵称
2. 提供登录页：用户名 + 密码，支持错误提示
3. 登录成功后跳转首页，展示当前用户名
4. 后端提供 /api/auth/register/ 与 /api/auth/login/ 接口
5. 密码 bcrypt 哈希存储，禁止明文
6. 补充 README 中的本地启动说明
"""

SUB_TASKS = [
    {"id": "st-1", "title": "设计 User 模型与迁移", "completed": True},
    {"id": "st-2", "title": "实现注册/登录 API 与 JWT", "completed": True},
    {"id": "st-3", "title": "前端 RegisterView / LoginView", "completed": True},
    {"id": "st-4", "title": "首页展示当前用户与退出", "completed": True},
    {"id": "st-5", "title": "补充单元测试与 README", "completed": True},
]

AFFECTED_FILES = {
    "predicted_by_agent": [
        "backend/apps/auth_app/entity/models.py",
        "backend/apps/auth_app/controller/views.py",
        "backend/apps/auth_app/service/auth_service.py",
        "frontend/src/views/RegisterView.vue",
        "frontend/src/views/LoginView.vue",
        "frontend/src/stores/auth.ts",
    ],
    "confirmed_by_human": [
        "backend/apps/auth_app/entity/models.py",
        "backend/apps/auth_app/controller/views.py",
        "backend/apps/auth_app/service/auth_service.py",
        "frontend/src/views/RegisterView.vue",
        "frontend/src/views/LoginView.vue",
        "frontend/src/stores/auth.ts",
    ],
}

CODE_DIFFS = [
    {
        "filePath": "backend/apps/auth_app/service/auth_service.py",
        "original": "# TODO: auth service\n",
        "modified": (
            '"""Auth service for register/login."""\n\n'
            "from django.contrib.auth.hashers import check_password, make_password\n\n\n"
            "class AuthService:\n"
            "    @staticmethod\n"
            "    def register(username: str, password: str, display_name: str = ''):\n"
            "        ...\n\n"
            "    @staticmethod\n"
            "    def login(username: str, password: str):\n"
            "        ...\n"
        ),
        "diffText": "+class AuthService: register/login helpers",
    },
    {
        "filePath": "frontend/src/views/LoginView.vue",
        "original": "<!-- legacy login -->\n",
        "modified": (
            "<template>\n"
            "  <div class=\"login-page\">\n"
            "    <el-form @submit.prevent=\"onSubmit\">\n"
            "      <el-input v-model=\"username\" placeholder=\"用户名\" />\n"
            "      <el-input v-model=\"password\" type=\"password\" placeholder=\"密码\" />\n"
            "      <el-button type=\"primary\" native-type=\"submit\">登录</el-button>\n"
            "    </el-form>\n"
            "  </div>\n"
            "</template>\n"
        ),
        "diffText": "+LoginView with username/password form",
    },
]

BASE_TS = datetime.now() - timedelta(hours=2)


def _ts(offset_min: int) -> str:
    return (BASE_TS + timedelta(minutes=offset_min)).isoformat()


def _step_history():
    return [
        {
            "step": TaskStep.REQUIREMENT_REFINEMENT,
            "run": 1,
            "startedAt": _ts(0),
            "finishedAt": _ts(8),
            "acceptanceCriteria": ACCEPTANCE,
            "subTasks": [
                {"id": "st-1", "title": "设计 User 模型与迁移", "completed": False},
                {"id": "st-2", "title": "实现注册/登录 API", "completed": False},
                {"id": "st-3", "title": "前端登录注册页", "completed": False},
            ],
            "affectedFiles": {
                "predicted_by_agent": AFFECTED_FILES["predicted_by_agent"],
                "confirmed_by_human": [],
            },
            "executionLogs": (
                "[10:00:01] === 开始 需求拆解 第1轮 ===\n"
                "[10:00:02] PM Agent: 开始需求拆解...\n"
                "[10:00:05] Agent 模式: anthropic_api\n"
                "[10:00:18] PM Agent: 拆解完成 (Anthropic API)，等待人工 Review 1\n"
                "[10:00:19] 自动 Review (人工 Review 1): 通过 — 子任务覆盖注册/登录/API\n"
            ),
            "agentMeta": {"source": "anthropic_api", "fallback": False, "model": "claude-sonnet-4-6"},
        },
        {
            "step": TaskStep.HUMAN_REVIEW_1,
            "run": 1,
            "finishedAt": _ts(15),
            "acceptanceCriteria": ACCEPTANCE,
            "subTasks": SUB_TASKS[:3],
            "affectedFiles": AFFECTED_FILES,
            "reviewOpinion": "子任务 4、5 需补充首页展示与测试说明，已手动添加。",
            "approved": True,
            "executionLogs": "",
        },
        {
            "step": TaskStep.AUTO_DEVELOPMENT,
            "run": 1,
            "startedAt": _ts(16),
            "finishedAt": _ts(45),
            "acceptanceCriteria": ACCEPTANCE,
            "subTasks": SUB_TASKS,
            "affectedFiles": AFFECTED_FILES,
            "codeDiffs": CODE_DIFFS,
            "executionLogs": (
                "[10:16:01] === 开始 自动开发 第1轮 ===\n"
                "[10:16:02] Coding Agent: 启动 (anthropic_api)...\n"
                "[10:16:30] Coding Agent: diff 已生成 (Anthropic API)，等待 Review 2\n"
                "[10:16:31] 自动 Review (人工 Review 2): 通过 — 代码结构符合偏好\n"
            ),
            "agentMeta": {"source": "anthropic_api", "mode": "anthropic_api", "fallback": False},
        },
        {
            "step": TaskStep.HUMAN_REVIEW_2,
            "run": 1,
            "finishedAt": _ts(50),
            "acceptanceCriteria": ACCEPTANCE,
            "subTasks": SUB_TASKS,
            "affectedFiles": AFFECTED_FILES,
            "codeDiffs": CODE_DIFFS,
            "reviewOpinion": "代码 diff 符合预期，同意合并发布。",
            "approved": True,
            "executionLogs": "",
        },
        {
            "step": TaskStep.COMMIT_PUSH,
            "run": 1,
            "startedAt": _ts(51),
            "finishedAt": _ts(65),
            "acceptanceCriteria": ACCEPTANCE,
            "subTasks": SUB_TASKS,
            "affectedFiles": AFFECTED_FILES,
            "codeDiffs": CODE_DIFFS,
            "executionLogs": (
                "[10:51:01] === 开始 提交发布 第1轮 ===\n"
                "[10:51:05] Apply Agent: 将 code_diffs 写入项目目录...\n"
                "[10:51:20] CI Agent: 运行项目自测...\n"
                "[10:52:10] Git Agent: commit & push...\n"
                "[10:52:30] Git commit: [main abc1234] agent-loop #N: 用户注册与登录\n"
                "[10:52:45] Deploy Agent: 发布流程完成\n"
            ),
        },
    ]


EXECUTION_LOGS = (
    "[10:00:01] === 开始 需求拆解 第1轮 ===\n"
    "[10:00:02] PM Agent: 开始需求拆解...\n"
    "[10:00:18] PM Agent: 拆解完成，等待人工 Review 1\n"
    "[10:15:00] Review 审计: review1_approved — 操作人 admin\n"
    "[10:15:01] Review 1 通过，进入自动开发\n"
    "[10:16:01] === 开始 自动开发 第1轮 ===\n"
    "[10:16:30] Coding Agent: diff 已生成，等待 Review 2\n"
    "[10:50:00] Review 审计: review2_approved — 操作人 admin\n"
    "[10:50:01] Review 2 通过，进入提交发布\n"
    "[10:51:01] === 开始 提交发布 第1轮 ===\n"
    "[10:52:45] Deploy Agent: 发布流程完成\n"
)


class Command(BaseCommand):
    help = "Seed one finished test task with full data at every workflow stage"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Recreate if task title already exists")

    def handle(self, *args, **options):
        project = ProjectDao.list_all().first()
        if not project:
            self.stderr.write("请先运行: python manage.py seed_demo")
            return

        admin = UserDao.get_by_username("admin")
        if not admin:
            self.stderr.write("请先运行: python manage.py seed_demo")
            return

        existing = TaskDao.list_by_project(project.id).filter(title=TASK_TITLE).first()
        if existing:
            if not options["force"]:
                self.stdout.write(self.style.WARNING(f"任务已存在 #{existing.id}，使用 --force 重建"))
                return
            TaskDao.delete(existing)
            self.stdout.write(f"Deleted existing task #{existing.id}")

        checkpoint = {
            "phase": "finished",
            "finished_at": _ts(65),
            "step_runs": {
                TaskStep.REQUIREMENT_REFINEMENT: 1,
                TaskStep.HUMAN_REVIEW_1: 1,
                TaskStep.AUTO_DEVELOPMENT: 1,
                TaskStep.HUMAN_REVIEW_2: 1,
                TaskStep.COMMIT_PUSH: 1,
            },
            "execution_history": _step_history(),
            "review_audit": [
                {"action": "review1_approved", "user_id": admin.id, "username": "admin", "at": _ts(15)},
                {"action": "review2_approved", "user_id": admin.id, "username": "admin", "at": _ts(50)},
            ],
            "opinion_history": [
                {
                    "step": TaskStep.HUMAN_REVIEW_1,
                    "opinion": "子任务 4、5 需补充首页展示与测试说明，已手动添加。",
                    "reject": False,
                    "user_id": admin.id,
                    "username": "admin",
                    "at": _ts(14),
                },
                {
                    "step": TaskStep.HUMAN_REVIEW_2,
                    "opinion": "代码 diff 符合预期，同意合并发布。",
                    "reject": False,
                    "user_id": admin.id,
                    "username": "admin",
                    "at": _ts(49),
                },
            ],
            "auto_review": {
                "passed": True,
                "summary": "自动 Review 通过：子任务完整，diff 覆盖 auth 前后端",
                "issues": [],
                "skipped": False,
                "step": TaskStep.HUMAN_REVIEW_2,
                "at": _ts(48),
            },
            "agent_meta": {
                "requirement_refinement": {
                    "source": "anthropic_api",
                    "fallback": False,
                    "model": "claude-sonnet-4-6",
                },
                "auto_development": {
                    "source": "anthropic_api",
                    "fallback": False,
                    "mode": "anthropic_api",
                },
            },
        }

        task = TaskDao.create(
            project=project,
            created_by=admin,
            title=TASK_TITLE,
            acceptance_criteria=ACCEPTANCE,
            current_step=TaskStep.COMMIT_PUSH,
            current_status=TaskStatus.FINISHED,
            affected_files=AFFECTED_FILES,
            sub_tasks=SUB_TASKS,
            execution_logs=EXECUTION_LOGS,
            code_diffs=CODE_DIFFS,
            review_opinion="代码 diff 符合预期，同意合并发布。",
            checkpoint=checkpoint,
        )

        self.stdout.write(self.style.SUCCESS(
            f"Created full test task #{task.id}: {TASK_TITLE}\n"
            f"  项目: {project.project_name}\n"
            f"  状态: {task.current_step} / {task.current_status}\n"
            f"  执行历史: {len(checkpoint['execution_history'])} 个阶段快照\n"
            f"  打开工作台查看步骤 1-5 详情"
        ))
