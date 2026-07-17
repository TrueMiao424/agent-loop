from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.common.response import ApiResponse


class PublicConfigView(APIView):
    """前端可读的运行参数（无需登录）。"""

    permission_classes = [AllowAny]
    def get(self, request):
        return ApiResponse.ok(
            {
                "maxConcurrentSessions": settings.AGENT_MAX_CONCURRENT_SESSIONS,
                "agentPreferAnthropicApi": getattr(settings, "AGENT_PREFER_ANTHROPIC_API", True),
                "rateLimitEnabled": getattr(settings, "RATE_LIMIT_ENABLED", False),
            }
        )
