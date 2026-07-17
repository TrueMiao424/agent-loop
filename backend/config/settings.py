import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-key")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "apps.common",
    "apps.auth_app",
    "apps.project",
    "apps.task",
    "apps.session",
    "apps.webhook",
    "apps.settings_app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.trace_middleware.TraceMiddleware",
    "apps.common.middleware.access_log_middleware.AccessLogMiddleware",
    "apps.common.middleware.rate_limit_middleware.RateLimitMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# MySQL with connection pool
DATABASES = {
    "default": {
        "ENGINE": "dj_db_conn_pool.backends.mysql",
        "NAME": os.getenv("DB_NAME", "agent_loop"),
        "USER": os.getenv("DB_USER", "root"),
        "PASSWORD": os.getenv("DB_PASSWORD", "123456"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"},
        "POOL_OPTIONS": {
            "POOL_SIZE": int(os.getenv("DB_POOL_SIZE", "20")),
            "MAX_OVERFLOW": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "RECYCLE": int(os.getenv("DB_POOL_RECYCLE", "3600")),
            "PRE_PING": True,
        },
    }
}


def _locmem_cache():
    return {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "agent-loop-local",
        }
    }


def _redis_ping_ok(redis_url: str) -> bool:
    try:
        import redis

        client = redis.from_url(redis_url, socket_connect_timeout=0.3, socket_timeout=0.3)
        client.ping()
        client.close()
        return True
    except Exception:
        return False


def _build_cache_config():
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    use_redis = os.getenv("USE_REDIS", "auto").lower()
    if use_redis == "false":
        return _locmem_cache()
    if use_redis == "auto" and not _redis_ping_ok(redis_url):
        import logging

        logging.getLogger("apps").warning(
            "Redis unavailable (%s), falling back to LocMemCache. "
            "Start Redis or set USE_REDIS=true when ready.",
            redis_url,
        )
        return _locmem_cache()
    return {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": redis_url,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": 0.5,
                "SOCKET_TIMEOUT": 0.5,
                "IGNORE_EXCEPTIONS": True,
            },
        }
    }


CACHES = _build_cache_config()
DJANGO_REDIS_IGNORE_EXCEPTIONS = True

AUTH_USER_MODEL = "auth_app.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "EXCEPTION_HANDLER": "apps.common.exception.handler.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
}

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    *(f"http://{host}:{port}" for host in ("localhost", "127.0.0.1") for port in range(5173, 5180)),
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Agent loop config
AGENT_MAX_CONCURRENT_SESSIONS = int(os.getenv("AGENT_MAX_CONCURRENT_SESSIONS", "2"))
AGENT_EXECUTOR_WORKERS = int(os.getenv("AGENT_EXECUTOR_WORKERS", "4"))
API_RATE_LIMIT_PER_MINUTE = int(os.getenv("API_RATE_LIMIT_PER_MINUTE", "120"))
# 开发环境默认关闭限流，避免 Redis 异常拖死 runserver；生产请设 RATE_LIMIT_ENABLED=true
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false" if DEBUG else "true").lower() == "true"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_AUTH_TOKEN = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
CLAUDE_SETTINGS_PATH = os.getenv(
    "CLAUDE_SETTINGS_PATH",
    str(Path.home() / ".claude" / "settings.json"),
)

# Git / CI (业务层真实执行)
GIT_PUSH_ENABLED = os.getenv("GIT_PUSH_ENABLED", "false").lower() == "true"
GIT_AUTO_INIT = os.getenv("GIT_AUTO_INIT", "true").lower() == "true"
GIT_DEFAULT_BRANCH = os.getenv("GIT_DEFAULT_BRANCH", "main")
# Agent：true=必须 API/CLI，禁止静默 mock；false=允许 fallback（仅开发演示）
# Agent：优先配置管理页 Anthropic API Key；CLI 为备选（需 CLAUDE_CLI_ENABLED=true 且无 Key 时）
AGENT_PREFER_ANTHROPIC_API = os.getenv("AGENT_PREFER_ANTHROPIC_API", "true").lower() == "true"
AGENT_REQUIRE_REAL_LLM = os.getenv("AGENT_REQUIRE_REAL_LLM", "true").lower() == "true"
CLAUDE_CLI_ENABLED = os.getenv("CLAUDE_CLI_ENABLED", "false").lower() == "true"
# 发布钩子：shell 命令，可用环境变量 AGENT_LOOP_TASK_ID / AGENT_LOOP_PROJECT_PATH
DEPLOY_HOOK_SCRIPT = os.getenv("DEPLOY_HOOK_SCRIPT", "")
DEPLOY_HOOK_TIMEOUT = int(os.getenv("DEPLOY_HOOK_TIMEOUT", "300"))
CI_STRICT = os.getenv("CI_STRICT", "false" if DEBUG else "true").lower() == "true"
PROJECT_PATH_AUTO_CREATE = os.getenv("PROJECT_PATH_AUTO_CREATE", "true").lower() == "true"
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
# 启用后后端随 runserver 启动自研飞书 WebSocket 长连接（需 pip install lark-oapi）
FEISHU_WS_ENABLED = os.getenv("FEISHU_WS_ENABLED", "false").lower() == "true"
FEISHU_WS_REQUIRE_MENTION = os.getenv("FEISHU_WS_REQUIRE_MENTION", "true").lower() == "true"

# Celery 异步队列（USE_CELERY=true 时需另开 worker）
USE_CELERY = os.getenv("USE_CELERY", "false").lower() == "true"
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
CELERY_TASK_TRACK_STARTED = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] [%(levelname)s] [trace=%(trace_id)s] %(name)s - %(message)s",
        },
    },
    "filters": {
        "trace_filter": {"()": "apps.common.middleware.trace.TraceLogFilter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "filters": ["trace_filter"],
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "agent_loop.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "standard",
            "filters": ["trace_filter"],
            "encoding": "utf-8",
        },
    },
    "root": {"handlers": ["console", "file"], "level": LOG_LEVEL},
    "loggers": {
        "apps": {"handlers": ["console"] if DEBUG else ["console", "file"], "level": LOG_LEVEL, "propagate": False},
        "apps.api": {"handlers": ["console"] if DEBUG else ["console", "file"], "level": "INFO", "propagate": False},
        "apps.scheduler": {"handlers": ["console"] if DEBUG else ["console", "file"], "level": "INFO", "propagate": False},
        "external": {"handlers": ["console"] if DEBUG else ["console", "file"], "level": LOG_LEVEL, "propagate": False},
        "dj_db_conn_pool": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
