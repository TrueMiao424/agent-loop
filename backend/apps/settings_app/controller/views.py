from rest_framework.views import APIView

from apps.common.exception.biz_exception import BizException, ErrorCode
from apps.common.response import ApiResponse
from apps.settings_app.service.settings_service import SettingsService


class SettingsView(APIView):
    def get(self, request):
        return ApiResponse.ok(SettingsService.get_settings(request.user))

    def post(self, request):
        result = SettingsService.save_settings(request.user, request.data)
        return ApiResponse.ok(result, msg="配置已保存")


class SettingsTestView(APIView):
    def post(self, request):
        try:
            result = SettingsService.test_agent_llm(request.user)
            return ApiResponse.ok(result, msg="连接成功")
        except Exception as exc:
            raise BizException(str(exc), ErrorCode.EXTERNAL_ERROR)
