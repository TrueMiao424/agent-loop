from apps.common.exception.biz_exception import BizException, ErrorCode
from apps.common.util.logging_util import log_method
from apps.project.dao.project_dao import ProjectDao


class ProjectService:
    @staticmethod
    @log_method
    def list_projects():
        return ProjectDao.list_all()

    @staticmethod
    @log_method
    def create_project(data: dict):
        chat_id = (data.get("chat_group_id") or "").strip()
        if not chat_id:
            raise BizException("群会话 ID 不能为空", ErrorCode.PARAM_ERROR)
        if chat_id.startswith("http"):
            raise BizException("请填写飞书群 chat_id，不要填写 Webhook URL", ErrorCode.PARAM_ERROR)
        return ProjectDao.create(**data)

    @staticmethod
    @log_method
    def update_project(project_id: int, data: dict):
        project = ProjectDao.get_by_id(project_id)
        if not project:
            raise BizException("项目不存在", ErrorCode.NOT_FOUND)
        return ProjectDao.update(project, **data)
