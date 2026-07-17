from rest_framework.views import APIView

from apps.common.response import ApiResponse
from apps.project.dto.serializers import ProjectSerializer
from apps.project.service.project_service import ProjectService


class ProjectListCreateView(APIView):
    def get(self, request):
        projects = ProjectService.list_projects()
        return ApiResponse.ok(ProjectSerializer(projects, many=True).data)

    def post(self, request):
        ser = ProjectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        project = ProjectService.create_project(ser.validated_data)
        return ApiResponse.ok(ProjectSerializer(project).data)


class ProjectDetailView(APIView):
    def put(self, request, project_id):
        ser = ProjectSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        project = ProjectService.update_project(project_id, ser.validated_data)
        return ApiResponse.ok(ProjectSerializer(project).data)
