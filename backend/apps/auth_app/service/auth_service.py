import threading

from django.contrib.auth import authenticate

from apps.auth_app.dao.user_dao import UserDao
from apps.common.exception.biz_exception import BizException, ErrorCode
from apps.common.service.session_cache_service import SessionCacheService
from apps.common.util.logging_util import log_method


class AuthService:
    @staticmethod
    @log_method
    def login(username: str, password: str):
        user = authenticate(username=username, password=password)
        if not user:
            raise BizException("用户名或密码错误", ErrorCode.UNAUTHORIZED)
        # 用户资料缓存走后台，避免 Redis 慢/不可用时拖慢登录
        threading.Thread(
            target=SessionCacheService.cache_user_profile,
            args=(user,),
            daemon=True,
            name=f"cache-profile-{user.id}",
        ).start()
        return user

    @staticmethod
    @log_method
    def get_user_profile(user):
        cached = SessionCacheService.get_user_profile(user.id)
        if cached:
            return cached
        return SessionCacheService.cache_user_profile(user)

    @staticmethod
    @log_method
    def register(username: str, password: str, display_name: str = ""):
        if UserDao.get_by_username(username):
            raise BizException("用户名已存在", ErrorCode.CONFLICT)
        return UserDao.create_user(username, password, display_name)
