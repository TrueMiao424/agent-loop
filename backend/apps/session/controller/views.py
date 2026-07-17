from rest_framework.views import APIView

from apps.common.response import ApiResponse
from apps.session.dto.serializers import SessionSerializer
from apps.session.service.session_service import SessionService


class SessionListView(APIView):
    def get(self, request):
        from apps.common.util.pagination import page_payload, parse_page_params

        page, page_size = parse_page_params(request)
        sessions, total, processing_count = SessionService.list_sessions_page(page, page_size)
        return ApiResponse.ok(
            page_payload(
                SessionSerializer(sessions, many=True).data,
                total,
                page,
                page_size,
                processingCount=processing_count,
            )
        )


class SessionResetView(APIView):
    def post(self, request):
        SessionService.reset_all()
        return ApiResponse.ok(msg="已重置所有会话")
