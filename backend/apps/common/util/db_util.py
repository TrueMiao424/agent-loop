from functools import wraps

from django.db import close_old_connections


def with_db_cleanup(fn):
    """后台线程使用 ORM 前后关闭过期连接，避免连接池耗尽/假死。"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        close_old_connections()
        try:
            return fn(*args, **kwargs)
        finally:
            close_old_connections()

    return wrapper
