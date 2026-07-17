import json

from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from apps.common.exception.biz_exception import ErrorCode
from apps.common.service.session_cache_service import SessionCacheService


class RateLimitMiddleware(MiddlewareMixin):
    """IP/用户维度限流。"""

    SKIP_PREFIXES = ("/api/feishu/", "/api/auth/login/", "/api/auth/register/", "/api/metrics/", "/api/health/", "/api/config/")

    def process_request(self, request):
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return None
        if not request.path.startswith("/api/"):
            return None
        if any(request.path.startswith(p) for p in self.SKIP_PREFIXES):
            return None

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            client_key = f"user:{user.id}"
        else:
            client_key = f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"

        if SessionCacheService.is_rate_limited(client_key):
            return JsonResponse(
                {"success": False, "code": ErrorCode.RATE_LIMIT, "msg": "请求过于频繁，请稍后再试", "data": None},
                status=429,
            )
        return None
