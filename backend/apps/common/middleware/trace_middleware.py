import uuid

from django.utils.deprecation import MiddlewareMixin

from apps.common.middleware.trace import set_trace_id


class TraceMiddleware(MiddlewareMixin):
    def process_request(self, request):
        trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
        request.trace_id = trace_id
        set_trace_id(trace_id)
