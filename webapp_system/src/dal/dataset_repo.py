"""
Dataset repository for expert HITL review flows.
"""
from __future__ import annotations

from datetime import datetime

from dal.base_repo import BaseRepo

STATUS_PENDING_REVIEW = "PENDING_REVIEW"
STATUS_AI_SCANNED = "AI_SCANNED"
STATUS_NEEDS_VERIFICATION = "NEEDS_VERIFICATION"
STATUS_WAITING_MORE_DATA = "WAITING_MORE_DATA"
STATUS_REJECTED = "REJECTED"
STATUS_VERIFIED = "VERIFIED"
STATUS_VERIFIED_DATASET = "VERIFIED_DATASET"
STATUS_CLEANED_DATA = "CLEANED_DATA"

FINAL_STATUSES = {STATUS_REJECTED, STATUS_VERIFIED, STATUS_VERIFIED_DATASET, STATUS_CLEANED_DATA}
ACTIVE_STATUSES = {
    STATUS_PENDING_REVIEW,
    STATUS_AI_SCANNED,
    STATUS_NEEDS_VERIFICATION,
    STATUS_WAITING_MORE_DATA,
}
APPROVED_STATUSES = {STATUS_VERIFIED, STATUS_VERIFIED_DATASET, STATUS_CLEANED_DATA}

_img_repo = BaseRepo("hinh_anh_dataset", pk_field="id_hinh_anh")
_hv_repo = BaseRepo("hanh_vi", pk_field="id_hanh_vi")
_kd_repo = BaseRepo("lich_su_kiem_duyet", pk_field="id_lich_su")

