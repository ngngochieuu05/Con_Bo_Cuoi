from __future__ import annotations

from datetime import datetime

from dal.base_repo import BaseRepo

_repo = BaseRepo("monitor_sessions", pk_field="id_session")


def init_seed() -> None:
    _repo.seed([])


def get_all() -> list[dict]:
    return _repo.all()


def get_by_user(id_user: int) -> list[dict]:
    items = _repo.find_many(id_user=id_user)
    items.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return items


def create_session(
    id_user: int,
    camera_label: str,
    source_type: str = "camera",
    source_label: str = "",
    status: str = "running",
) -> dict:
    return _repo.insert(
        {
            "id_user": id_user,
            "camera_label": camera_label,
            "source_type": source_type,
            "source_label": source_label,
            "status": status,
            "started_at": datetime.now().isoformat(),
            "stopped_at": "",
            "frame_count": 0,
        }
    )


def finish_session(id_session: int, status: str = "completed", frame_count: int = 0) -> dict | None:
    return _repo.update(
        id_session,
        {
            "status": status,
            "frame_count": max(0, int(frame_count)),
            "stopped_at": datetime.now().isoformat(),
        },
    )
