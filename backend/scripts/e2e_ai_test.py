"""端到端测试：PM 拆解 → Review1 → 自动开发 → Review2"""
import json
import os
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.common.constant.task_constants import TaskStatus, TaskStep
from apps.task.client.llm_client import AnthropicClient
from apps.task.dao.task_dao import TaskDao
from apps.task.service.task_service import TaskService
from apps.task.service.workflow_service import AgentOrchestrator, WorkflowService

TASK_ID = 3  # seed_ai_try 创建的任务


def wait_step(task_id: int, step: str, timeout: int = 120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = TaskDao.get_by_id(task_id)
        if task.current_step == step and task.current_status == TaskStatus.INIT:
            return task
        if task.current_status == TaskStatus.FAILED:
            raise RuntimeError(f"任务失败: {task.fail_reason}")
        time.sleep(2)
    task = TaskDao.get_by_id(task_id)
    raise TimeoutError(f"等待 {step} 超时，当前 {task.current_step}/{task.current_status}")


def wait_processing_done(task_id: int, expect_step: str, timeout: int = 180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = TaskDao.get_by_id(task_id)
        if task.current_step == expect_step and task.current_status == TaskStatus.INIT:
            return task
        if task.current_status == TaskStatus.FAILED:
            raise RuntimeError(f"任务失败: {task.fail_reason}")
        time.sleep(3)
    task = TaskDao.get_by_id(task_id)
    raise TimeoutError(f"等待进入 {expect_step} 超时，当前 {task.current_step}/{task.current_status}")


def run_phase(task_id: int):
    task = TaskDao.get_by_id(task_id)
    if task.current_status != TaskStatus.INIT:
        print(f"  skip dispatch: status={task.current_status}")
        return
    print(f"  dispatch step={task.current_step} ...")
    AgentOrchestrator.dispatch(task_id)


def main():
    task_id = int(sys.argv[1]) if len(sys.argv) > 1 else TASK_ID
    task = TaskDao.get_by_id(task_id)
    if not task:
        print(f"任务 #{task_id} 不存在")
        sys.exit(1)

    cfg = AnthropicClient._config(task.created_by_id)
    print("=" * 50)
    print("AI 配置")
    print(f"  Anthropic: {AnthropicClient.is_configured(task.created_by_id)}")
    print(f"  URL: {cfg['base_url']}")
    print(f"  Model: {cfg['model']}")
    print("=" * 50)
    print(f"任务 #{task.id}: {task.title}")
    print(f"  初始: {task.current_step} / {task.current_status}")
    print()

    # Phase 1: PM 拆解
    if task.current_step == TaskStep.REQUIREMENT_REFINEMENT:
        print("[1/4] PM Agent 需求拆解...")
        run_phase(task_id)
        task = wait_processing_done(task_id, TaskStep.HUMAN_REVIEW_1)
        files = (task.affected_files or {}).get("predicted_by_agent", [])
        print(f"  -> Review 1 | 预测文件: {files}")
        print(f"  -> 子任务数: {len(task.sub_tasks or [])}")
        for st in (task.sub_tasks or [])[:3]:
            print(f"     - {st.get('title', '')}")

    task = TaskDao.get_by_id(task_id)

    # Phase 2: Review 1
    if task.current_step == TaskStep.HUMAN_REVIEW_1:
        print("\n[2/4] 模拟人工 Review 1...")
        files = (task.affected_files or {}).get("predicted_by_agent", [])
        TaskService.review1(task_id, files, task.sub_tasks or [])
        task = TaskDao.get_by_id(task_id)
        print(f"  -> {task.current_step} / {task.current_status}")

    task = TaskDao.get_by_id(task_id)

    # Phase 3: 自动开发
    if task.current_step == TaskStep.AUTO_DEVELOPMENT:
        print("\n[3/4] Coding Agent 自动开发（约 30~60s）...")
        run_phase(task_id)
        task = wait_processing_done(task_id, TaskStep.HUMAN_REVIEW_2, timeout=180)
        diffs = task.code_diffs or []
        print(f"  -> Review 2 | diff 文件数: {len(diffs)}")
        for d in diffs[:3]:
            print(f"     - {d.get('filePath', '?')}")

    task = TaskDao.get_by_id(task_id)

    # Phase 4: Review 2 + 发布
    if task.current_step == TaskStep.HUMAN_REVIEW_2:
        print("\n[4/4] 模拟人工 Review 2 + 发布...")
        TaskService.review2(task_id)
        run_phase(task_id)
        deadline = time.time() + 30
        while time.time() < deadline:
            task = TaskDao.get_by_id(task_id)
            if task.current_status == TaskStatus.FINISHED:
                break
            time.sleep(1)
        print(f"  -> {task.current_step} / {task.current_status}")

    task = TaskDao.get_by_id(task_id)
    print("\n" + "=" * 50)
    print("测试结果")
    print(f"  最终状态: {task.current_step} / {task.current_status}")
    print(f"  预测文件: {(task.affected_files or {}).get('predicted_by_agent', [])}")
    print(f"  diff 数: {len(task.code_diffs or [])}")
    mock_hit = any("src/main.py" == f for f in (task.affected_files or {}).get("predicted_by_agent", []))
    kanban_hit = any("Kanban" in f or "kanban" in f for f in (task.affected_files or {}).get("predicted_by_agent", []))
    print(f"  是否 mock 数据: {'是 (src/main.py)' if mock_hit and not kanban_hit else '否'}")
    print(f"  是否命中 KanbanView: {'是' if kanban_hit else '否'}")
    logs = (task.execution_logs or "")[-500:]
    print(f"  日志末尾:\n{logs}")
    print("=" * 50)
    ok = task.current_status == TaskStatus.FINISHED and kanban_hit
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
