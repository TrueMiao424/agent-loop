from rest_framework.views import APIView

from apps.common.response import ApiResponse
from apps.task.dto.serializers import TaskSerializer
from apps.task.service.task_service import TaskService


class TaskListCreateView(APIView):
    def get(self, request):
        project_id = request.query_params.get("projectId")
        if not project_id:
            return ApiResponse.fail("projectId 必填", code=40001)
        tasks = TaskService.list_tasks(int(project_id))
        return ApiResponse.ok(TaskSerializer(tasks, many=True).data)

    def post(self, request):
        project_id = request.data.get("projectId")
        title = request.data.get("title", "").strip()
        criteria = request.data.get("acceptanceCriteria", "")
        idem = request.headers.get("X-Idempotency-Key", "")
        if not project_id or not title:
            return ApiResponse.fail("projectId 和 title 必填", code=40001)
        task = TaskService.create_task(int(project_id), title, criteria, idem, request.user)
        return ApiResponse.ok(TaskSerializer(task).data)


class TaskDetailView(APIView):
    def get(self, request, task_id):
        task = TaskService.get_task(task_id)
        return ApiResponse.ok(TaskSerializer(task).data)

    def put(self, request, task_id):
        ser = TaskSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        task = TaskService.update_task(task_id, ser.validated_data)
        return ApiResponse.ok(TaskSerializer(task).data)

    def delete(self, request, task_id):
        TaskService.delete_task(task_id)
        return ApiResponse.ok(msg="已删除")


class TaskReview1View(APIView):
    def post(self, request, task_id):
        task = TaskService.review1(
            task_id,
            request.data.get("confirmed_files", []),
            request.data.get("sub_tasks", []),
            user=request.user,
        )
        return ApiResponse.ok(TaskSerializer(task).data)


class TaskReview2View(APIView):
    def post(self, request, task_id):
        task = TaskService.review2(task_id, user=request.user)
        return ApiResponse.ok(TaskSerializer(task).data)


class TaskOpinionView(APIView):
    def post(self, request, task_id):
        task = TaskService.save_opinion(
            task_id,
            request.data.get("opinion", ""),
            reject=bool(request.data.get("reject")),
            user=request.user,
        )
        return ApiResponse.ok(TaskSerializer(task).data)


class TaskForceStepView(APIView):
    def post(self, request, task_id):
        task = TaskService.force_step(
            task_id,
            request.data.get("step"),
            request.data.get("status"),
            user=request.user,
        )
        return ApiResponse.ok(TaskSerializer(task).data)


class TaskInterruptView(APIView):
    def post(self, request, task_id):
        task = TaskService.interrupt(task_id)
        return ApiResponse.ok(TaskSerializer(task).data, msg="任务已中断")


class TaskCancelView(APIView):
    def post(self, request, task_id):
        task = TaskService.cancel(task_id)
        return ApiResponse.ok(TaskSerializer(task).data, msg="任务已取消")


class TaskResumeView(APIView):
    def post(self, request, task_id):
        task = TaskService.resume(task_id)
        return ApiResponse.ok(TaskSerializer(task).data, msg="任务已续做，等待调度")


class TaskResumableListView(APIView):
    def get(self, request):
        tasks = TaskService.list_resumable()
        return ApiResponse.ok(TaskSerializer(tasks, many=True).data)
