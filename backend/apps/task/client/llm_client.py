import json
import re
import time
from datetime import datetime
from typing import List, Optional, Tuple

import requests
from django.conf import settings

from apps.common.util.circuit_breaker import CircuitOpenError, anthropic_breaker
from apps.common.util.logging_util import log_external_call, log_method
from apps.project.util.project_context_util import build_file_context, read_convention
from apps.task.client.claude_cli_client import ClaudeCliClient
from apps.task.util.diff_validate_util import validate_code_diffs

PM_SYSTEM = """你是 PM Agent。根据需求拆解为 JSON，只输出 JSON，不要 markdown 代码块。
格式：
{"predicted_files": ["相对路径"], "sub_tasks": [{"id": "st-1", "title": "中文描述", "completed": false}]}
要求：
- predicted_files 3～8 个相对路径，贴合项目结构
- sub_tasks 3～5 条可执行子任务，title 用中文
"""

CODING_SYSTEM = """你是 Coding Agent。根据需求在项目中实现代码，输出 JSON 数组，只输出 JSON，不要 markdown。
格式：
[{"filePath": "相对路径", "original": "修改前完整内容或空字符串", "modified": "修改后完整可运行源码", "diffText": "简要 unified diff 摘要"}]
硬性要求：
- modified 必须是完整源码，禁止用一句话描述代替代码
- 新建文件 original 为空字符串
- 每个 filePath 只出现一次
- Python 文件需可运行；包含必要 import
"""


