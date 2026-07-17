from datetime import datetime
from typing import Optional

from django.conf import settings

from apps.common.constant.task_constants import TaskStatus, TaskStep
from apps.common.exception.biz_exception import BizException, ErrorCode
from apps.common.exception.task_interrupted import TaskInterruptedException
from apps.common.service.session_cache_service import SessionCacheService
from apps.common.util.agent_executor import submit_agent_task
from apps.common.util.logging_util import log_method
from apps.session.dao.session_dao import SessionDao
from apps.task.client.ci_client import CiClient
from apps.task.client.deploy_client import DeployClient
from apps.task.client.git_client import GitClient
from apps.task.client.llm_client import ClaudeCodeClient, PmAgentClient
from apps.project.util.project_context_util import read_convention
from apps.task.dao.task_dao import TaskDao
from apps.project.util.project_path_util import ensure_project_directory
from apps.task.service.auto_review_service import AutoReviewService
from apps.task.service.diff_apply_service import DiffApplyService


def _record_agent_metric(step: str, status: str):
    try:
        from apps.common.controller.metrics_views import record_agent_task

        record_agent_task(step, status)
    except Exception:
        pass


def _save_agent_meta(task, meta: dict, step: str):
    cp = dict(task.checkpoint or {})
    cp["agent_meta"] = {**(cp.get("agent_meta") or {}), step: meta}
    task.checkpoint = cp
    TaskDao.save(task)


def _agent_mode_label(meta: dict) -> str:
    if meta.get("fallback"):
        return "⚠️ 模拟数据(fallback)"
    source = meta.get("source", "unknown")
    labels = {
        "anthropic_api": "Anthropic API",
        "claude_cli": "Claude Code CLI",
        "gemini": "Gemini API",
        "fallback": "本地模拟",
    }
    return labels.get(source, source)


def _notify_task(task, title: str, phase: str):
    from apps.webhook.service.webhook_service import WebhookService

    WebhookService.notify_task_event(task, title, phase)


def _finish_interrupted(task_id: int, session_id: str):
    task = TaskDao.get_by_id(task_id)
    if not task:
        return
    should_notify = False
    if task.current_status != TaskStatus.INTERRUPTED:
        WorkflowService.transition(
            task,
            task.current_step,
            TaskStatus.INTERRUPTED,
            checkpoint_patch={
                "step": task.current_step,
                "status": TaskStatus.PROCESSING,
                "interrupted_at": datetime.now().isoformat(),
            },
        )
        WorkflowService.append_log(task, "⚠️ Agent 已响应中断信号")
        should_notify = True
    SessionDao.interrupt_by_task(task_id)
    SessionCacheService.remove_agent_session(session_id)
    SessionCacheService.release_dispatch_lock(task_id)
    if should_notify:
        task = TaskDao.get_by_id(task_id)
        if task:
            _notify_task(task, "任务已中断", "Interrupted")


def _handle_run_error(task_id: int, session_id: str, exc: Exception, default_step: str):
    if isinstance(exc, TaskInterruptedException) or SessionCacheService.is_task_cancelled(task_id):
        _finish_interrupted(task_id, session_id)
        return
    task = TaskDao.get_by_id(task_id)
    if not task:
        return
    task.fail_reason = str(exc)
    WorkflowService.transition(task, default_step, TaskStatus.FAILED)
    WorkflowService.append_log(task, f"❌ 执行失败: {str(exc)[:300]}")
    SessionDao.fail(session_id, str(exc))
    SessionCacheService.remove_agent_session(session_id)
    SessionCacheService.release_dispatch_lock(task_id)
    task = TaskDao.get_by_id(task_id)
    if task:
        _notify_task(task, "任务执行失败", "Failed")


def _step_label(step: str) -> str:
    labels = {
        TaskStep.REQUIREMENT_REFINEMENT: "需求拆解",
        TaskStep.HUMAN_REVIEW_1: "人工 Review 1",
        TaskStep.AUTO_DEVELOPMENT: "自动开发",
        TaskStep.HUMAN_REVIEW_2: "人工 Review 2",
        TaskStep.COMMIT_PUSH: "提交发布",
    }
    return labels.get(step, step)


