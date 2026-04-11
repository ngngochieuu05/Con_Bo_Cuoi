"""
Repository: model_ai
LÆ°u thĂ´ng tin mĂ´ hĂ¬nh YOLO (YOLOv8/v11...) Ä‘á»™c láº­p theo loáº¡i.
Ănh xáº¡ â†’ models.json
"""
from __future__ import annotations

from datetime import datetime

from dal.base_repo import BaseRepo

_repo = BaseRepo("models", pk_field="id_model")

# Seed 3 mĂ´ hĂ¬nh YOLO Ä‘á»™c láº­p
_SEED = [
    {
        "id_model": 1,
        "ten_mo_hinh": "Nháº­n diá»‡n bĂ²",
        "loai_mo_hinh": "cattle_detect",    # cattle_detect | behavior | disease
        "phien_ban": "v1.0.0",
        "trang_thai": "offline",            # online | testing | offline
        "mo_ta": "PhĂ¡t hiá»‡n & Ä‘á»‹nh vá»‹ bĂ² trong khung hĂ¬nh (bounding box)",
        "duong_dan_file": "",
        "conf": 0.50,
        "iou": 0.45,
        "updated_at": "2026-01-01T00:00:00",
    },
    {
        "id_model": 2,
        "ten_mo_hinh": "HĂ nh vi bĂ²",
        "loai_mo_hinh": "behavior",
        "phien_ban": "v2.1.0",
        "trang_thai": "online",
        "mo_ta": "Nháº­n diá»‡n hĂ nh vi: Ä‘á»©ng, náº±m, Ä‘i láº¡i, hĂºc, giao phá»‘i",
        "duong_dan_file": "models/Dataset/model_22v_behavior.pt",
        "conf": 0.55,
        "iou": 0.45,
        "updated_at": "2026-03-01T08:00:00",
    },
    {
        "id_model": 3,
        "ten_mo_hinh": "Bá»‡nh trĂªn bĂ²",
        "loai_mo_hinh": "disease",
        "phien_ban": "v1.0.0",
        "trang_thai": "offline",
        "mo_ta": "PhĂ¡t hiá»‡n dáº¥u hiá»‡u bá»‡nh qua hĂ¬nh áº£nh: gháº», sÆ°ng, tá»•n thÆ°Æ¡ng da",
        "duong_dan_file": "",
        "conf": 0.60,
        "iou": 0.50,
        "updated_at": "2026-01-01T00:00:00",
    },
]


def init_seed():
    _repo.seed(_SEED)


def get_all_models() -> list[dict]:
    return _repo.all()


def get_model_by_id(id_model: int) -> dict | None:
    return _repo.find_by_id(id_model)


def get_models_by_status(trang_thai: str) -> list[dict]:
    return _repo.find_many(trang_thai=trang_thai)


def get_model_by_type(loai_mo_hinh: str) -> dict | None:
    return _repo.find_one(loai_mo_hinh=loai_mo_hinh)


def create_model(
    ten_mo_hinh: str,
    phien_ban: str,
    trang_thai: str = "offline",
    mo_ta: str = "",
    duong_dan_file: str = "",
    loai_mo_hinh: str = "custom",
    conf: float = 0.5,
    iou: float = 0.45,
) -> dict:
    return _repo.insert({
        "ten_mo_hinh": ten_mo_hinh,
        "loai_mo_hinh": loai_mo_hinh,
        "phien_ban": phien_ban,
        "trang_thai": trang_thai,
        "mo_ta": mo_ta,
        "duong_dan_file": duong_dan_file,
        "conf": conf,
        "iou": iou,
        "updated_at": datetime.now().isoformat(),
    })


def update_model(id_model: int, updates: dict) -> dict | None:
    updates["updated_at"] = datetime.now().isoformat()
    return _repo.update(id_model, updates)


def update_model_status(id_model: int, trang_thai: str) -> dict | None:
    return _repo.update(id_model, {"trang_thai": trang_thai, "updated_at": datetime.now().isoformat()})


def update_model_config(id_model: int, conf: float, iou: float, duong_dan_file: str) -> dict | None:
    """Cáº­p nháº­t cáº¥u hĂ¬nh YOLO (conf, iou, .pt path)."""
    return _repo.update(id_model, {
        "conf": round(float(conf), 3),
        "iou": round(float(iou), 3),
        "duong_dan_file": duong_dan_file,
        "updated_at": datetime.now().isoformat(),
    })


def count_online() -> int:
    return len(get_models_by_status("online"))


def delete_model(id_model: int) -> bool:
    return _repo.delete(id_model)
