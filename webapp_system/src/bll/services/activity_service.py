"""
BLL — Activity Service
Ghi log hành động hệ thống và lấy recent activity cho Dashboard Admin.
"""
from __future__ import annotations

from dal.activity_log_repo import insert_log, get_recent as _get_recent

# (action_key → (nhãn tiếng Việt, badge_kind))
_ACTION_LABELS: dict[str, tuple[str, str]] = {
    "LOGIN":           ("Đăng nhập",       "primary"),
    "LOGOUT":          ("Đăng xuất",       "warning"),
    "CREATE_USER":     ("Tạo tài khoản",   "primary"),
    "DELETE_USER":     ("Xóa tài khoản",   "danger"),
    "UPDATE_USER":     ("Cập nhật TK",     "warning"),
    "CREATE_CAMERA":   ("Thêm camera",     "primary"),
    "DELETE_CAMERA":   ("Xóa camera",      "danger"),
    "UPDATE_CAMERA":   ("Cập nhật cam",    "warning"),
    "ALERT_RESOLVED":  ("Xử lý cảnh báo", "primary"),
    "MODEL_UPDATED":   ("Cập nhật model",  "secondary"),
    "MODEL_TRAINED":   ("Train model",     "secondary"),
}


def log_action(user_id: int | None, action: str, details: str = "") -> None:
    """Ghi một hành động vào log. Không throw exception."""
    try:
        insert_log(user_id, action, details)
    except Exception:
        pass


def get_recent_activities(limit: int = 15) -> list[dict]:
    """
    Trả về các bản ghi log gần nhất, đã thêm trường 'label' và 'kind'
    để UI render trực tiếp.
    """
    logs = _get_recent(limit)
    result = []
    for log in logs:
        action = log.get("action", "")
        label, kind = _ACTION_LABELS.get(action, (action, "warning"))
        result.append({**log, "label": label, "kind": kind})
    return result


def get_action_meta(action: str) -> tuple[str, str]:
    return _ACTION_LABELS.get(action, (action, "warning"))
