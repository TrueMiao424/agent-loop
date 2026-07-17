import logging
import threading
import time
from typing import Optional

from django.conf import settings
from django.core.cache import cache

from apps.common.exception.task_interrupted import TaskInterruptedException

logger = logging.getLogger("apps")

_local_cancel_flags: dict = {}
_local_lock = threading.Lock()


class SessionCacheService:
    """Redis 会话/缓存：用户态、任务取消、调度锁、限流。"""

    USER_TTL = 3600
    CANCEL_TTL = 86400
    DISPATCH_LOCK_TTL = 600
    RATE_WINDOW = 60

    @staticmethod
    def _cache_set(key: str, value, timeout: int):
        try:
            cache.set(key, value, timeout=timeout)
            return True
        except Exception as exc:
            logger.warning("Redis set failed key=%s err=%s", key, exc)
            return False

    @staticmethod
    def _cache_get(key: str):
        try:
            return cache.get(key)
        except Exception as exc:
            logger.warning("Redis get failed key=%s err=%s", key, exc)
            return None

    @staticmethod
    def _cache_delete(key: str):
        try:
            cache.delete(key)
        except Exception as exc:
            logger.warning("Redis delete failed key=%s err=%s", key, exc)

    @staticmethod
    def _cache_add(key: str, value, timeout: int) -> bool:
        try:
            return cache.add(key, value, timeout=timeout)
        except Exception as exc:
            logger.warning("Redis add failed key=%s err=%s", key, exc)
            return True

    # --- 用户 Session 缓存 ---
    @staticmethod
    def cache_user_profile(user) -> dict:
        profile = {
            "id": user.id,
            "username": user.username,
            "display_name": getattr(user, "display_name", "") or user.username,
            "role": getattr(user, "role", "operator"),
        }
        SessionCacheService._cache_set(f"user:profile:{user.id}", profile, SessionCacheService.USER_TTL)
        SessionCacheService._cache_set(
            f"user:token_active:{user.id}",
            int(time.time()),
            int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()) + 60,
        )
        return profile

    @staticmethod
    def get_user_profile(user_id: int) -> Optional[dict]:
        return SessionCacheService._cache_get(f"user:profile:{user_id}")

    @staticmethod
    def invalidate_user(user_id: int):
        SessionCacheService._cache_delete(f"user:profile:{user_id}")
        SessionCacheService._cache_delete(f"user:token_active:{user_id}")

    # --- Agent Session 元数据 ---
    @staticmethod
    def register_agent_session(session_id: str, task_id: int, user_id: Optional[int], step: str):
        SessionCacheService._cache_set(
            f"agent:session:{session_id}",
            {"task_id": task_id, "user_id": user_id, "step": step, "started_at": time.time()},
            SessionCacheService.DISPATCH_LOCK_TTL,
        )

    @staticmethod
    def remove_agent_session(session_id: str):
        SessionCacheService._cache_delete(f"agent:session:{session_id}")

    # --- 任务协作式中断 ---
    @staticmethod
    def set_task_cancelled(task_id: int):
        with _local_lock:
            _local_cancel_flags[task_id] = True
        SessionCacheService._cache_set(f"task:cancel:{task_id}", 1, SessionCacheService.CANCEL_TTL)

    @staticmethod
    def clear_task_cancelled(task_id: int):
        with _local_lock:
            _local_cancel_flags.pop(task_id, None)
        SessionCacheService._cache_delete(f"task:cancel:{task_id}")

    @staticmethod
    def is_task_cancelled(task_id: int) -> bool:
        if SessionCacheService._cache_get(f"task:cancel:{task_id}"):
            return True
        with _local_lock:
            return _local_cancel_flags.get(task_id, False)

    @staticmethod
    def ensure_not_cancelled(task_id: int):
        if SessionCacheService.is_task_cancelled(task_id):
            raise TaskInterruptedException()

    # --- 调度锁（防重复 dispatch）---
    @staticmethod
    def acquire_dispatch_lock(task_id: int) -> bool:
        return SessionCacheService._cache_add(
            f"agent:dispatch:lock:{task_id}",
            "1",
            SessionCacheService.DISPATCH_LOCK_TTL,
        )

    @staticmethod
    def release_dispatch_lock(task_id: int):
        SessionCacheService._cache_delete(f"agent:dispatch:lock:{task_id}")

    # --- 限流 ---
    @staticmethod
    def is_rate_limited(client_key: str) -> bool:
        limit = int(getattr(settings, "API_RATE_LIMIT_PER_MINUTE", 120))
        bucket = int(time.time()) // SessionCacheService.RATE_WINDOW
        key = f"ratelimit:{client_key}:{bucket}"
        try:
            count = cache.get(key)
            if count is None:
                cache.add(key, 1, timeout=SessionCacheService.RATE_WINDOW + 5)
                return False
            if int(count) >= limit:
                return True
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, 1, timeout=SessionCacheService.RATE_WINDOW + 5)
            return False
        except Exception as exc:
            logger.warning("Rate limit check failed: %s", exc)
            return False
