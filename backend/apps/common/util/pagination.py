from typing import Any, Dict, List, Tuple


def parse_page_params(request, default_size: int = 20, max_size: int = 100) -> Tuple[int, int]:
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.query_params.get("pageSize", default_size))
    except (TypeError, ValueError):
        page_size = default_size
    page_size = max(1, min(page_size, max_size))
    return page, page_size


def paginate_queryset(qs, page: int, page_size: int) -> Tuple[List[Any], int]:
    total = qs.count()
    start = (page - 1) * page_size
    items = list(qs[start : start + page_size])
    return items, total


def page_payload(items, total: int, page: int, page_size: int, **extra: Any) -> Dict[str, Any]:
    data = {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
    }
    data.update(extra)
    return data
