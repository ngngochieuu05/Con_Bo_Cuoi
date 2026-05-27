"""
Repository: activity_log
Ghi lại hành động quan trọng của người dùng / hệ thống.
Mỗi bản ghi: id_log, user_id, action, details, timestamp.
"""
from __future__ import annotations

from datetime import datetime

from dal.base_repo import BaseRepo

_repo = BaseRepo("activity_log", pk_field="id_log")


def insert_log(user_id: int | None, action: str, details: str = "") -> dict:
    return _repo.insert({
        "user_id":   user_id,
        "action":    action,
        "details":   details,
        "timestamp": datetime.now().isoformat(),
    })


def get_all() -> list[dict]:
    return _repo.all()


def get_recent(limit: int = 20) -> list[dict]:
    logs = _repo.all()
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return logs[:limit]


def get_by_user(user_id: int) -> list[dict]:
    return _repo.find_many(user_id=user_id)


def count() -> int:
    return _repo.count()
