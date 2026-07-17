from apps.common.constant.task_constants import TaskStep
from apps.common.middleware.trace import new_trace_id, run_with_trace
from apps.common.util.logging_util import log_method
from config.celery import app


@app.task(name="task.run_workflow_step", bind=True, max_retries=0)
def run_workflow_step(self, task_id: int, session_id: str, step: str):
    trace_id = new_trace_id(f"celery-{task_id}")

    def work():
        from apps.task.service.workflow_service import WorkflowService

        if step == TaskStep.REQUIREMENT_REFINEMENT:
            WorkflowService.run_requirement_refinement(task_id, session_id)
        elif step == TaskStep.AUTO_DEVELOPMENT:
            WorkflowService.run_auto_development(task_id, session_id)
        elif step == TaskStep.COMMIT_PUSH:
            WorkflowService.run_commit_push(task_id, session_id)

    run_with_trace(trace_id, work)


@log_method
def dispatch_workflow_async(task_id: int, session_id: str, step: str):
    run_workflow_step.delay(task_id, session_id, step)
