"""
Repository: camera_chuong
Ánh xạ bảng camera_chuong → camera_chuong.json
"""
from __future__ import annotations

from dal.base_repo import BaseRepo

_repo = BaseRepo("camera_chuong", pk_field="id_camera_chuong")

_SEED = [
    {
        "id_camera_chuong": 1,
        "id_chuong": "CHUONG-A",
        "khu_vuc_chuong": "Khu A",
        "id_camera": "CAM-01",
        "id_user": 3,
        "trang_thai": "online",
        "updated_at": "2026-04-10T10:45:00",
    },
    {
        "id_camera_chuong": 2,
        "id_chuong": "CHUONG-B",
        "khu_vuc_chuong": "Khu B",
        "id_camera": "CAM-03",
        "id_user": 3,
        "trang_thai": "warning",
        "updated_at": "2026-04-10T10:42:00",
    },
    {
        "id_camera_chuong": 3,
        "id_chuong": "CHUONG-C",
        "khu_vuc_chuong": "Khu C",
        "id_camera": "CAM-07",
        "id_user": 3,
        "trang_thai": "offline",
        "updated_at": "2026-04-10T10:40:00",
    },
]


def init_seed():
    _repo.seed(_SEED)


def get_all() -> list[dict]:
    return _repo.all()


# Alias for readability
get_all_cameras = get_all


def get_by_user(id_user: int) -> list[dict]:
    return _repo.find_many(id_user=id_user)


def get_by_camera_id(id_camera: str) -> dict | None:
    return _repo.find_one(id_camera=id_camera)


def create_camera(id_chuong: str, khu_vuc: str, id_camera: str, id_user: int) -> dict:
    from datetime import datetime
    return _repo.insert({
        "id_chuong":       id_chuong,
        "khu_vuc_chuong":  khu_vuc,
        "id_camera":       id_camera,
        "id_user":         id_user,
        "trang_thai":      "offline",
        "updated_at":      datetime.now().isoformat(),
    })


def update_camera(id_camera_chuong: int, updates: dict) -> dict | None:
    from datetime import datetime
    updates = {**updates, "updated_at": datetime.now().isoformat()}
    return _repo.update(id_camera_chuong, updates)


def update_camera_status(id_camera_chuong: int, trang_thai: str) -> dict | None:
    from datetime import datetime
    return _repo.update(id_camera_chuong, {
        "trang_thai": trang_thai,
        "updated_at": datetime.now().isoformat(),
    })


def delete_camera(id_camera_chuong: int) -> bool:
    return _repo.delete(id_camera_chuong)


def count() -> int:
    return _repo.count()
