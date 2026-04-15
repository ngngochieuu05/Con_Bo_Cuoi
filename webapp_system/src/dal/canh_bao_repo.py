"""
Repository: canh_bao_su_co
Ánh xạ bảng canh_bao_su_co → canh_bao_su_co.json
"""
from __future__ import annotations

from datetime import datetime

from dal.base_repo import BaseRepo

_repo = BaseRepo("canh_bao_su_co", pk_field="id_canh_bao")

_SEED = [
    {
        "id_canh_bao": 1,
        "loai_canh_bao": "cow_fight",
        "trang_thai": "CHUA_XU_LY",
        "id_user": 3,
        "id_camera_chuong": 1,
        "created_at": "2026-04-10T10:40:00",
    },
    {
        "id_canh_bao": 2,
        "loai_canh_bao": "cow_lie",
        "trang_thai": "DA_XU_LY",
        "id_user": 3,
        "id_camera_chuong": 2,
        "created_at": "2026-04-10T09:15:00",
    },
]


def init_seed():
    _repo.seed(_SEED)


def get_all() -> list[dict]:
    return _repo.all()


def get_by_user(id_user: int) -> list[dict]:
    return _repo.find_many(id_user=id_user)


def get_by_status(trang_thai: str) -> list[dict]:
    return _repo.find_many(trang_thai=trang_thai)


def create_alert(loai_canh_bao: str, id_user: int, id_camera_chuong: int) -> dict:
    return _repo.insert({
        "loai_canh_bao": loai_canh_bao,
        "trang_thai": "CHUA_XU_LY",
        "id_user": id_user,
        "id_camera_chuong": id_camera_chuong,
        "created_at": datetime.now().isoformat(),
    })


def resolve_alert(id_canh_bao: int) -> dict | None:
    return _repo.update(id_canh_bao, {"trang_thai": "DA_XU_LY"})


def count_open() -> int:
    return len(get_by_status("CHUA_XU_LY"))
