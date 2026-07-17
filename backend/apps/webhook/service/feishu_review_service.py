"""飞书群内任务操作（固定指令，必须带任务号）。"""
from __future__ import annotations

import re
from typing import Optional

from apps.auth_app.dao.user_dao import UserDao
from apps.common.constant.task_constants import TaskStatus, TaskStep
from apps.common.exception.biz_exception import BizException
from apps.task.dao.task_dao import TaskDao
from apps.task.service.task_service import TaskService

# 固定指令（一字不差，除空白与 #号 前后空格）
_CMD_CREATE = re.compile(r"^新建任务[：:]\s*(.+)\s*$", re.S)
_CMD_CREATE_EMPTY = re.compile(r"^新建任务[：:]\s*$")
_CMD_APPROVE1 = re.compile(r"^#(\d+)\s*同意动工\s*$")
_CMD_APPROVE2 = re.compile(r"^#(\d+)\s*合并发布\s*$")
_CMD_REJECT = re.compile(r"^#(\d+)\s*驳回[：:]\s*(.*)\s*$", re.S)
_CMD_RESUME = re.compile(r"^#(\d+)\s*续做\s*$")
_CMD_CANCEL = re.compile(r"^#(\d+)\s*取消任务\s*$")
_CMD_HASH_PREFIX = re.compile(r"^#(\d+)\s*(.*)$", re.S)

_NEAR_MISS = (
    (re.compile(r"同意动工"), "#任务号 同意动工"),
    (re.compile(r"合并发布"), "#任务号 合并发布"),
    (re.compile(r"驳回"), "#任务号 驳回：你的意见"),
    (re.compile(r"续做"), "#任务号 续做"),
    (re.compile(r"取消任务"), "#任务号 取消任务"),
    (re.compile(r"新建任务"), "新建任务：需求描述"),
)

USAGE_HELP = (
    "可用指令：\n"
    "· 新建任务：需求描述\n"
    "· #任务号 同意动工\n"
    "· #任务号 合并发布\n"
    "· #任务号 驳回：意见\n"
    "· #任务号 续做\n"
    "· #任务号 取消任务"
)

_STEP_HINT = {
    TaskStep.HUMAN_REVIEW_1: "Review 1，可用：#{tid} 同意动工 / #{tid} 驳回：意见 / #{tid} 取消任务",
    TaskStep.HUMAN_REVIEW_2: "Review 2，可用：#{tid} 合并发布 / #{tid} 驳回：意见 / #{tid} 取消任务",
    TaskStep.REQUIREMENT_REFINEMENT: "需求拆解中，可用：#{tid} 取消任务",
    TaskStep.AUTO_DEVELOPMENT: "自动开发中，可用：#{tid} 取消任务",
    TaskStep.COMMIT_PUSH: "提交发布中，可用：#{tid} 取消任务",
}


def _normalize(text: str) -> str:
    return (text or "").strip()


def _preview(text: str, limit: int = 80) -> str:
    raw = _normalize(text).replace("\n", "\\n")
    return raw if len(raw) <= limit else raw[: limit - 1] + "…"


def _error_reply(reason: str, *, example: str = "", action: str = "command_error", task_id: Optional[int] = None) -> dict:
    parts = ["指令有误", reason]
    if example:
        parts.append(f"正确写法：{example}")
    parts.append("")
    parts.append(USAGE_HELP)
    result = {"ok": True, "reply": "\n".join(parts), "action": action}
    if task_id is not None:
        result["taskId"] = task_id
    return result


def parse_create_body(text: str) -> Optional[str]:
    """若为创建任务指令则返回正文，否则 None。"""
    match = _CMD_CREATE.match(_normalize(text))
    if not match:
        return None
    body = (match.group(1) or "").strip()
    return body or None


def _load_task(project_id: int, task_id: int):
    from apps.task.entity.models import Task

    return (
        Task.objects.filter(id=task_id, project_id=project_id)
        .select_related("project")
        .first()
    )


def _status_hint(task) -> str:
    tid = task.id
    if task.current_status == TaskStatus.FAILED:
        return f"失败/待续做，可用：#{tid} 续做 / #{tid} 取消任务"
    if task.current_status == TaskStatus.INTERRUPTED:
        return f"已中断，可用：#{tid} 续做 / #{tid} 取消任务"
    if task.current_status == TaskStatus.PROCESSING:
        return f"执行中（{task.current_step}），可用：#{tid} 取消任务"
    if task.current_status == TaskStatus.FINISHED:
        return "已完成，无需再操作"
    if task.current_status == TaskStatus.CANCELLED:
        return "已取消，无需再操作"
    tpl = _STEP_HINT.get(task.current_step, f"当前 {task.current_step}/{task.current_status}")
    return tpl.replace("{tid}", str(tid))