_IMG_SEED = [
    {
        "id_hinh_anh": 1,
        "duong_dan": "data/dataset/img_001.jpg",
        "trang_thai": STATUS_PENDING_REVIEW,
        "id_user": 1,
        "created_at": "2026-04-10T08:00:00",
    },
    {
        "id_hinh_anh": 2,
        "duong_dan": "data/dataset/img_002.jpg",
        "trang_thai": STATUS_CLEANED_DATA,
        "id_user": 2,
        "created_at": "2026-04-09T15:30:00",
    },
    {
        "id_hinh_anh": 3,
        "duong_dan": "data/dataset/img_003.jpg",
        "trang_thai": STATUS_AI_SCANNED,
        "id_user": 1,
        "created_at": "2026-04-11T09:10:00",
        "ai_primary_label": "mastitis",
        "ai_confidence": 0.82,
        "ai_summary": "mastitis 82%, swelling 61%",
        "last_ai_scan_at": "2026-04-11T09:15:00",
    },
    {
        "id_hinh_anh": 4,
        "duong_dan": "data/dataset/img_004.jpg",
        "trang_thai": STATUS_NEEDS_VERIFICATION,
        "id_user": 3,
        "created_at": "2026-04-11T11:20:00",
        "ai_primary_label": "lameness",
        "ai_confidence": 0.54,
        "ai_summary": "lameness 54%",
        "linked_case_id": 1004,
        "linked_case_summary": "Ca bò đi khập khiễng sau khi phối giống",
    },
    {
        "id_hinh_anh": 5,
        "duong_dan": "data/dataset/img_005.jpg",
        "trang_thai": STATUS_WAITING_MORE_DATA,
        "id_user": 4,
        "created_at": "2026-04-12T07:40:00",
        "request_more_reason": "Cần ảnh góc nghiêng và cận vùng chân sau.",
        "review_note": "Ảnh mờ, khó xác nhận tổn thương.",
    },
    {
        "id_hinh_anh": 6,
        "duong_dan": "data/dataset/img_006.jpg",
        "trang_thai": STATUS_VERIFIED_DATASET,
        "id_user": 2,
        "created_at": "2026-04-12T10:00:00",
        "expert_label": "mụn cóc da",
        "symptom_notes": "Tổn thương nhỏ, bờ rõ, chưa thấy viêm lan.",
        "reviewed_by": 2,
        "reviewed_at": "2026-04-12T11:30:00",
        "reviewer_name": "Expert 02",
        "verified_dataset": True,
    },
    {
        "id_hinh_anh": 7,
        "duong_dan": "data/dataset/img_007.jpg",
        "trang_thai": STATUS_REJECTED,
        "id_user": 5,
        "created_at": "2026-04-12T13:25:00",
        "reject_reason": "Ảnh không chứa bò hoặc vùng bệnh cần xem xét.",
        "reviewed_by": 3,
        "reviewed_at": "2026-04-12T14:00:00",
        "reviewer_name": "Expert 03",
    },
    {
        "id_hinh_anh": 8,
        "duong_dan": "data/dataset/img_008.jpg",
        "trang_thai": STATUS_PENDING_REVIEW,
        "id_user": 1,
        "created_at": "2026-04-13T08:05:00",
        "linked_case_id": 1008,
        "linked_case_summary": "Ca nghi viêm móng ở bò sữa số 12",
    },
    {
        "id_hinh_anh": 9,
        "duong_dan": "data/dataset/img_009.jpg",
        "trang_thai": STATUS_AI_SCANNED,
        "id_user": 3,
        "created_at": "2026-04-13T09:45:00",
        "ai_primary_label": "skin_lesion",
        "ai_confidence": 0.73,
        "ai_summary": "skin_lesion 73%",
        "last_ai_scan_at": "2026-04-13T09:50:00",
    },
    {
        "id_hinh_anh": 10,
        "duong_dan": "data/dataset/img_010.jpg",
        "trang_thai": STATUS_PENDING_REVIEW,
        "id_user": 4,
        "created_at": "2026-04-13T15:15:00",
    },
    {
        "id_hinh_anh": 11,
        "duong_dan": "data/dataset/img_011.jpg",
        "trang_thai": STATUS_WAITING_MORE_DATA,
        "id_user": 2,
        "created_at": "2026-04-14T07:55:00",
        "request_more_reason": "Thiếu ảnh phần tai trái để đối chiếu.",
        "linked_case_id": 1011,
        "linked_case_summary": "Ca theo dõi sốt và biếng ăn ngày 14/04",
    },
    {
        "id_hinh_anh": 12,
        "duong_dan": "data/dataset/img_012.jpg",
        "trang_thai": STATUS_VERIFIED_DATASET,
        "id_user": 5,
        "created_at": "2026-04-14T16:20:00",
        "expert_label": "viêm da nhẹ",
        "symptom_notes": "Mảng đỏ nhỏ, theo dõi thêm 48 giờ.",
        "reviewed_by": 1,
        "reviewed_at": "2026-04-14T17:05:00",
        "reviewer_name": "Expert 01",
        "verified_dataset": True,
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
    {"id_hanh_vi": 3, "ten_hanh_vi": "udder_swelling", "bounding_box": {"x_center": 0.48, "y_center": 0.56, "w": 0.28, "h": 0.20}, "id_hinh_anh": 3},
    {"id_hanh_vi": 4, "ten_hanh_vi": "limping", "bounding_box": {"x_center": 0.55, "y_center": 0.62, "w": 0.26, "h": 0.24}, "id_hinh_anh": 4},
    {"id_hanh_vi": 5, "ten_hanh_vi": "cow_side_view", "bounding_box": {"x_center": 0.50, "y_center": 0.48, "w": 0.42, "h": 0.36}, "id_hinh_anh": 5},
    {"id_hanh_vi": 6, "ten_hanh_vi": "skin_bump", "bounding_box": {"x_center": 0.43, "y_center": 0.37, "w": 0.14, "h": 0.12}, "id_hinh_anh": 6},
    {"id_hanh_vi": 7, "ten_hanh_vi": "non_cow_object", "bounding_box": {"x_center": 0.52, "y_center": 0.50, "w": 0.60, "h": 0.44}, "id_hinh_anh": 7},
    {"id_hanh_vi": 8, "ten_hanh_vi": "hoof_closeup", "bounding_box": {"x_center": 0.46, "y_center": 0.67, "w": 0.22, "h": 0.18}, "id_hinh_anh": 8},
    {"id_hanh_vi": 9, "ten_hanh_vi": "skin_patch", "bounding_box": {"x_center": 0.58, "y_center": 0.40, "w": 0.18, "h": 0.14}, "id_hinh_anh": 9},
    {"id_hanh_vi": 10, "ten_hanh_vi": "cow_face", "bounding_box": {"x_center": 0.51, "y_center": 0.33, "w": 0.24, "h": 0.20}, "id_hinh_anh": 10},
    {"id_hanh_vi": 11, "ten_hanh_vi": "ear_closeup", "bounding_box": {"x_center": 0.64, "y_center": 0.22, "w": 0.16, "h": 0.16}, "id_hinh_anh": 11},
    {"id_hanh_vi": 12, "ten_hanh_vi": "skin_redness", "bounding_box": {"x_center": 0.41, "y_center": 0.45, "w": 0.20, "h": 0.16}, "id_hinh_anh": 12},
]

_KD_SEED = [
    {
        "id_lich_su": 1,
        "thoi_gian_duyet": "2026-04-09T16:00:00",
        "id_user": 2,
        "id_hinh_anh": 2,
        "action": "approve",
        "to_status": STATUS_CLEANED_DATA,
    },
    {"id_lich_su": 2, "thoi_gian_duyet": "2026-04-11T09:15:00", "id_user": 1, "id_hinh_anh": 3, "action": "ai_scan", "to_status": STATUS_AI_SCANNED},
    {"id_lich_su": 3, "thoi_gian_duyet": "2026-04-11T11:30:00", "id_user": 3, "id_hinh_anh": 4, "action": "link_case", "to_status": STATUS_NEEDS_VERIFICATION},
    {"id_lich_su": 4, "thoi_gian_duyet": "2026-04-12T08:10:00", "id_user": 4, "id_hinh_anh": 5, "action": "request_more_data", "to_status": STATUS_WAITING_MORE_DATA, "reason": "Cần ảnh rõ hơn."},
    {"id_lich_su": 5, "thoi_gian_duyet": "2026-04-12T11:30:00", "id_user": 2, "id_hinh_anh": 6, "action": "approve", "to_status": STATUS_VERIFIED_DATASET, "reason": "Đủ điều kiện đưa vào tập xác nhận."},
    {"id_lich_su": 6, "thoi_gian_duyet": "2026-04-12T14:00:00", "id_user": 3, "id_hinh_anh": 7, "action": "reject", "to_status": STATUS_REJECTED, "reason": "Ảnh không hợp lệ."},
    {"id_lich_su": 7, "thoi_gian_duyet": "2026-04-13T09:50:00", "id_user": 3, "id_hinh_anh": 9, "action": "ai_scan", "to_status": STATUS_AI_SCANNED},
    {"id_lich_su": 8, "thoi_gian_duyet": "2026-04-14T08:15:00", "id_user": 2, "id_hinh_anh": 11, "action": "request_more_data", "to_status": STATUS_WAITING_MORE_DATA, "reason": "Bổ sung ảnh tai trái."},
    {"id_lich_su": 9, "thoi_gian_duyet": "2026-04-14T17:05:00", "id_user": 1, "id_hinh_anh": 12, "action": "approve", "to_status": STATUS_VERIFIED_DATASET, "reason": "Đã xác nhận nhẹ."},
]


def _now_iso() -> str:
    return datetime.now().isoformat()


def _normalize_status(status: str | None) -> str:
    if status == STATUS_CLEANED_DATA:
        return STATUS_VERIFIED_DATASET
    return status or STATUS_PENDING_REVIEW


def _image_defaults(record: dict) -> dict:
    image = dict(record)
    image["trang_thai"] = _normalize_status(image.get("trang_thai"))
    image.setdefault("source_type", "image")
    image.setdefault("file_name", image.get("duong_dan", "").replace("\\", "/").split("/")[-1] or "dataset-image")
    image.setdefault("linked_case_id", None)
    image.setdefault("linked_case_summary", "")
    image.setdefault("ai_result", None)
    image.setdefault("ai_primary_label", "")
    image.setdefault("ai_confidence", 0.0)
    image.setdefault("ai_summary", "")
    image.setdefault("ai_model_name", "")
    image.setdefault("last_ai_scan_at", "")
    image.setdefault("expert_label", "")
    image.setdefault("expert_decision", "")
    image.setdefault("symptom_notes", "")
    image.setdefault("request_more_reason", "")
    image.setdefault("reject_reason", "")
    image.setdefault("review_note", "")
    image.setdefault("reviewed_by", None)
    image.setdefault("reviewed_at", "")
    image.setdefault("reviewer_name", "")
    image.setdefault("verified_dataset", image["trang_thai"] in APPROVED_STATUSES)
    image.setdefault("priority", "normal")
    return image


def init_seed():
    _img_repo.seed(_IMG_SEED)
    _hv_repo.seed(_HV_SEED)
    _kd_repo.seed(_KD_SEED)


def get_all_images() -> list[dict]:
    return [_image_defaults(row) for row in _img_repo.all()]


def get_image_by_id(id_hinh_anh: int) -> dict | None:
    row = _img_repo.find_by_id(id_hinh_anh)
    return _image_defaults(row) if row else None


def get_images_by_status(trang_thai: str) -> list[dict]:
    normalized = _normalize_status(trang_thai)
    return [item for item in get_all_images() if item.get("trang_thai") == normalized]


def get_images_pending() -> list[dict]:
    return [item for item in get_all_images() if item.get("trang_thai") in ACTIVE_STATUSES]


def get_images_by_case(case_id: int) -> list[dict]:
    return [item for item in get_all_images() if item.get("linked_case_id") == case_id]


def add_image(duong_dan: str, id_user: int, trang_thai: str = STATUS_PENDING_REVIEW) -> dict:
    created = _img_repo.insert(
        {
            "duong_dan": duong_dan,
            "trang_thai": _normalize_status(trang_thai),
            "id_user": id_user,
            "created_at": _now_iso(),
        }
    )
    return _image_defaults(created)


def update_image(id_hinh_anh: int, updates: dict) -> dict | None:
    payload = dict(updates)
    if "trang_thai" in payload:
        payload["trang_thai"] = _normalize_status(payload["trang_thai"])
    updated = _img_repo.update(id_hinh_anh, payload)
    return _image_defaults(updated) if updated else None


def update_image_status(id_hinh_anh: int, trang_thai: str) -> dict | None:
    return update_image(id_hinh_anh, {"trang_thai": trang_thai})


def save_ai_review(id_hinh_anh: int, ai_result: dict, reviewer_hint: str = "") -> dict | None:
    diagnosis = ai_result.get("diagnosis", {})
    detected = diagnosis.get("detected", [])
    primary = detected[0] if detected else {}
    summary = ", ".join(
        f"{item.get('class', 'unknown')} {float(item.get('confidence', 0)):.0%}" for item in detected[:3]
    )
    return update_image(
        id_hinh_anh,
        {
            "trang_thai": STATUS_AI_SCANNED if detected else STATUS_NEEDS_VERIFICATION,
            "ai_result": ai_result,
            "ai_primary_label": primary.get("class", ""),
            "ai_confidence": float(primary.get("confidence", 0) or 0),
            "ai_summary": summary or "No disease detected",
            "ai_model_name": ai_result.get("model_name", ""),
            "last_ai_scan_at": _now_iso(),
            "review_note": reviewer_hint or "",
        },
    )


def set_expert_review(
    id_hinh_anh: int,
    *,
    status: str,
    reviewer_id: int,
    reviewer_name: str = "",
    expert_label: str = "",
    symptom_notes: str = "",
    review_note: str = "",
    request_more_reason: str = "",
    reject_reason: str = "",
    verified_dataset: bool | None = None,
) -> dict | None:
    normalized_status = _normalize_status(status)
    is_verified = normalized_status in APPROVED_STATUSES if verified_dataset is None else verified_dataset
    return update_image(
        id_hinh_anh,
        {
            "trang_thai": normalized_status,
            "reviewed_by": reviewer_id,
            "reviewed_at": _now_iso(),
            "reviewer_name": reviewer_name,
            "expert_label": expert_label,
            "expert_decision": normalized_status,
            "symptom_notes": symptom_notes,
            "review_note": review_note,
            "request_more_reason": request_more_reason,
            "reject_reason": reject_reason,
            "verified_dataset": is_verified,
        },
    )


def link_image_case(id_hinh_anh: int, case_id: int | None, case_summary: str = "") -> dict | None:
    return update_image(
        id_hinh_anh,
        {
            "linked_case_id": case_id,
            "linked_case_summary": case_summary,
        },
    )


def get_behaviors_by_image(id_hinh_anh: int) -> list[dict]:
    return _hv_repo.find_many(id_hinh_anh=id_hinh_anh)


def add_behavior(ten_hanh_vi: str, bounding_box: dict, id_hinh_anh: int) -> dict:
    return _hv_repo.insert(
        {
            "ten_hanh_vi": ten_hanh_vi,
            "bounding_box": bounding_box,
            "id_hinh_anh": id_hinh_anh,
        }
    )


def get_review_history(id_user: int | None = None, id_hinh_anh: int | None = None) -> list[dict]:
    history = _kd_repo.all()
    if id_user is not None:
        history = [item for item in history if item.get("id_user") == id_user]
    if id_hinh_anh is not None:
        history = [item for item in history if item.get("id_hinh_anh") == id_hinh_anh]
    return history


def log_review(
    id_user: int,
    id_hinh_anh: int,
    *,
    action: str = "review",
    to_status: str = "",
    reason: str = "",
    metadata: dict | None = None,
) -> dict:
    return _kd_repo.insert(
        {
            "thoi_gian_duyet": _now_iso(),
            "id_user": id_user,
            "id_hinh_anh": id_hinh_anh,
            "action": action,
            "to_status": _normalize_status(to_status) if to_status else "",
            "reason": reason,
            "metadata": metadata or {},
        }
    )
