import logging
import time

from django.utils.deprecation import MiddlewareMixin

from apps.common.middleware.trace import get_trace_id

logger = logging.getLogger("apps.api")


class AccessLogMiddleware(MiddlewareMixin):
    """API 入站请求/响应日志。"""

    def process_request(self, request):
        request._access_start = time.time()

    def process_response(self, request, response):
        if not request.path.startswith("/api/"):
            return response
        duration = int((time.time() - getattr(request, "_access_start", time.time())) * 1000)
        user_id = getattr(getattr(request, "user", None), "id", None)
        logger.info(
            "API %s %s status=%s duration_ms=%s user_id=%s trace=%s",
            request.method,
            request.path,
            response.status_code,
            duration,
            user_id,
            get_trace_id(),
        )
        try:
            from apps.common.controller.metrics_views import record_http_metric

            record_http_metric(request.method, request.path, response.status_code, duration)
        except Exception:
            pass
        return response
