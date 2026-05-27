"""
Repository: model_ai
Lưu thông tin mô hình YOLO (YOLOv8/v11...) độc lập theo loại.
Ánh xạ -> models.json
"""
from __future__ import annotations

from datetime import datetime

from dal.base_repo import BaseRepo

_repo = BaseRepo("models", pk_field="id_model")

# Seed các mô hình YOLO độc lập (chỉ dùng khi DB chưa có bản ghi)
_SEED = [
    {
        "id_model": 1,
        "ten_mo_hinh": "Nhận diện bò",
        "loai_mo_hinh": "cattle_detect",
        "phien_ban": "v1.0.0",
        "trang_thai": "online",
        "mo_ta": "Phát hiện và định vị bò trong khung hình (bounding box)",
        "duong_dan_file": "models_trained/model_tong_hop/train_yolov8m-seg_500epv2/weights/best.pt",
        "conf": 0.50,
        "iou": 0.45,
        "updated_at": "2026-05-01T00:00:00",
    },
    {
        "id_model": 2,
        "ten_mo_hinh": "Hành vi bò",
        "loai_mo_hinh": "behavior",
        "phien_ban": "v2.1.0",
        "trang_thai": "online",
        "mo_ta": "Nhận diện hành vi: đứng, nằm, đi lại, húc, giao phối",
        "duong_dan_file": "models_trained/behavior/v1/train_yolov8s_200ep/weights/best.pt",
        "conf": 0.55,
        "iou": 0.45,
        "updated_at": "2026-05-01T00:00:00",
    },
    {
        "id_model": 3,
        "ten_mo_hinh": "Bệnh trên bò",
        "loai_mo_hinh": "disease",
        "phien_ban": "v1.0.0",
        "trang_thai": "offline",
        "mo_ta": "Phát hiện dấu hiệu bệnh qua hình ảnh: ghẻ, sưng, tổn thương da",
        "duong_dan_file": "models_trained/desease/jilsa2022_3class/insegment/train_yolov8m-seg_85ep/weights/best.pt",
        "conf": 0.60,
        "iou": 0.50,
        "updated_at": "2026-05-01T00:00:00",
    },
    {
        "id_model": 4,
        "ten_mo_hinh": "Phân loại bệnh bò",
        "loai_mo_hinh": "disease_cls",
        "phien_ban": "v1.0.0",
        "trang_thai": "offline",
        "mo_ta": "Model classification chạy song song với segmentation để xếp hạng mức độ nghi ngờ bệnh.",
        "duong_dan_file": "",
        "conf": 0.60,
        "iou": 0.50,
        "updated_at": "2026-05-01T00:00:00",
    },
    {
        "id_model": 5,
        "ten_mo_hinh": "Sàng lọc bò khỏe/bệnh",
        "loai_mo_hinh": "health_cls",
        "phien_ban": "v1.0.0",
        "trang_thai": "offline",
        "mo_ta": "Model classification gate ở bước đầu để quyết định có cần chạy tiếp phân loại bệnh và segmentation hay không.",
        "duong_dan_file": "",
        "conf": 0.60,
        "iou": 0.50,
        "updated_at": "2026-05-01T00:00:00",
    },
]


def init_seed():
    _repo.seed(_SEED)
    _ensure_missing_seed_models()


def _ensure_missing_seed_models() -> None:
    for rec in _SEED:
        loai = rec.get("loai_mo_hinh")
        if loai and not _repo.find_one(loai_mo_hinh=loai):
            _repo.insert(dict(rec))


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
    return _repo.update(id_model, {
        "trang_thai": trang_thai,
        "updated_at": datetime.now().isoformat(),
    })


def update_model_config(id_model: int, conf: float, iou: float, duong_dan_file: str) -> dict | None:
    """Cập nhật cấu hình YOLO (conf, iou, đường dẫn .pt)."""
    return _repo.update(id_model, {
        "conf": round(float(conf), 3),
        "iou": round(float(iou), 3),
        "duong_dan_file": duong_dan_file,
        "updated_at": datetime.now().isoformat(),
    })


def count_online() -> int:
    return len(get_models_by_status("online"))
