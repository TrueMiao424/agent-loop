class ErrorCode:
    SUCCESS = 0
    PARAM_ERROR = 40001
    UNAUTHORIZED = 40101
    FORBIDDEN = 40301
    NOT_FOUND = 40401
    CONFLICT = 40901
    IDEMPOTENT_REJECT = 40902
    RATE_LIMIT = 42901
    SYSTEM_ERROR = 50001
    EXTERNAL_ERROR = 50201


class BizException(Exception):
    def __init__(self, msg: str, code: int = ErrorCode.SYSTEM_ERROR):
        self.msg = msg
        self.code = code
        super().__init__(msg)
