import json
import re
from typing import Optional

from apps.common.constant.task_constants import TaskStep
from apps.common.util.logging_util import log_method
from apps.task.client.llm_client import AnthropicClient
from apps.task.service.review_preference_service import ReviewPreferenceService


AUTO_REVIEW_SYSTEM = """你是 Review Agent。根据用户历史 Review 偏好，审查 Agent 产出。
只输出 JSON，不要 markdown：
{"passed": true/false, "summary": "中文总结", "issues": ["问题1", "问题2"]}
passed=true 表示基本符合用户偏好，可进入人工 Review；passed=false 表示存在明显不符合偏好的问题。"""


def _extract_json(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"(\{[\s\S]*\})", text)
    return match.group(1) if match else text


class AutoReviewService:
    @staticmethod
    @log_method
    def review_task(task, review_step: str) -> dict:
        user_id = task.created_by_id
        prefs = ReviewPreferenceService.get_summary(user_id)
        if not prefs:
            return {
                "passed": True,
                "summary": "暂无历史 Review 偏好，跳过自动 Review",
                "issues": [],
                "skipped": True,
            }

        if review_step == TaskStep.HUMAN_REVIEW_1:
            content = {
                "acceptanceCriteria": task.acceptance_criteria,
                "subTasks": task.sub_tasks,
                "affectedFiles": task.affected_files,
            }
            focus = "需求拆解结果（子任务与影响文件）"
        else:
            content = {
                "acceptanceCriteria": task.acceptance_criteria,
                "codeDiffs": [
                    {"filePath": d.get("filePath"), "diffText": (d.get("diffText") or "")[:500]}
                    for d in (task.code_diffs or [])[:8]
                ],
            }
            focus = "代码变更 diff"

        if AnthropicClient.is_configured(user_id):
            return AutoReviewService._llm_review(user_id, task.id, prefs, focus, content)

        return AutoReviewService._rule_review(prefs, content, review_step)

    @staticmethod
    def _llm_review(user_id: int, task_id: int, prefs: str, focus: str, content: dict) -> dict:
        prompt = (
            f"用户偏好：\n{prefs}\n\n"
            f"待审查内容（{focus}）：\n{json.dumps(content, ensure_ascii=False, indent=2)}\n\n"
            "请判断是否满足用户偏好。"
        )
        try:
            raw, _ = AnthropicClient.generate(
                prompt,
                system=AUTO_REVIEW_SYSTEM,
                user_id=user_id,
                task_id=task_id,
                allow_fallback=True,
            )
            parsed = json.loads(_extract_json(raw))
            return {
                "passed": bool(parsed.get("passed", True)),
                "summary": parsed.get("summary", ""),
                "issues": parsed.get("issues") or [],
                "skipped": False,
            }
        except Exception as exc:
            return {
                "passed": True,
                "summary": f"自动 Review 跳过: {exc}",
                "issues": [],
                "skipped": True,
            }

    @staticmethod
    def _rule_review(prefs: str, content: dict, review_step: str) -> dict:
        issues = []
        prefs_lower = prefs.lower()
        if review_step == TaskStep.HUMAN_REVIEW_1:
            sub_tasks = content.get("subTasks") or []
            if "子任务" in prefs and len(sub_tasks) < 3:
                issues.append("子任务数量偏少，历史偏好要求更细的拆解")
            if "测试" in prefs and not any("测试" in (st.get("title") or "") for st in sub_tasks):
                issues.append("子任务中缺少测试相关项")
        else:
            diffs = content.get("codeDiffs") or []
            if "注释" in prefs and not diffs:
                issues.append("未生成代码 diff")
        passed = len(issues) == 0
        return {
            "passed": passed,
            "summary": "基于规则的用户偏好检查" + ("通过" if passed else "发现问题"),
            "issues": issues,
            "skipped": False,
        }
