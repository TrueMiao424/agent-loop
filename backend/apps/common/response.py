from rest_framework.response import Response


class ApiResponse:
    """Unified response body: code, msg, data, success."""

    @staticmethod
    def ok(data=None, msg="success", code=0):
        return Response({"code": code, "msg": msg, "data": data, "success": True})

    @staticmethod
    def fail(msg="error", code=1, data=None, http_status=400):
        return Response({"code": code, "msg": msg, "data": data, "success": False}, status=http_status)
