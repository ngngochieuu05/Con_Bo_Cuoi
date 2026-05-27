"""
Repository: hinh_anh_dataset + hanh_vi + lich_su_kiem_duyet
Ánh xạ 3 bảng liên quan đến pipeline HITL.
"""
from __future__ import annotations

from datetime import datetime

from dal.base_repo import BaseRepo

_img_repo = BaseRepo("hinh_anh_dataset", pk_field="id_hinh_anh")
_hv_repo = BaseRepo("hanh_vi", pk_field="id_hanh_vi")
_kd_repo = BaseRepo("lich_su_kiem_duyet", pk_field="id_lich_su")

# ─── Seed dữ liệu mẫu ───────────────────────────────────────────
_IMG_SEED = [
    {
        "id_hinh_anh": 1,
        "duong_dan": "data/dataset/img_001.jpg",
        "trang_thai": "PENDING_REVIEW",
        "id_user": 1,
        "created_at": "2026-04-10T08:00:00",
    },
    {
        "id_hinh_anh": 2,
        "duong_dan": "data/dataset/img_002.jpg",
        "trang_thai": "CLEANED_DATA",
        "id_user": 2,
        "created_at": "2026-04-09T15:30:00",
    },
]

_HV_SEED = [
    {
        "id_hanh_vi": 1,
        "ten_hanh_vi": "cow_fight",
        "bounding_box": {"x_center": 0.5, "y_center": 0.4, "w": 0.3, "h": 0.25},
        "id_hinh_anh": 1,
    },
    {
        "id_hanh_vi": 2,
        "ten_hanh_vi": "cow_normal",
        "bounding_box": {"x_center": 0.6, "y_center": 0.5, "w": 0.2, "h": 0.3},
        "id_hinh_anh": 2,
    },
]

_KD_SEED = [
    {
        "id_lich_su": 1,
        "thoi_gian_duyet": "2026-04-09T16:00:00",
        "id_user": 2,
        "id_hinh_anh": 2,
    },
]


def init_seed():
    _img_repo.seed(_IMG_SEED)
    _hv_repo.seed(_HV_SEED)
    _kd_repo.seed(_KD_SEED)


# ─── hinh_anh_dataset ───────────────────────────────────────────
def get_all_images() -> list[dict]:
    return _img_repo.all()


def get_images_by_status(trang_thai: str) -> list[dict]:
    return _img_repo.find_many(trang_thai=trang_thai)


def get_images_pending() -> list[dict]:
    return get_images_by_status("PENDING_REVIEW")


def add_image(duong_dan: str, id_user: int, trang_thai: str = "PENDING_REVIEW") -> dict:
    return _img_repo.insert({
        "duong_dan": duong_dan,
        "trang_thai": trang_thai,
        "id_user": id_user,
        "created_at": datetime.now().isoformat(),
    })


def update_image_status(id_hinh_anh: int, trang_thai: str) -> dict | None:
    return _img_repo.update(id_hinh_anh, {"trang_thai": trang_thai})


# ─── hanh_vi ────────────────────────────────────────────────────
def get_behaviors_by_image(id_hinh_anh: int) -> list[dict]:
    return _hv_repo.find_many(id_hinh_anh=id_hinh_anh)


def add_behavior(ten_hanh_vi: str, bounding_box: dict, id_hinh_anh: int) -> dict:
    return _hv_repo.insert({
        "ten_hanh_vi": ten_hanh_vi,
        "bounding_box": bounding_box,
        "id_hinh_anh": id_hinh_anh,
    })


# ─── lich_su_kiem_duyet ─────────────────────────────────────────
def get_review_history(id_user: int | None = None) -> list[dict]:
    if id_user is not None:
        return _kd_repo.find_many(id_user=id_user)
    return _kd_repo.all()


def log_review(id_user: int, id_hinh_anh: int) -> dict:
    return _kd_repo.insert({
        "thoi_gian_duyet": datetime.now().isoformat(),
        "id_user": id_user,
        "id_hinh_anh": id_hinh_anh,
    })
