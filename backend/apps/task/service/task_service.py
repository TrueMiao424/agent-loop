from django.conf import settings

from datetime import datetime

from apps.common.constant.task_constants import TaskStatus, TaskStep
from apps.common.exception.biz_exception import BizException, ErrorCode
from apps.common.util.logging_util import log_method
from apps.project.dao.project_dao import ProjectDao
from apps.session.dao.session_dao import SessionDao
from apps.task.client.llm_client import AnthropicClient
from apps.task.dao.task_dao import TaskDao
from apps.task.service.review_preference_service import ReviewPreferenceService
from apps.task.service.workflow_service import AgentOrchestrator, WorkflowService


class TaskService:
    @staticmethod
    @log_method
    def list_tasks(project_id: int):
        return TaskDao.list_by_project(project_id)

    @staticmethod
    @log_method
    def get_task(task_id: int):
        task = TaskDao.get_by_id(task_id)
        if not task:
            raise BizException("任务不存在", ErrorCode.NOT_FOUND)
        return task

    @staticmethod
    @log_method
    def create_task(
        project_id: int,
        title: str,
        acceptance_criteria: str,
        idempotency_key: str = "",
        created_by=None,
    ):
        if idempotency_key:
            existing = TaskDao.get_idempotency(idempotency_key)
            if existing:
                return TaskDao.get_by_id(existing.task_id)
        if not created_by:
            raise BizException("未登录，无法创建任务", ErrorCode.PARAM_ERROR)
        if not AnthropicClient.is_configured(created_by.id):
            raise BizException("请先在「配置管理」填写您的 API Key", ErrorCode.PARAM_ERROR)
        project = ProjectDao.get_by_id(project_id)
        if not project:
            raise BizException("项目不存在", ErrorCode.NOT_FOUND)
        task = TaskDao.create(
            project=project,
            created_by=created_by,
            title=title,
            acceptance_criteria=acceptance_criteria,
            current_step=TaskStep.REQUIREMENT_REFINEMENT,
            current_status=TaskStatus.INIT,
            affected_files={"predicted_by_agent": [], "confirmed_by_human": []},
            sub_tasks=[],
            idempotency_key=idempotency_key or "",
        )
        if idempotency_key:
            TaskDao.save_idempotency(idempotency_key, task.id)
        return task

    @staticmethod
    @log_method
    def update_task(task_id: int, data: dict):
        task = TaskService.get_task(task_id)
        for field in ("title", "acceptance_criteria", "affected_files", "sub_tasks", "manual_edits", "review_opinion"):
            if field in data:
                setattr(task, field, data[field])
        return TaskDao.save(task)

    @staticmethod
    @log_method
    def delete_task(task_id: int):
        task = TaskService.get_task(task_id)
        TaskDao.delete(task)

    @staticmethod
    @log_method
    def review1(task_id: int, confirmed_files: list, sub_tasks: list, user=None):
        task = TaskService.get_task(task_id)
        if task.current_step != TaskStep.HUMAN_REVIEW_1:
            raise BizException("当前不在 Review 1 阶段", ErrorCode.PARAM_ERROR)
        if task.current_status != TaskStatus.INIT:
            raise BizException("Review 1 仅能在待处理状态下操作", ErrorCode.PARAM_ERROR)
        files = task.affected_files or {}
        files["confirmed_by_human"] = confirmed_files
        task.affected_files = files
        task.sub_tasks = sub_tasks
        TaskDao.save(task)
        if user:
            WorkflowService.record_review_audit(task, "review1_approved", user)
        WorkflowService.save_review_snapshot(task, TaskStep.HUMAN_REVIEW_1, {"approved": True})
        WorkflowService.transition(task, TaskStep.AUTO_DEVELOPMENT, TaskStatus.INIT)
        WorkflowService.append_log(task, "Review 1 通过，进入自动开发")
        return task

    @staticmethod
    @log_method
    def review2(task_id: int, user=None):
        task = TaskService.get_task(task_id)
        if task.current_step != TaskStep.HUMAN_REVIEW_2:
            raise BizException("当前不在 Review 2 阶段", ErrorCode.PARAM_ERROR)
        if task.current_status != TaskStatus.INIT:
            raise BizException("Review 2 仅能在待处理状态下操作", ErrorCode.PARAM_ERROR)
        if user:
            WorkflowService.record_review_audit(task, "review2_approved", user)
        WorkflowService.save_review_snapshot(task, TaskStep.HUMAN_REVIEW_2, {"approved": True})
        WorkflowService.transition(task, TaskStep.COMMIT_PUSH, TaskStatus.INIT)
        WorkflowService.append_log(task, "Review 2 通过，进入提交发布")
        return task

    @staticmethod
    @log_method
    def save_opinion(task_id: int, opinion: str, reject: bool = False, user=None):
        task = TaskService.get_task(task_id)
        opinion = (opinion or "").strip()
        if not opinion:
            raise BizException("请填写 Review 意见", ErrorCode.PARAM_ERROR)

        task.review_opinion = opinion
        cp = dict(task.checkpoint or {})
        history = list(cp.get("opinion_history") or [])
        history.append(
            {
                "step": task.current_step,
                "opinion": opinion,
                "reject": reject,
                "user_id": getattr(user, "id", None),
                "username": getattr(user, "username", None) or "unknown",
                "at": datetime.now().isoformat(),
            }
        )
        cp["opinion_history"] = history
        task.checkpoint = cp
        TaskDao.save(task)

        # 偏好按任务创建人积累，保证下次自动 Review 读到同一套总结
        pref_user_id = task.created_by_id or getattr(user, "id", None)
        if pref_user_id:
            ReviewPreferenceService.append_opinion(pref_user_id, task.current_step, opinion, task_id)

        if not reject:
            return task

        if task.current_step == TaskStep.HUMAN_REVIEW_1:
            if task.current_status != TaskStatus.INIT:
                raise BizException("Review 1 仅能在待处理状态下驳回", ErrorCode.PARAM_ERROR)
            cp["pending_review_feedback"] = opinion
            task.checkpoint = cp
            TaskDao.save(task)
            if user:
                WorkflowService.record_review_audit(task, "review1_rejected", user)
            WorkflowService.save_review_snapshot(task, TaskStep.HUMAN_REVIEW_1, {"reviewOpinion": opinion, "rejected": True})
            WorkflowService.transition(task, TaskStep.REQUIREMENT_REFINEMENT, TaskStatus.INIT)
            WorkflowService.append_log(task, "Review 1 驳回，重新进入需求拆解")
            TaskService._try_dispatch(task_id)
            return task

        if task.current_step == TaskStep.HUMAN_REVIEW_2:
            if task.current_status != TaskStatus.INIT:
                raise BizException("Review 2 仅能在待处理状态下驳回", ErrorCode.PARAM_ERROR)
            cp["pending_review_feedback"] = opinion
            task.checkpoint = cp
            TaskDao.save(task)
            if user:
                WorkflowService.record_review_audit(task, "review2_rejected", user)
            WorkflowService.save_review_snapshot(task, TaskStep.HUMAN_REVIEW_2, {"reviewOpinion": opinion, "rejected": True})
            WorkflowService.transition(task, TaskStep.AUTO_DEVELOPMENT, TaskStatus.INIT)
            WorkflowService.append_log(task, "Review 2 驳回，重新进入自动开发")
            TaskService._try_dispatch(task_id)
            return task

        raise BizException("当前阶段不支持提交驳回意见", ErrorCode.PARAM_ERROR)

    @staticmethod
    def _try_dispatch(task_id: int):
        if SessionDao.count_processing() < settings.AGENT_MAX_CONCURRENT_SESSIONS:
            try:
                AgentOrchestrator.dispatch(task_id)
            except Exception:
                pass

    @staticmethod
    @log_method
    def force_step(task_id: int, step: str, status: str, user=None):
        if user and getattr(user, "role", "") != "admin" and not getattr(user, "is_superuser", False):
            raise BizException("仅管理员可强制改步骤", ErrorCode.FORBIDDEN)
        task = TaskService.get_task(task_id)
        WorkflowService.append_log(
            task,
            f"⚠️ 强制改步骤 → {step}/{status}（操作人: {getattr(user, 'username', 'unknown')}）",
        )
        WorkflowService.transition(task, step, status, checkpoint_patch={"force_step": True})
        return task

    @staticmethod
    @log_method
    def interrupt(task_id: int):
        return AgentOrchestrator.interrupt(task_id)

    @staticmethod
    @log_method
    def cancel(task_id: int):
        return AgentOrchestrator.cancel(task_id)

    @staticmethod
    @log_method
    def resume(task_id: int):
        task = AgentOrchestrator.resume(task_id)
        if SessionDao.count_processing() < settings.AGENT_MAX_CONCURRENT_SESSIONS:
            AgentOrchestrator.dispatch(task_id)
        return task

    @staticmethod
    @log_method
    def list_resumable():
        return TaskDao.find_interrupted()