def _near_miss_reply(text: str) -> Optional[dict]:
    raw = _normalize(text)
    if _CMD_CREATE_EMPTY.match(raw):
        return _error_reply(
            f"你发送：{_preview(raw)}\n缺少需求描述。",
            example="新建任务：测试登录后发布",
            action="command_format_error",
        )

    for pattern, example in _NEAR_MISS:
        if pattern.search(raw):
            return _error_reply(
                f"你发送：{_preview(raw)}\n格式不正确。",
                example=example,
                action="command_format_error",
            )

    hash_match = _CMD_HASH_PREFIX.match(raw)
    if hash_match:
        task_id = int(hash_match.group(1))
        rest = (hash_match.group(2) or "").strip()
        if not rest:
            return _error_reply(
                f"你发送：{_preview(raw)}\n只有任务号，缺少操作关键词。",
                example=f"#{task_id} 同意动工",
                action="command_format_error",
                task_id=task_id,
            )
        return _error_reply(
            f"你发送：{_preview(raw)}\n无法识别「{rest}」。",
            example=f"#{task_id} 同意动工 / #{task_id} 合并发布 / #{task_id} 驳回：意见 / #{task_id} 续做 / #{task_id} 取消任务",
            action="command_unknown",
            task_id=task_id,
        )
    return None


def _handle_approve1(project_id: int, task_id: int) -> dict:
    task = _load_task(project_id, task_id)
    if not task:
        return _error_reply(
            f"未找到任务 #{task_id}（请确认任务号属于当前飞书关联项目）。",
            example=f"#{task_id} 同意动工",
            action="task_miss",
        )
    if task.current_step != TaskStep.HUMAN_REVIEW_1 or task.current_status != TaskStatus.INIT:
        return _error_reply(
            f"任务 #{task_id} 当前不能「同意动工」。\n当前状态：{_status_hint(task)}",
            example=f"#{task_id} 同意动工",
            action="review1_invalid",
            task_id=task.id,
        )
    try:
        admin = UserDao.get_by_username("admin")
        files = task.affected_files or {}
        confirmed = list(files.get("confirmed_by_human") or files.get("predicted_by_agent") or [])
        TaskService.review1(task.id, confirmed, list(task.sub_tasks or []), user=admin)
        TaskService._try_dispatch(task.id)
    except BizException as exc:
        return _error_reply(f"任务 #{task_id} 同意动工失败：{exc}", action="review1_failed", task_id=task_id)
    except Exception as exc:
        return _error_reply(f"任务 #{task_id} 同意动工异常：{exc}", action="review1_failed", task_id=task_id)
    return {
        "ok": True,
        "reply": f"任务 #{task.id} Review 1 已通过，已启动自动开发。",
        "taskId": task.id,
        "action": "review1_approved",
    }


def _handle_approve2(project_id: int, task_id: int) -> dict:
    task = _load_task(project_id, task_id)
    if not task:
        return _error_reply(
            f"未找到任务 #{task_id}（请确认任务号属于当前飞书关联项目）。",
            example=f"#{task_id} 合并发布",
            action="task_miss",
        )
    if task.current_step != TaskStep.HUMAN_REVIEW_2 or task.current_status != TaskStatus.INIT:
        return _error_reply(
            f"任务 #{task_id} 当前不能「合并发布」。\n当前状态：{_status_hint(task)}",
            example=f"#{task_id} 合并发布",
            action="review2_invalid",
            task_id=task.id,
        )
    try:
        admin = UserDao.get_by_username("admin")
        TaskService.review2(task.id, user=admin)
        TaskService._try_dispatch(task.id)
    except BizException as exc:
        return _error_reply(f"任务 #{task_id} 合并发布失败：{exc}", action="review2_failed", task_id=task_id)
    except Exception as exc:
        return _error_reply(f"任务 #{task_id} 合并发布异常：{exc}", action="review2_failed", task_id=task_id)
    return {
        "ok": True,
        "reply": f"任务 #{task.id} Review 2 已通过，进入提交发布。",
        "taskId": task.id,
        "action": "review2_approved",
    }


def _handle_reject(project_id: int, task_id: int, opinion: str) -> dict:
    task = _load_task(project_id, task_id)
    if not task:
        return _error_reply(
            f"未找到任务 #{task_id}（请确认任务号属于当前飞书关联项目）。",
            example=f"#{task_id} 驳回：你的意见",
            action="task_miss",
        )
    if task.current_status != TaskStatus.INIT or task.current_step not in (
        TaskStep.HUMAN_REVIEW_1,
        TaskStep.HUMAN_REVIEW_2,
    ):
        return _error_reply(
            f"任务 #{task_id} 当前不能「驳回」。\n当前状态：{_status_hint(task)}",
            example=f"#{task_id} 驳回：你的意见",
            action="reject_invalid",
            task_id=task.id,
        )
    opinion = (opinion or "").strip()
    if not opinion:
        return _error_reply(
            f"你发送：#{task_id} 驳回：\n缺少意见内容。",
            example=f"#{task_id} 驳回：子任务需补充测试说明",
            action="reject_empty",
            task_id=task.id,
        )
    try:
        admin = UserDao.get_by_username("admin")
        review_step = task.current_step
        TaskService.save_opinion(task.id, opinion, reject=True, user=admin)
    except BizException as exc:
        return _error_reply(f"任务 #{task_id} 驳回失败：{exc}", action="reject_failed", task_id=task_id)
    except Exception as exc:
        return _error_reply(f"任务 #{task_id} 驳回异常：{exc}", action="reject_failed", task_id=task_id)
    if review_step == TaskStep.HUMAN_REVIEW_1:
        reply = f"任务 #{task.id} 已收到 Review 意见，正在重新拆解…"
    else:
        reply = f"任务 #{task.id} 已收到 Review 意见，正在重新开发…"
    return {"ok": True, "reply": reply, "taskId": task.id, "action": "review_rejected"}


