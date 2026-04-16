"""
BLL — Kiểm Duyệt Dữ Liệu (Expert)
Nghiệp vụ chuyên gia kiểm duyệt ảnh trong pipeline HITL (Human-In-The-Loop).
Chỉ Expert (chuyên gia thú y) mới có quyền truy cập.
"""
from __future__ import annotations

from dal.dataset_repo import (
    get_images_pending,
    get_all_images,
    get_images_by_status,
    update_image_status,
    get_behaviors_by_image,
    log_review,
)


# ─── Trạng thái ảnh dataset ──────────────────────────────────────────────────
STATUS_PENDING  = "PENDING_REVIEW"
STATUS_APPROVED = "CLEANED_DATA"
STATUS_REJECTED = "REJECTED"


def get_pending_images() -> list[dict]:
    """Lấy tất cả ảnh đang chờ kiểm duyệt."""
    return get_images_pending()


def get_reviewed_images() -> list[dict]:
    """Lấy tất cả ảnh đã kiểm duyệt (CLEANED_DATA + REJECTED)."""
    approved = get_images_by_status(STATUS_APPROVED)
    rejected  = get_images_by_status(STATUS_REJECTED)
    return approved + rejected


def get_all_dataset_images() -> list[dict]:
    """Lấy toàn bộ ảnh dataset."""
    return get_all_images()


def approve_image(id_hinh_anh: int, id_user: int) -> tuple[bool, str]:
    """
    Duyệt ảnh: cập nhật trạng thái → CLEANED_DATA và ghi lịch sử.
    Trả về (success, message).
    """
    result = update_image_status(id_hinh_anh, STATUS_APPROVED)
    if result is None:
        return False, f"Không tìm thấy ảnh ID={id_hinh_anh}."
    log_review(id_user, id_hinh_anh)
    return True, "Đã duyệt ảnh thành công."


def reject_image(id_hinh_anh: int, id_user: int) -> tuple[bool, str]:
    """
    Từ chối ảnh: cập nhật trạng thái → REJECTED và ghi lịch sử.
    Trả về (success, message).
    """
    result = update_image_status(id_hinh_anh, STATUS_REJECTED)
    if result is None:
        return False, f"Không tìm thấy ảnh ID={id_hinh_anh}."
    log_review(id_user, id_hinh_anh)
    return True, "Đã từ chối ảnh."


def get_image_detail(id_hinh_anh: int) -> dict:
    """
    Lấy chi tiết ảnh kèm danh sách hành vi gắn nhãn.
    Trả về {'image': dict | None, 'behaviors': list[dict]}.
    """
    all_imgs = get_all_images()
    img = next((i for i in all_imgs if i["id_hinh_anh"] == id_hinh_anh), None)
    behaviors = get_behaviors_by_image(id_hinh_anh) if img else []
    return {"image": img, "behaviors": behaviors}


def get_review_summary() -> dict:
    """
    Tóm tắt thống kê:
        total, pending, approved, rejected
    """
    all_imgs = get_all_images()
    pending  = sum(1 for i in all_imgs if i.get("trang_thai") == STATUS_PENDING)
    approved = sum(1 for i in all_imgs if i.get("trang_thai") == STATUS_APPROVED)
    rejected = sum(1 for i in all_imgs if i.get("trang_thai") == STATUS_REJECTED)
    return {
        "total":    len(all_imgs),
        "pending":  pending,
        "approved": approved,
        "rejected": rejected,
    }
