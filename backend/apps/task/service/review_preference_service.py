import json
from datetime import datetime

from apps.common.util.logging_util import log_method
from apps.settings_app.dao.settings_dao import SettingsDao


def _prefs_key(user_id: int) -> str:
    return f"user_review_prefs_{user_id}"


class ReviewPreferenceService:
    @staticmethod
    @log_method
    def get_summary(user_id: int) -> str:
        if not user_id:
            return ""
        raw = SettingsDao.get(_prefs_key(user_id), "")
        if not raw:
            return ""
        try:
            data = json.loads(raw)
            return data.get("summary", "") or ""
        except json.JSONDecodeError:
            return raw

    @staticmethod
    @log_method
    def get_history(user_id: int) -> list:
        if not user_id:
            return []
        raw = SettingsDao.get(_prefs_key(user_id), "")
        if not raw:
            return []
        try:
            return json.loads(raw).get("history", [])
        except json.JSONDecodeError:
            return []

    @staticmethod
    @log_method
    def append_opinion(user_id: int, step: str, opinion: str, task_id: int = None):
        if not user_id or not opinion.strip():
            return
        raw = SettingsDao.get(_prefs_key(user_id), "")
        try:
            data = json.loads(raw) if raw else {"summary": "", "history": []}
        except json.JSONDecodeError:
            data = {"summary": "", "history": []}

        entry = {
            "step": step,
            "opinion": opinion.strip(),
            "taskId": task_id,
            "at": datetime.now().isoformat(),
        }
        history = list(data.get("history") or [])
        history.append(entry)
        data["history"] = history[-50:]
        data["summary"] = ReviewPreferenceService._build_summary(history)
        SettingsDao.set_many({_prefs_key(user_id): json.dumps(data, ensure_ascii=False)})

    @staticmethod
    def _build_summary(history: list) -> str:
        if not history:
            return ""
        lines = []
        for item in history[-20:]:
            step = item.get("step", "")
            opinion = (item.get("opinion") or "").strip()
            if not opinion:
                continue
            label = "需求拆解" if "Review_1" in step or step == "Requirement_Refinement" else "代码开发"
            lines.append(f"- [{label}] {opinion}")
        if not lines:
            return ""
        return "用户 Review 偏好总结（来自历史意见）：\n" + "\n".join(lines)