def _handle_cancel(project_id: int, task_id: int) -> dict:
    task = _load_task(project_id, task_id)
    if not task:
        return _error_reply(
            f"未找到任务 #{task_id}（请确认任务号属于当前飞书关联项目）。",
            example=f"#{task_id} 取消任务",
            action="task_miss",
        )
    if task.current_status in (TaskStatus.FINISHED, TaskStatus.CANCELLED):
        return _error_reply(
            f"任务 #{task_id} 当前不能「取消任务」。\n当前状态：{_status_hint(task)}",
            example=f"#{task_id} 取消任务",
            action="cancel_invalid",
            task_id=task_id,
        )
    try:
        TaskService.cancel(task.id)
    except BizException as exc:
        return _error_reply(f"任务 #{task.id} 取消失败：{exc}", action="cancel_failed", task_id=task.id)
    except Exception as exc:
        return _error_reply(f"任务 #{task.id} 取消异常：{exc}", action="cancel_failed", task_id=task.id)
    return {
        "ok": True,
        "reply": f"任务 #{task.id} 已取消，流程结束（不可续做）。",
        "taskId": task.id,
        "action": "cancelled",
    }


def _handle_resume(project_id: int, task_id: int) -> dict:
    task = TaskDao.find_resumable(project_id, task_id=task_id)
    if not task:
        exists = _load_task(project_id, task_id)
        if not exists:
            return _error_reply(
                f"未找到任务 #{task_id}（请确认任务号属于当前飞书关联项目）。",
                example=f"#{task_id} 续做",
                action="task_miss",
            )
        return _error_reply(
            f"任务 #{task_id} 当前不能「续做」。\n当前状态：{_status_hint(exists)}",
            example=f"#{task_id} 续做",
            action="resume_invalid",
            task_id=task_id,
        )

    status_word = "失败" if task.current_status == TaskStatus.FAILED else "中断"
    try:
        TaskService.resume(task.id)
    except BizException as exc:
        return _error_reply(f"任务 #{task.id} 续做失败：{exc}", action="resume_failed", task_id=task.id)
    except Exception as exc:
        return _error_reply(f"任务 #{task.id} 续做异常：{exc}", action="resume_failed", task_id=task.id)
    return {
        "ok": True,
        "reply": f"任务 #{task.id} 已从{status_word}状态续做，正在重新调度执行…",
        "taskId": task.id,
        "action": "resumed",
    }


def try_handle_review_command(project_id: int, text: str) -> Optional[dict]:
    """若消息是固定指令则处理；格式错误返回提示；无关消息返回 None。"""
    raw = _normalize(text)
    if not raw:
        return None

    if parse_create_body(raw):
        return None

    m = _CMD_APPROVE1.match(raw)
    if m:
        return _handle_approve1(project_id, int(m.group(1)))

    m = _CMD_APPROVE2.match(raw)
    if m:
        return _handle_approve2(project_id, int(m.group(1)))

    m = _CMD_REJECT.match(raw)
    if m:
        return _handle_reject(project_id, int(m.group(1)), m.group(2) or "")

    m = _CMD_RESUME.match(raw)
    if m:
        return _handle_resume(project_id, int(m.group(1)))

    m = _CMD_CANCEL.match(raw)
    if m:
        return _handle_cancel(project_id, int(m.group(1)))

    return _near_miss_reply(raw)


def pending_review_hint(project_id: int) -> Optional[str]:
    task = TaskDao.find_pending_review(project_id)
    if task:
        if task.current_step == TaskStep.HUMAN_REVIEW_1:
            return f"任务 #{task.id} 等待 Review 1，请回复：#{task.id} 同意动工  或  #{task.id} 驳回：意见"
        if task.current_step == TaskStep.HUMAN_REVIEW_2:
            return f"任务 #{task.id} 等待 Review 2，请回复：#{task.id} 合并发布  或  #{task.id} 驳回：意见"

    resumable = TaskDao.find_resumable(project_id)
    if resumable:
        status = "失败" if resumable.current_status == TaskStatus.FAILED else "中断"
        return f"任务 #{resumable.id} 已{status}，请回复：#{resumable.id} 续做"
    return None