class WorkflowService:
    @staticmethod
    @log_method
    def begin_step_run(task, step: str):
        cp = dict(task.checkpoint or {})
        runs = dict(cp.get("step_runs") or {})
        run_no = int(runs.get(step, 0)) + 1
        runs[step] = run_no
        cp["step_runs"] = runs
        cp["active_run"] = {
            "step": step,
            "run": run_no,
            "log_start": len(task.execution_logs or ""),
            "started_at": datetime.now().isoformat(),
        }
        task.checkpoint = cp
        TaskDao.save(task)
        WorkflowService.append_log(task, f"=== 开始 {_step_label(step)} 第{run_no}轮 ===")

    @staticmethod
    @log_method
    def save_review_snapshot(task, step: str, extra: Optional[dict] = None):
        cp = dict(task.checkpoint or {})
        runs = dict(cp.get("step_runs") or {})
        run_no = int(runs.get(step, 0)) + 1
        runs[step] = run_no
        cp["step_runs"] = runs
        entry = {
            "step": step,
            "run": run_no,
            "finishedAt": datetime.now().isoformat(),
            "acceptanceCriteria": task.acceptance_criteria,
            "subTasks": list(task.sub_tasks or []),
            "affectedFiles": dict(task.affected_files or {}),
            "codeDiffs": list(task.code_diffs or []),
            "executionLogs": "",
            "reviewOpinion": task.review_opinion or "",
        }
        if extra:
            entry.update(extra)
        history = list(cp.get("execution_history") or [])
        history.append(entry)
        cp["execution_history"] = history
        task.checkpoint = cp
        TaskDao.save(task)

    @staticmethod
    @log_method
    def finish_step_snapshot(task, artifacts: Optional[dict] = None):
        cp = dict(task.checkpoint or {})
        active = dict(cp.get("active_run") or {})
        if not active.get("step"):
            return
        logs = task.execution_logs or ""
        start = int(active.get("log_start", 0))
        entry = {
            "step": active["step"],
            "run": active.get("run", 1),
            "startedAt": active.get("started_at"),
            "finishedAt": datetime.now().isoformat(),
            "acceptanceCriteria": task.acceptance_criteria,
            "subTasks": list(task.sub_tasks or []),
            "affectedFiles": dict(task.affected_files or {}),
            "codeDiffs": list(task.code_diffs or []),
            "executionLogs": logs[start:],
            "reviewOpinion": task.review_opinion or "",
        }
        if artifacts:
            entry.update(artifacts)
        history = list(cp.get("execution_history") or [])
        history.append(entry)
        cp["execution_history"] = history
        cp["active_run"] = None
        task.checkpoint = cp
        TaskDao.save(task)

    @staticmethod
    @log_method
    def store_auto_review(task, review_step: str, result: dict):
        cp = dict(task.checkpoint or {})
        cp["auto_review"] = {**result, "step": review_step, "at": datetime.now().isoformat()}
        task.checkpoint = cp
        TaskDao.save(task)
        status = "通过" if result.get("passed") else "待关注"
        WorkflowService.append_log(task, f"自动 Review ({_step_label(review_step)}): {status} — {result.get('summary', '')}")
        for issue in result.get("issues") or []:
            WorkflowService.append_log(task, f"  · {issue}")

    @staticmethod
    @log_method
    def get_pending_review_feedback(task) -> str:
        return (task.checkpoint or {}).get("pending_review_feedback", "") or task.review_opinion or ""

    @staticmethod
    @log_method
    def clear_pending_review_feedback(task):
        cp = dict(task.checkpoint or {})
        cp.pop("pending_review_feedback", None)
        task.checkpoint = cp
        TaskDao.save(task)

    @staticmethod
    @log_method
    def append_log(task, line: str):
        ts = datetime.now().strftime("%H:%M:%S")
        task.execution_logs = (task.execution_logs or "") + f"[{ts}] {line}\n"
        TaskDao.save(task)

    @staticmethod
    @log_method
    def transition(task, step: str, status: str, checkpoint_patch: Optional[dict] = None):
        task.current_step = step
        task.current_status = status
        if checkpoint_patch is not None:
            cp = dict(task.checkpoint or {})
            cp.update(checkpoint_patch)
            task.checkpoint = cp
        TaskDao.save(task)

    @staticmethod
    @log_method
    def record_review_audit(task, action: str, user):
        username = getattr(user, "username", None) or "unknown"
        user_id = getattr(user, "id", None)
        ts = datetime.now().isoformat()
        cp = dict(task.checkpoint or {})
        audits = list(cp.get("review_audit") or [])
        audits.append({"action": action, "user_id": user_id, "username": username, "at": ts})
        cp["review_audit"] = audits
        task.checkpoint = cp
        TaskDao.save(task)
        WorkflowService.append_log(task, f"Review 审计: {action} — 操作人 {username} @ {ts[:19]}")

    @staticmethod
    @log_method
    def run_requirement_refinement(task_id: int, session_id: str):
        task = TaskDao.get_by_id(task_id)
        if not task:
            return
        try:
            SessionCacheService.ensure_not_cancelled(task_id)
            WorkflowService.transition(task, TaskStep.REQUIREMENT_REFINEMENT, TaskStatus.PROCESSING)
            WorkflowService.begin_step_run(task, TaskStep.REQUIREMENT_REFINEMENT)
            WorkflowService.append_log(task, "PM Agent: 开始需求拆解...")
            user_id = task.created_by_id
            project_path = str(ensure_project_directory(task.project.project_path))
            convention = read_convention(project_path, task.project.convention_path)
            mode = ClaudeCodeClient.resolve_mode(user_id, project_path)
            WorkflowService.append_log(task, f"Agent 模式: {mode}")
            review_feedback = WorkflowService.get_pending_review_feedback(task)
            if review_feedback:
                WorkflowService.append_log(task, f"人工 Review 意见: {review_feedback[:200]}")
            parsed, pm_meta = PmAgentClient.decompose(
                task.acceptance_criteria,
                user_id=user_id,
                task_id=task_id,
                convention_text=convention,
                review_feedback=review_feedback,
            )
            SessionCacheService.ensure_not_cancelled(task_id)

            task = TaskDao.get_by_id(task_id)
            task.affected_files = {
                "predicted_by_agent": parsed.get("predicted_files", []),
                "confirmed_by_human": [],
            }
            task.sub_tasks = parsed.get("sub_tasks", [])
            TaskDao.save(task)
            _save_agent_meta(task, pm_meta, "requirement_refinement")
            WorkflowService.finish_step_snapshot(task, {"agentMeta": pm_meta})
            WorkflowService.clear_pending_review_feedback(task)
            auto_result = AutoReviewService.review_task(task, TaskStep.HUMAN_REVIEW_1)
            WorkflowService.store_auto_review(task, TaskStep.HUMAN_REVIEW_1, auto_result)
            WorkflowService.append_log(task, f"PM Agent: 拆解完成 ({_agent_mode_label(pm_meta)})，等待人工 Review 1")
            WorkflowService.transition(
                task,
                TaskStep.HUMAN_REVIEW_1,
                TaskStatus.INIT,
                checkpoint_patch={"phase": "review1", "session_id": session_id},
            )
            task = TaskDao.get_by_id(task_id) or task
            _notify_task(task, "需求拆解完成，请 Review", "Human_Review_1")
            SessionDao.finish(session_id)
            SessionCacheService.remove_agent_session(session_id)
            SessionCacheService.release_dispatch_lock(task_id)
            _record_agent_metric(TaskStep.REQUIREMENT_REFINEMENT, "finished")
        except Exception as exc:
            _record_agent_metric(TaskStep.REQUIREMENT_REFINEMENT, "failed")
            _handle_run_error(task_id, session_id, exc, TaskStep.REQUIREMENT_REFINEMENT)

    @staticmethod
    @log_method
    def run_auto_development(task_id: int, session_id: str):
        task = TaskDao.get_by_id(task_id)
        if not task:
            return
        try:
            SessionCacheService.ensure_not_cancelled(task_id)
            WorkflowService.transition(task, TaskStep.AUTO_DEVELOPMENT, TaskStatus.PROCESSING)
            WorkflowService.begin_step_run(task, TaskStep.AUTO_DEVELOPMENT)
            confirmed = (task.affected_files or {}).get("confirmed_by_human") or (task.affected_files or {}).get(
                "predicted_by_agent", []
            )
            user_id = task.created_by_id
            project_path = str(ensure_project_directory(task.project.project_path))
            convention = read_convention(project_path, task.project.convention_path)
            GitClient.ensure_repo(project_path)
            mode = ClaudeCodeClient.resolve_mode(user_id, project_path)
            WorkflowService.append_log(task, f"Coding Agent: 启动 ({mode})...")
            review_feedback = WorkflowService.get_pending_review_feedback(task)
            if review_feedback:
                WorkflowService.append_log(task, f"人工 Review 意见: {review_feedback[:200]}")
            cli_mode = mode == "claude_cli"
            log_chunk, run_meta = ClaudeCodeClient.run(
                task_id,
                task.acceptance_criteria,
                confirmed,
                user_id=user_id,
                project_path=project_path,
                convention_text=convention,
                review_feedback=review_feedback,
            )
            SessionCacheService.ensure_not_cancelled(task_id)
            WorkflowService.append_log(task, log_chunk)

            task = TaskDao.get_by_id(task_id)
            for st in task.sub_tasks or []:
                st["completed"] = True
            code_diffs, diff_meta = ClaudeCodeClient.generate_diffs(
                task.acceptance_criteria,
                confirmed,
                user_id=user_id,
                task_id=task_id,
                project_path=project_path,
                convention_text=convention,
                cli_already_ran=cli_mode,
                review_feedback=review_feedback,
            )
            SessionCacheService.ensure_not_cancelled(task_id)
            task.code_diffs = code_diffs
            TaskDao.save(task)
            _save_agent_meta(task, {**run_meta, **diff_meta, "mode": mode}, "auto_development")
            WorkflowService.finish_step_snapshot(task, {"agentMeta": {**run_meta, **diff_meta, "mode": mode}})
            WorkflowService.clear_pending_review_feedback(task)
            auto_result = AutoReviewService.review_task(task, TaskStep.HUMAN_REVIEW_2)
            WorkflowService.store_auto_review(task, TaskStep.HUMAN_REVIEW_2, auto_result)

            WorkflowService.append_log(
                task,
                f"Coding Agent: diff 已生成 ({_agent_mode_label(diff_meta)})，等待 Review 2",
            )
            WorkflowService.transition(
                task,
                TaskStep.HUMAN_REVIEW_2,
                TaskStatus.INIT,
                checkpoint_patch={"phase": "review2", "session_id": session_id},
            )
            task = TaskDao.get_by_id(task_id) or task
            _notify_task(task, "开发完成，请 Review 代码", "Human_Review_2")
            SessionDao.finish(session_id)
            SessionCacheService.remove_agent_session(session_id)
            SessionCacheService.release_dispatch_lock(task_id)
            _record_agent_metric(TaskStep.AUTO_DEVELOPMENT, "finished")
        except Exception as exc:
            _record_agent_metric(TaskStep.AUTO_DEVELOPMENT, "failed")
            _handle_run_error(task_id, session_id, exc, TaskStep.AUTO_DEVELOPMENT)

    @staticmethod
    @log_method
    def run_commit_push(task_id: int, session_id: str):
        task = TaskDao.get_by_id(task_id)
        if not task:
            return
        try:
            SessionCacheService.ensure_not_cancelled(task_id)
            WorkflowService.transition(task, TaskStep.COMMIT_PUSH, TaskStatus.PROCESSING)
            WorkflowService.begin_step_run(task, TaskStep.COMMIT_PUSH)
            project_path = str(ensure_project_directory(task.project.project_path))

            WorkflowService.append_log(task, "Apply Agent: 将 code_diffs 写入项目目录...")
            for line in DiffApplyService.apply_diffs(project_path, task.code_diffs or []):
                WorkflowService.append_log(task, line)
            SessionCacheService.ensure_not_cancelled(task_id)

            WorkflowService.append_log(task, "CI Agent: 运行项目自测...")
            for line in CiClient.run_tests(project_path):
                WorkflowService.append_log(task, line)
            SessionCacheService.ensure_not_cancelled(task_id)

            WorkflowService.append_log(task, "Git Agent: commit & push...")
            commit_msg = f"agent-loop #{task_id}: {task.title}"
            project = task.project
            for line in GitClient.commit_and_push(
                project_path,
                commit_msg,
                branch=getattr(project, "git_branch", "") or None,
                remote_url=getattr(project, "git_remote_url", "") or "",
                push_enabled=getattr(project, "git_push_enabled", False),
            ):
                WorkflowService.append_log(task, line)

            WorkflowService.append_log(task, "Deploy Agent: 执行发布...")
            for line in DeployClient.deploy(project_path, task_id, task.title):
                WorkflowService.append_log(task, line)

            WorkflowService.append_log(task, "Deploy Agent: 发布流程完成")
            WorkflowService.finish_step_snapshot(task)
            WorkflowService.transition(
                task,
                TaskStep.COMMIT_PUSH,
                TaskStatus.FINISHED,
                checkpoint_patch={"phase": "finished", "finished_at": datetime.now().isoformat()},
            )
            _notify_task(task, "任务已发布上线", "Finished")
            SessionDao.finish(session_id)
            SessionCacheService.remove_agent_session(session_id)
            SessionCacheService.release_dispatch_lock(task_id)
            _record_agent_metric(TaskStep.COMMIT_PUSH, "finished")
        except Exception as exc:
            _record_agent_metric(TaskStep.COMMIT_PUSH, "failed")
            _handle_run_error(task_id, session_id, exc, TaskStep.COMMIT_PUSH)


