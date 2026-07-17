from apps.auth_app.entity.models import User
from apps.common.util.logging_util import log_method


class UserDao:
    @staticmethod
    @log_method
    def get_by_username(username: str):
        return User.objects.filter(username=username).first()

    @staticmethod
    @log_method
    def create_user(username: str, password: str, display_name: str = "", role: str = "operator"):
        return User.objects.create_user(
            username=username,
            password=password,
            display_name=display_name or username,
            role=role,
        )
