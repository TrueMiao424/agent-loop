from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views import View


class HealthView(View):
    def get(self, request):
        checks = {"database": self._check_database(), "cache": self._check_cache()}
        ok = all(checks.values())
        return JsonResponse(
            {
                "ok": ok,
                "service": "agent-loop-backend",
                "checks": checks,
            },
            status=200 if ok else 503,
        )

    @staticmethod
    def _check_database() -> bool:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception:
            return False

    @staticmethod
    def _check_cache() -> bool:
        try:
            from django.core.cache import cache

            key = "health:ping"
            cache.set(key, 1, 5)
            return cache.get(key) == 1
        except Exception:
            return False