def _extract_json(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    return match.group(1) if match else text


def _require_real_llm() -> bool:
    return getattr(settings, "AGENT_REQUIRE_REAL_LLM", True)


class AnthropicClient:
    """Anthropic Messages API（按用户配置 Key / Base URL）。"""

    @classmethod
    def _config(cls, user_id: Optional[int] = None) -> dict:
        from apps.settings_app.dao.settings_dao import get_agent_llm_config, read_claude_settings

        cfg = get_agent_llm_config(user_id)
        if not cfg["api_key"] and user_id is None:
            claude = read_claude_settings()
            env = claude.get("env") or {}
            if env.get("ANTHROPIC_AUTH_TOKEN"):
                cfg = {
                    "api_key": env.get("ANTHROPIC_AUTH_TOKEN", ""),
                    "base_url": (env.get("ANTHROPIC_BASE_URL") or cfg["base_url"]).rstrip("/"),
                    "model": claude.get("model") or cfg["model"],
                }
        return cfg

    @classmethod
    def is_configured(cls, user_id: Optional[int] = None) -> bool:
        return bool(cls._config(user_id)["api_key"])

    @classmethod
    @log_method
    def generate(
        cls,
        prompt: str,
        system: str = "",
        user_id: Optional[int] = None,
        task_id: Optional[int] = None,
        allow_fallback: bool = False,
    ) -> Tuple[str, dict]:
        meta = {"source": "anthropic_api", "fallback": False, "model": "", "base_url": ""}
        if task_id is not None:
            from apps.common.service.session_cache_service import SessionCacheService

            SessionCacheService.ensure_not_cancelled(task_id)

        cfg = cls._config(user_id)
        if not cfg["api_key"]:
            if _require_real_llm() and not allow_fallback:
                raise ValueError("未配置 API Key，请在「配置管理」填写 Anthropic API Key")
            meta["source"] = "fallback"
            meta["fallback"] = True
            return LlmFallback.response(prompt), meta

        meta["model"] = cfg["model"]
        meta["base_url"] = cfg["base_url"]
        url = f"{cfg['base_url']}/v1/messages"
        headers = {
            "x-api-key": cfg["api_key"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": cfg["model"],
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system

        start = time.time()
        try:
            resp = anthropic_breaker.call(
                requests.post,
                url,
                json=body,
                headers=headers,
                timeout=120,
            )
            duration = int((time.time() - start) * 1000)
            log_external_call("anthropic", url, {"model": cfg["model"], "prompt_len": len(prompt)}, resp.text[:2000], duration)
            resp.raise_for_status()
            data = resp.json()
            blocks = data.get("content") or []
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
            if task_id is not None:
                from apps.common.service.session_cache_service import SessionCacheService

                SessionCacheService.ensure_not_cancelled(task_id)
            return text.strip(), meta
        except CircuitOpenError as exc:
            duration = int((time.time() - start) * 1000)
            log_external_call("anthropic", url, {"model": cfg["model"]}, {"circuit_open": True}, duration, str(exc))
            if _require_real_llm() and not allow_fallback:
                raise ValueError("Anthropic 熔断中，请稍后再试") from exc
            meta["source"] = "fallback"
            meta["fallback"] = True
            return LlmFallback.response(prompt), meta
        except Exception as exc:
            duration = int((time.time() - start) * 1000)
            log_external_call("anthropic", url, {"model": cfg["model"]}, None, duration, str(exc))
            raise

    @classmethod
    @log_method
    def test_connection(cls, user_id: int) -> str:
        cfg = cls._config(user_id)
        if not cfg["api_key"]:
            raise ValueError("未配置 API Key")

        url = f"{cfg['base_url']}/v1/messages"
        headers = {
            "x-api-key": cfg["api_key"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": cfg["model"],
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "回复：OK"}],
            "system": "只回复 OK 两个字母，不要其他内容",
        }

        start = time.time()
        try:
            resp = anthropic_breaker.call(
                requests.post,
                url,
                json=body,
                headers=headers,
                timeout=90,
            )
            duration = int((time.time() - start) * 1000)
            log_external_call("anthropic", url, {"model": cfg["model"], "test": True}, resp.text[:500], duration)
            resp.raise_for_status()
            data = resp.json()
            blocks = data.get("content") or []
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip() or "OK"
        except CircuitOpenError as exc:
            duration = int((time.time() - start) * 1000)
            log_external_call("anthropic", url, {"test": True}, {"circuit_open": True}, duration, str(exc))
            raise ValueError("Anthropic 熔断中，请稍后再试") from exc
        except Exception as exc:
            duration = int((time.time() - start) * 1000)
            log_external_call("anthropic", url, {"test": True}, None, duration, str(exc))
            raise


class LlmFallback:
    @staticmethod
    def response(prompt: str) -> str:
        lower = prompt.lower()
        if "decompose" in lower or "subtask" in lower or "拆解" in prompt:
            return json.dumps(
                {
                    "predicted_files": ["src/main.py", "README.md"],
                    "sub_tasks": [
                        {"id": "st-1", "title": "分析需求并列出改动文件", "completed": False},
                        {"id": "st-2", "title": "实现核心逻辑", "completed": False},
                        {"id": "st-3", "title": "补充测试与文档", "completed": False},
                    ],
                },
                ensure_ascii=False,
            )
        if "diff" in lower or "code" in lower or "coding" in lower:
            return json.dumps(
                [
                    {
                        "filePath": "src/main.py",
                        "original": "# TODO\n",
                        "modified": "#!/usr/bin/env python3\n\"\"\"Agent Loop demo module.\"\"\"\n\n\ndef main():\n    print('hello agent loop')\n\n\nif __name__ == '__main__':\n    main()\n",
                        "diffText": "+def main(): ...",
                    }
                ],
                ensure_ascii=False,
            )
        return json.dumps({"intent": "CHAT_COMMENT"}, ensure_ascii=False)


class GeminiClient:
    BASE = "https://generativelanguage.googleapis.com/v1beta"

    @classmethod
    @log_method
    def generate(cls, prompt: str, user_id: Optional[int] = None, allow_fallback: bool = False) -> Tuple[str, dict]:
        if AnthropicClient.is_configured(user_id):
            return AnthropicClient.generate(prompt, user_id=user_id, allow_fallback=allow_fallback)
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            if _require_real_llm() and not allow_fallback:
                raise ValueError("未配置 API Key")
            return LlmFallback.response(prompt), {"source": "fallback", "fallback": True}
        url = f"{cls.BASE}/models/gemini-2.0-flash:generateContent?key={api_key}"
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        start = time.time()
        try:
            resp = requests.post(url, json=body, timeout=60)
            duration = int((time.time() - start) * 1000)
            log_external_call("gemini", url, body, resp.text[:2000], duration)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"], {"source": "gemini", "fallback": False}
        except Exception as exc:
            duration = int((time.time() - start) * 1000)
            log_external_call("gemini", url, body, None, duration, str(exc))
            if _require_real_llm() and not allow_fallback:
                raise
            return LlmFallback.response(prompt), {"source": "fallback", "fallback": True}


class ClaudeCodeClient:
    """Coding Agent：优先 Anthropic API（配置管理 Key），备选 Claude CLI。"""

    @staticmethod
    def _use_api(user_id: Optional[int]) -> bool:
        if not AnthropicClient.is_configured(user_id):
            return False
        if getattr(settings, "AGENT_PREFER_ANTHROPIC_API", True):
            return True
        return not ClaudeCliClient.is_available()

    @staticmethod
    def _use_cli(user_id: Optional[int], project_path: str) -> bool:
        if not project_path or not ClaudeCliClient.is_available():
            return False
        if AnthropicClient.is_configured(user_id) and getattr(settings, "AGENT_PREFER_ANTHROPIC_API", True):
            return False
        return True

    @staticmethod
    @log_method
    def build_command(user_id: Optional[int] = None) -> str:
        if ClaudeCodeClient._use_api(user_id):
            cfg = AnthropicClient._config(user_id)
            return f"anthropic-api ({cfg['model']}) @ {cfg['base_url']}"
        if ClaudeCliClient.is_available():
            return "claude --dangerously-skip-permissions"
        return "未配置（请在配置管理填写 Anthropic API Key）"

    @staticmethod
    @log_method
    def run(
        task_id: int,
        prompt: str,
        confirmed_files: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        project_path: str = "",
        convention_text: str = "",
        review_feedback: str = "",
    ) -> Tuple[str, dict]:
        ts = datetime.now().strftime("%H:%M:%S")
        files_hint = "\n".join(f"- {f}" for f in (confirmed_files or []))
        full_prompt = (
            f"任务 #{task_id} 开发需求：\n{prompt}\n\n"
            f"请在以下文件中实现（相对项目根目录）：\n{files_hint or '(由你推断)'}\n\n"
        )
        if convention_text:
            full_prompt += f"编码规范：\n{convention_text[:4000]}\n\n"
        if review_feedback:
            full_prompt += f"人工 Review 修改意见（请据此重新实现）：\n{review_feedback}\n\n"
        full_prompt += "直接修改项目内文件，输出可运行代码。"

        if ClaudeCodeClient._use_api(user_id):
            cfg = AnthropicClient._config(user_id)
            lines = [
                f"[{ts}] Coding Agent: Anthropic API ({cfg['model']})",
                f"[{ts}] Base URL: {cfg['base_url']}",
            ]
            user_prompt = f"{full_prompt}\n\n请输出 3～8 条中文实现要点（不要 JSON）。"
            summary, meta = AnthropicClient.generate(
                user_prompt,
                system="你是 Coding Agent，输出简洁中文要点列表。",
                user_id=user_id,
                task_id=task_id,
            )
            for line in summary.splitlines():
                lines.append(f"[{ts}] {line}")
            return "\n".join(lines) + "\n", meta

        if ClaudeCodeClient._use_cli(user_id, project_path):
            lines = [f"[{ts}] Coding Agent: Claude Code CLI (备选)", f"[{ts}] $ claude -p \"...\""]
            output, ok = ClaudeCliClient.run_in_project(project_path, full_prompt)
            for line in output.splitlines()[:80]:
                lines.append(f"[{ts}] {line}")
            if not ok:
                lines.append(f"[{ts}] WARN: CLI exit != 0，仍将尝试收集 git diff")
            return "\n".join(lines) + "\n", {"source": "claude_cli", "fallback": False}

        raise ValueError("未配置 Anthropic API Key，请在「配置管理」填写后再创建/执行任务")

    @staticmethod
    @log_method
    def generate_diffs(
        acceptance_criteria: str,
        confirmed_files: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        task_id: Optional[int] = None,
        project_path: str = "",
        convention_text: str = "",
        cli_already_ran: bool = False,
        review_feedback: str = "",
    ) -> Tuple[list, dict]:
        if cli_already_ran and project_path:
            diffs = ClaudeCliClient.collect_diffs_from_git(project_path, confirmed_files)
            if diffs:
                errors = validate_code_diffs(diffs)
                if not errors:
                    return diffs, {"source": "claude_cli", "fallback": False}
            # CLI 未产生 git 变更时继续走 API 生成

        file_ctx = build_file_context(project_path, confirmed_files or []) if project_path else ""
        prompt = (
            f"需求验收标准：\n{acceptance_criteria}\n\n"
            f"必须修改的文件：{', '.join(confirmed_files or []) or '由你推断'}\n\n"
        )
        if convention_text:
            prompt += f"编码规范：\n{convention_text[:4000]}\n\n"
        if file_ctx:
            prompt += f"当前工作区文件内容：\n{file_ctx}\n\n"
        if review_feedback:
            prompt += f"人工 Review 修改意见（请据此重新生成代码）：\n{review_feedback}\n\n"
        prompt += "请输出完整可运行的 modified 源码 JSON 数组。"

        raw, meta = AnthropicClient.generate(
            prompt,
            system=CODING_SYSTEM,
            user_id=user_id,
            task_id=task_id,
        )
        try:
            parsed = json.loads(_extract_json(raw))
            diffs = parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            raise ValueError("Coding Agent 返回的不是合法 JSON diff 数组")

        errors = validate_code_diffs(diffs)
        if errors:
            raise ValueError("生成的 diff 无效: " + "; ".join(errors))
        return diffs, meta

    @staticmethod
    @log_method
    def resolve_mode(user_id: Optional[int] = None, project_path: str = "") -> str:
        if ClaudeCodeClient._use_api(user_id):
            return "anthropic_api"
        if ClaudeCodeClient._use_cli(user_id, project_path):
            return "claude_cli"
        return "unconfigured"


class PmAgentClient:
    @staticmethod
    @log_method
    def decompose(
        acceptance_criteria: str,
        user_id: Optional[int] = None,
        task_id: Optional[int] = None,
        convention_text: str = "",
        review_feedback: str = "",
    ) -> Tuple[dict, dict]:
        system = PM_SYSTEM
        if convention_text:
            system += f"\n\n项目编码规范摘要：\n{convention_text[:3000]}"

        prompt = f"需求 PRD：\n{acceptance_criteria}\n\n请拆解为 predicted_files 与 sub_tasks。"
        if review_feedback:
            prompt += f"\n\n人工 Review 修改意见（请据此重新拆解）：\n{review_feedback}"
        try:
            if AnthropicClient.is_configured(user_id):
                raw, meta = AnthropicClient.generate(
                    prompt,
                    system=system,
                    user_id=user_id,
                    task_id=task_id,
                    allow_fallback=not _require_real_llm(),
                )
            else:
                raw, meta = GeminiClient.generate(prompt, user_id=user_id, allow_fallback=not _require_real_llm())
            parsed = json.loads(_extract_json(raw))
            return {
                "predicted_files": parsed.get("predicted_files", []),
                "sub_tasks": parsed.get("sub_tasks", []),
            }, meta
        except (json.JSONDecodeError, Exception) as exc:
            if _require_real_llm():
                raise ValueError(f"PM Agent 拆解失败: {exc}") from exc
            raw = LlmFallback.response(prompt)
            parsed = json.loads(raw)
            return {
                "predicted_files": parsed.get("predicted_files", []),
                "sub_tasks": parsed.get("sub_tasks", []),
            }, {"source": "fallback", "fallback": True}
