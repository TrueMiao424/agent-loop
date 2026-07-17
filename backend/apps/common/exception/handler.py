from rest_framework.views import exception_handler

from apps.common.exception.biz_exception import BizException
from apps.common.response import ApiResponse


def custom_exception_handler(exc, context):
    if isinstance(exc, BizException):
        return ApiResponse.fail(msg=exc.msg, code=exc.code)

    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data
        msg = detail.get("detail") if isinstance(detail, dict) else str(detail)
        return ApiResponse.fail(msg=str(msg), code=response.status_code, http_status=response.status_code)

    return ApiResponse.fail(msg="Internal server error", code=50001, http_status=500)
