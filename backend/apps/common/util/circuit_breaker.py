import logging
import time
from functools import wraps
from typing import Callable, TypeVar

from django.core.cache import cache

logger = logging.getLogger("apps")

T = TypeVar("T")


class CircuitOpenError(Exception):
    """熔断器打开，拒绝外调。"""


class CircuitBreaker:
    """简单熔断器：失败达阈值后打开，超时后半开。"""

    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

    def _state_key(self):
        return f"circuit:{self.name}:state"

    def _fail_key(self):
        return f"circuit:{self.name}:failures"

    def _open_until_key(self):
        return f"circuit:{self.name}:open_until"

    def _is_open(self) -> bool:
        try:
            open_until = cache.get(self._open_until_key())
            if open_until and float(open_until) > time.time():
                return True
            if open_until:
                cache.delete(self._open_until_key())
                cache.delete(self._fail_key())
            return False
        except Exception:
            return False

    def _record_failure(self):
        try:
            fails = cache.get(self._fail_key()) or 0
            fails = int(fails) + 1
            cache.set(self._fail_key(), fails, timeout=self.recovery_timeout * 2)
            if fails >= self.failure_threshold:
                cache.set(self._open_until_key(), time.time() + self.recovery_timeout, timeout=self.recovery_timeout * 2)
                logger.warning("Circuit OPEN name=%s failures=%s", self.name, fails)
        except Exception as exc:
            logger.warning("Circuit record failure error: %s", exc)

    def _record_success(self):
        try:
            cache.delete(self._fail_key())
            cache.delete(self._open_until_key())
        except Exception:
            pass

    def call(self, fn: Callable[..., T], *args, **kwargs) -> T:
        if self._is_open():
            raise CircuitOpenError(f"Circuit {self.name} is open")
        try:
            result = fn(*args, **kwargs)
            self._record_success()
            return result
        except CircuitOpenError:
            raise
        except Exception:
            self._record_failure()
            raise


def with_circuit_breaker(breaker: CircuitBreaker):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return breaker.call(fn, *args, **kwargs)

        return wrapper

    return decorator


anthropic_breaker = CircuitBreaker("anthropic", failure_threshold=5, recovery_timeout=120)
feishu_breaker = CircuitBreaker("feishu", failure_threshold=3, recovery_timeout=60)
