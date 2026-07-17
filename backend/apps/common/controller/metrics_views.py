import logging
import time

from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

logger = logging.getLogger("apps.metrics")

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

    HTTP_REQUESTS = Counter("agent_loop_http_requests_total", "HTTP requests", ["method", "path", "status"])
    HTTP_LATENCY = Gauge("agent_loop_http_request_duration_ms", "Last request duration ms", ["path"])
    AGENT_TASKS = Counter("agent_loop_agent_tasks_total", "Agent workflow runs", ["step", "status"])
    PROMETHEUS_OK = True
except ImportError:
    PROMETHEUS_OK = False


class MetricsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not PROMETHEUS_OK:
            return HttpResponse("# prometheus_client not installed\n", content_type="text/plain")
        return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)


def record_http_metric(method: str, path: str, status: int, duration_ms: int):
    if not PROMETHEUS_OK:
        return
    try:
        HTTP_REQUESTS.labels(method=method, path=path, status=str(status)).inc()
        HTTP_LATENCY.labels(path=path).set(duration_ms)
    except Exception as exc:
        logger.debug("metrics record failed: %s", exc)


def record_agent_task(step: str, status: str):
    if not PROMETHEUS_OK:
        return
    try:
        AGENT_TASKS.labels(step=step, status=status).inc()
    except Exception:
        pass