class AgentOrchestrator:
    @staticmethod
    @log_method
    def dispatch(task_id: int):
        if not SessionCacheService.acquire_dispatch_lock(task_id):
            return None
        try:
            return AgentOrchestrator._dispatch_locked(task_id)
        except Exception:
            SessionCacheService.release_dispatch_lock(task_id)
            raise

    @staticmethod
    @log_method
    def _dispatch_locked(task_id: int):
        task = TaskDao.get_by_id(task_id)
        if not task:
            SessionCacheService.release_dispatch_lock(task_id)
            raise BizException("任务不存在", ErrorCode.NOT_FOUND)

        SessionCacheService.clear_task_cancelled(task_id)
        session = SessionDao.create_for_task(task)
        SessionCacheService.register_agent_session(
            session.session_id,
            task_id,
            task.created_by_id,
            task.current_step,
        )

        step = task.current_step
        if step == TaskStep.REQUIREMENT_REFINEMENT:
            target = WorkflowService.run_requirement_refinement
        elif step == TaskStep.AUTO_DEVELOPMENT:
            target = WorkflowService.run_auto_development
        elif step == TaskStep.COMMIT_PUSH:
            target = WorkflowService.run_commit_push
        else:
            SessionCacheService.release_dispatch_lock(task_id)
            raise BizException("当前阶段无需自动调度", ErrorCode.PARAM_ERROR)

        if getattr(settings, "USE_CELERY", False):
            from apps.task.tasks import dispatch_workflow_async

            dispatch_workflow_async(task_id, session.session_id, step)
        else:
            submit_agent_task(target, task_id, session.session_id, trace_prefix=f"task-{task_id}")
        return session

    @staticmethod
    @log_method
    def interrupt(task_id: int):
        task = TaskDao.get_by_id(task_id)
        if not task:
            raise BizException("任务不存在", ErrorCode.NOT_FOUND)
        if task.current_status not in (TaskStatus.PROCESSING, TaskStatus.INIT):
            raise BizException("当前状态不可中断", ErrorCode.PARAM_ERROR)

        SessionCacheService.set_task_cancelled(task_id)
        SessionDao.interrupt_by_task(task_id)
        WorkflowService.transition(
            task,
            task.current_step,
            TaskStatus.INTERRUPTED,
            checkpoint_patch={
                "step": task.current_step,
                "status": task.current_status,
                "interrupted_at": datetime.now().isoformat(),
            },
        )
        WorkflowService.append_log(task, "⚠️ 任务已中断，可稍后续做")
        SessionCacheService.release_dispatch_lock(task_id)
        _notify_task(task, "任务已中断", "Interrupted")
        return task

    @staticmethod
    @log_method
    def cancel(task_id: int):
        """永久取消任务（不可续做）。"""
        task = TaskDao.get_by_id(task_id)
        if not task:
            raise BizException("任务不存在", ErrorCode.NOT_FOUND)
        if task.current_status in (TaskStatus.FINISHED, TaskStatus.CANCELLED):
            raise BizException("当前状态不可取消", ErrorCode.PARAM_ERROR)

        SessionCacheService.set_task_cancelled(task_id)
        SessionDao.interrupt_by_task(task_id)
        WorkflowService.transition(
            task,
            task.current_step,
            TaskStatus.CANCELLED,
            checkpoint_patch={
                "step": task.current_step,
                "status": task.current_status,
                "cancelled_at": datetime.now().isoformat(),
            },
        )
        WorkflowService.append_log(task, "🚫 任务已取消（不可续做）")
        SessionCacheService.release_dispatch_lock(task_id)
        _notify_task(task, "任务已取消", "Cancelled")
        return task

    @staticmethod
    @log_method
    def resume(task_id: int):
        task = TaskDao.get_by_id(task_id)
        if not task:
            raise BizException("任务不存在", ErrorCode.NOT_FOUND)
        if task.current_status not in (TaskStatus.INTERRUPTED, TaskStatus.FAILED):
            raise BizException("仅中断或失败任务可续做", ErrorCode.PARAM_ERROR)

        cp = task.checkpoint or {}
        step = cp.get("step", task.current_step)
        task.current_step = step
        task.current_status = TaskStatus.INIT
        task.fail_reason = ""
        TaskDao.save(task)
        SessionCacheService.clear_task_cancelled(task_id)
        WorkflowService.append_log(task, "▶️ 任务续做，重新进入调度队列")
        return task
