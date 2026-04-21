"""
BLL — Model Management (Admin)
Nghiệp vụ quản lý mô hình YOLO: kích hoạt, cập nhật đường dẫn, xoá cache.
Chỉ Admin mới có quyền thao tác.
"""
from __future__ import annotations

from datetime import datetime

from dal.model_repo import (
    get_all_models,
    get_model_by_id,
    get_model_by_type,
    resolve_model_path,
    update_model as _dal_update_model,
    update_model_status as _dal_update_status,
    update_model_config as _dal_update_config,
    create_model,
)


def list_models() -> list[dict]:
    """Lấy danh sách tất cả model."""
    return get_all_models()


def activate_model(id_model: int, duong_dan_file: str) -> tuple[bool, str]:
    """
    Kích hoạt model: cập nhật đường dẫn file + đặt trạng thái 'online'.
    Trả về (success, message).
    """
    from pathlib import Path
    if not duong_dan_file.strip():
        return False, "Đường dẫn file không được để trống."
    if not Path(duong_dan_file).exists():
        return False, f"File không tồn tại: {duong_dan_file}"
    result = update_model(id_model, {
        "duong_dan_file": duong_dan_file.strip(),
        "trang_thai": "online",
        "updated_at": datetime.now().isoformat(),
    })
    if result:
        # Xoá cache AI nếu model disease vừa cập nhật
        _clear_ai_cache_if_disease(id_model)
        return True, f"Đã kích hoạt model ID={id_model}."
    return False, "Không tìm thấy model trong DB."


def deactivate_model(id_model: int) -> tuple[bool, str]:
    """Đặt model về trạng thái 'offline'."""
    result = update_model(id_model, {
        "trang_thai": "offline",
        "updated_at": datetime.now().isoformat(),
    })
    if result:
        _clear_ai_cache_if_disease(id_model)
        return True, f"Đã tắt model ID={id_model}."
    return False, "Không tìm thấy model trong DB."


def update_model_config(id_model: int, **kwargs) -> tuple[bool, str]:
    """
    Cập nhật cấu hình model (conf, iou, phien_ban, mo_ta, ...).
    Trả về (success, message).
    """
    allowed_keys = {"conf", "iou", "phien_ban", "mo_ta", "duong_dan_file", "trang_thai"}
    updates = {k: v for k, v in kwargs.items() if k in allowed_keys}
    if not updates:
        return False, "Không có tham số hợp lệ để cập nhật."
    updates["updated_at"] = datetime.now().isoformat()
    result = update_model(id_model, updates)
    if result:
        _clear_ai_cache_if_disease(id_model)
        return True, "Đã cập nhật cấu hình model."
    return False, "Không tìm thấy model trong DB."


def get_disease_model_info() -> dict | None:
    """Lấy thông tin model disease (id=3) để hiển thị trên UI."""
    return get_model_by_type("disease")


def get_model_status_summary() -> dict:
    """
    Tóm tắt trạng thái 3 model:
        {loai_mo_hinh: {"ten": str, "trang_thai": str, "duong_dan_file": str}}
    """
    models = get_all_models()
    return {
        m["loai_mo_hinh"]: {
            "ten": m.get("ten_mo_hinh", ""),
            "trang_thai": m.get("trang_thai", "offline"),
            "duong_dan_file": m.get("duong_dan_file", ""),
        }
        for m in models
    }


def promote_model(id_model: int) -> tuple[bool, str]:
    """Promote a model to production for its type and demote current online siblings."""
    target = get_model_by_id(id_model)
    if not target:
        return False, "Khong tim thay model."

    resolved_path = resolve_model_path(target.get("duong_dan_file", ""))
    if not resolved_path:
        return False, "Model chua co duong dan file .pt."

    model_type = target.get("loai_mo_hinh", "")
    siblings = [model for model in get_all_models() if model.get("loai_mo_hinh") == model_type]
    for sibling in siblings:
        sibling_id = sibling.get("id_model")
        if sibling_id == id_model:
            continue
        if sibling.get("trang_thai") == "online":
            _dal_update_model(
                sibling_id,
                {
                    "trang_thai": "offline",
                    "updated_at": datetime.now().isoformat(),
                },
            )

    result = _dal_update_model(
        id_model,
        {
            "duong_dan_file": resolved_path,
            "trang_thai": "online",
            "updated_at": datetime.now().isoformat(),
        },
    )
    if result:
        _clear_ai_cache_if_disease(id_model)
        return True, "Da dua model len production."
    return False, "Khong the cap nhat model."


def set_model_testing(id_model: int) -> tuple[bool, str]:
    """Mark a model as testing without promoting it to production."""
    result = _dal_update_model(
        id_model,
        {
            "trang_thai": "testing",
            "updated_at": datetime.now().isoformat(),
        },
    )
    if result:
        _clear_ai_cache_if_disease(id_model)
        return True, "Da chuyen model sang testing."
    return False, "Khong the cap nhat model."


# ── Thin wrappers với chữ ký khớp DAL — dùng từ UI ──────────────────────────

def update_model_status(id_model: int, trang_thai: str) -> dict | None:
    """Cập nhật trạng thái model. Tự xoá AI cache nếu cần."""
    result = _dal_update_status(id_model, trang_thai)
    if result:
        _clear_ai_cache_if_disease(id_model)
    return result


def update_model_config(id_model: int, conf: float, iou: float,
                        duong_dan_file: str) -> dict | None:
    """Cập nhật conf/IOU/đường dẫn file model. Tự xoá AI cache nếu cần."""
    result = _dal_update_config(id_model, conf, iou, duong_dan_file)
    if result:
        _clear_ai_cache_if_disease(id_model)
    return result


def update_model(id_model: int, updates: dict) -> dict | None:
    """Cập nhật tuỳ ý field của model (ví dụ phien_ban). Xoá AI cache nếu cần."""
    result = _dal_update_model(id_model, updates)
    if result:
        _clear_ai_cache_if_disease(id_model)
    return result


# ─── internal ────────────────────────────────────────────────────────────────

def _clear_ai_cache_if_disease(id_model: int):
    """Xoá cache YOLO khi model disease bị thay đổi."""
    try:
        rec = get_model_by_id(id_model)
        if rec and rec.get("loai_mo_hinh") == "disease":
            from bll.user.farmer.tu_van_ai import clear_model_cache
            clear_model_cache()
    except Exception:
        pass
