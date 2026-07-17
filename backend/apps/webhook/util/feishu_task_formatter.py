"""飞书任务 Review 摘要格式化。"""
from __future__ import annotations

from apps.common.constant.task_constants import TaskStep

_STEP_LABELS = {
    TaskStep.REQUIREMENT_REFINEMENT: "需求拆解",
    TaskStep.HUMAN_REVIEW_1: "人工 Review 1",
    TaskStep.AUTO_DEVELOPMENT: "自动开发",
    TaskStep.HUMAN_REVIEW_2: "人工 Review 2",
    TaskStep.COMMIT_PUSH: "提交发布",
}

_REVIEW_SOURCE_STEP = {
    TaskStep.HUMAN_REVIEW_1: TaskStep.REQUIREMENT_REFINEMENT,
    TaskStep.HUMAN_REVIEW_2: TaskStep.AUTO_DEVELOPMENT,
}

_MAX_LOG_CHARS = 1200
_MAX_MESSAGE_CHARS = 3800


def _latest_snapshot(task, step: str) -> dict:
    history = (task.checkpoint or {}).get("execution_history") or []
    for entry in reversed(history):
        if entry.get("step") == step:
            return entry
    return {}


def _subtask_lines(sub_tasks: list) -> list[str]:
    lines: list[str] = []
    for item in sub_tasks or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        status = "已完成" if item.get("completed") else "待办"
        lines.append(f"{status}\n{title}")
    return lines


def _file_lines(affected_files: dict) -> list[str]:
    files = affected_files or {}
    predicted = files.get("predicted_by_agent") or []
    confirmed = files.get("confirmed_by_human") or []
    chosen = confirmed or predicted
    return [str(path).strip() for path in chosen if str(path).strip()]


def _truncate_logs(logs: str) -> str:
    text = (logs or "").strip()
    if len(text) <= _MAX_LOG_CHARS:
        return text
    return f"...\n{text[-_MAX_LOG_CHARS:]}\n（完整日志请在看板查看）"


def _append_section(parts: list[str], title: str, body_lines: list[str]) -> None:
    if not body_lines:
        return
    parts.append(title)
    parts.extend(body_lines)


def _append_auto_review_section(parts: list[str], task) -> None:
    """把基于用户偏好的自动 Review 建议写入飞书文案。"""
    auto_review = (task.checkpoint or {}).get("auto_review") or {}
    if not auto_review:
        return

    skipped = bool(auto_review.get("skipped"))
    passed = bool(auto_review.get("passed"))
    summary = str(auto_review.get("summary") or "").strip()
    issues = [str(x).strip() for x in (auto_review.get("issues") or []) if str(x).strip()]

    if skipped:
        status = "已跳过"
    elif passed:
        status = "建议通过"
    else:
        status = "建议关注"

    parts.extend(["", "自动 Review 建议（基于历史偏好）", f"结论：{status}"])
    if summary:
        parts.append(f"说明：{summary}")
    if issues:
        parts.append("建议：")
        for issue in issues[:8]:
            parts.append(f"· {issue}")
    elif not skipped and passed:
        parts.append("建议：产出与近期偏好基本一致，可直接人工确认。")


def format_task_review_message(task, phase: str) -> str:
    """生成 Review 阶段推送到飞书的结构化摘要。"""
    review_step = phase
    source_step = _REVIEW_SOURCE_STEP.get(phase, phase)
    snapshot = _latest_snapshot(task, source_step)

    sub_tasks = snapshot.get("subTasks") or task.sub_tasks or []
    affected_files = snapshot.get("affectedFiles") or task.affected_files or {}
    execution_logs = snapshot.get("executionLogs") or task.execution_logs or ""
    code_diffs = snapshot.get("codeDiffs") or task.code_diffs or []

    review_label = _STEP_LABELS.get(review_step, review_step)
    parts = [
        f"任务 #{task.id} · {task.title}",
        f"{review_label} · 执行历史",
        "",
    ]

    if review_step == TaskStep.HUMAN_REVIEW_1:
        _append_section(parts, "子任务清单", _subtask_lines(sub_tasks))
        _append_section(parts, "影响文件", _file_lines(affected_files))
    elif review_step == TaskStep.HUMAN_REVIEW_2:
        diff_lines = []
        for diff in code_diffs:
            if not isinstance(diff, dict):
                continue
            path = str(diff.get("filePath") or diff.get("file_path") or "").strip()
            if path:
                diff_lines.append(path)
        _append_section(parts, "变更文件", diff_lines)

    log_text = _truncate_logs(execution_logs)
    if log_text:
        parts.extend(["执行日志", log_text])

    _append_auto_review_section(parts, task)

    task_id = getattr(task, "id", "")
    if review_step == TaskStep.HUMAN_REVIEW_1:
        parts.extend(
            [
                "",
                "---",
                f"通过：#{task_id} 同意动工",
                f"驳回：#{task_id} 驳回：你的意见",
            ]
        )
    elif review_step == TaskStep.HUMAN_REVIEW_2:
        parts.extend(
            [
                "",
                "---",
                f"通过：#{task_id} 合并发布",
                f"驳回：#{task_id} 驳回：你的意见",
            ]
        )

    text = "\n".join(parts).strip()
    if len(text) <= _MAX_MESSAGE_CHARS:
        return text
    return text[: _MAX_MESSAGE_CHARS - 20] + "\n…（内容过长，请看板查看）"


def format_task_created_message(task_id: int) -> str:
    return (
        f"已创建任务 #{task_id}，Agent 正在拆解需求，完成后将推送 Review 摘要。\n"
        f"后续操作请务必带上任务号，例如：#{task_id} 同意动工"
    )


def format_task_alert_message(task, phase: str, title: str = "") -> str:
    """生成任务中断 / 失败推送到飞书的提示。"""
    step = getattr(task, "current_step", "") or ""
    step_label = _STEP_LABELS.get(step, step or "未知阶段")
    reason = (getattr(task, "fail_reason", "") or "").strip()
    task_id = getattr(task, "id", "")
    if phase == "Interrupted":
        status_line = "状态：已中断"
        default_title = "任务已中断"
        action = f"续做：#{task_id} 续做"
    elif phase == "Failed":
        status_line = "状态：执行失败"
        default_title = "任务执行失败"
        action = f"续做：#{task_id} 续做"
    elif phase == "Cancelled":
        status_line = "状态：已取消"
        default_title = "任务已取消"
        action = "任务已结束，不可续做"
    else:
        status_line = f"状态：{phase}"
        default_title = title or "任务状态变更"
        action = "请在 Agent Loop 看板查看详情"

    parts = [
        f"任务 #{task.id} · {task.title}",
        title or default_title,
        status_line,
        f"阶段：{step_label}",
    ]
    if phase == "Failed" and reason:
        clipped = reason if len(reason) <= 500 else reason[:500] + "…"
        parts.extend(["失败原因", clipped])

    log_text = _truncate_logs(getattr(task, "execution_logs", "") or "")
    if log_text and phase == "Failed":
        parts.extend(["最近日志", log_text])

    parts.extend(["", "---", action])
    text = "\n".join(parts).strip()
    if len(text) <= _MAX_MESSAGE_CHARS:
        return text
    return text[: _MAX_MESSAGE_CHARS - 20] + "\n…（内容过长，请看板查看）"
