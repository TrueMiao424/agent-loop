from apps.common.util.logging_util import log_method
from apps.session.dao.session_dao import SessionDao


class SessionService:
    @staticmethod
    @log_method
    def list_sessions():
        return SessionDao.list_all()

    @staticmethod
    @log_method
    def list_sessions_page(page: int, page_size: int):
        from apps.common.util.pagination import paginate_queryset

        items, total = paginate_queryset(SessionDao.list_all(), page, page_size)
        return items, total, SessionDao.count_processing()

    @staticmethod
    @log_method
    def reset_all():
        SessionDao.reset_all()
