"""
Expert data review business logic.
"""
from __future__ import annotations

from dal.dataset_repo import (
    ACTIVE_STATUSES,
    APPROVED_STATUSES,
    FINAL_STATUSES,
    STATUS_AI_SCANNED,
    STATUS_NEEDS_VERIFICATION,
    STATUS_PENDING_REVIEW,
    STATUS_REJECTED,
    STATUS_VERIFIED_DATASET,
    STATUS_WAITING_MORE_DATA,
    get_all_images,
    get_behaviors_by_image,
    get_image_by_id,
    get_images_by_case,
    get_images_by_status,
    get_images_pending,
    get_review_history,
    link_image_case,
    log_review,
    save_ai_review,
    set_expert_review,
)


def get_pending_images() -> list[dict]:
    return get_images_pending()


def get_reviewed_images() -> list[dict]:
    return [item for item in get_all_images() if item.get("trang_thai") in FINAL_STATUSES]


def get_all_dataset_images() -> list[dict]:
    return get_all_images()


def get_case_images(case_id: int) -> list[dict]:
    return get_images_by_case(case_id)


def approve_image(
    id_hinh_anh: int,
    id_user: int,
    *,
    reviewer_name: str = "",
    expert_label: str = "",
    symptom_notes: str = "",
    review_note: str = "",
) -> tuple[bool, str]:
    result = set_expert_review(
        id_hinh_anh,
        status=STATUS_VERIFIED_DATASET,
        reviewer_id=id_user,
        reviewer_name=reviewer_name,
        expert_label=expert_label,
        symptom_notes=symptom_notes,
        review_note=review_note,
        verified_dataset=True,
    )
    if result is None:
        return False, f"Image ID={id_hinh_anh} was not found."
    log_review(
        id_user,
        id_hinh_anh,
        action="approve",
        to_status=STATUS_VERIFIED_DATASET,
        reason=review_note,
        metadata={"expert_label": expert_label, "symptom_notes": symptom_notes},
    )
    return True, "Image verified and moved into the expert-approved dataset."


def reject_image(
    id_hinh_anh: int,
    id_user: int,
    *,
    reviewer_name: str = "",
    reject_reason: str = "",
    review_note: str = "",
) -> tuple[bool, str]:
    result = set_expert_review(
        id_hinh_anh,
        status=STATUS_REJECTED,
        reviewer_id=id_user,
        reviewer_name=reviewer_name,
        reject_reason=reject_reason,
        review_note=review_note,
        verified_dataset=False,
    )
    if result is None:
        return False, f"Image ID={id_hinh_anh} was not found."
    log_review(
        id_user,
        id_hinh_anh,
        action="reject",
        to_status=STATUS_REJECTED,
        reason=reject_reason or review_note,
    )
    return True, "Image rejected."


def request_more_data(
    id_hinh_anh: int,
    id_user: int,
    *,
    reviewer_name: str = "",
    request_reason: str = "",
    review_note: str = "",
) -> tuple[bool, str]:
    result = set_expert_review(
        id_hinh_anh,
        status=STATUS_WAITING_MORE_DATA,
        reviewer_id=id_user,
        reviewer_name=reviewer_name,
        request_more_reason=request_reason,
        review_note=review_note,
        verified_dataset=False,
    )
    if result is None:
        return False, f"Image ID={id_hinh_anh} was not found."
    log_review(
        id_user,
        id_hinh_anh,
        action="request_more_data",
        to_status=STATUS_WAITING_MORE_DATA,
        reason=request_reason or review_note,
    )
    return True, "Marked as waiting for more data."


def store_ai_scan(
    id_hinh_anh: int,
    id_user: int,
    ai_result: dict,
    *,
    reviewer_hint: str = "",
) -> tuple[bool, str]:
    result = save_ai_review(id_hinh_anh, ai_result, reviewer_hint=reviewer_hint)
    if result is None:
        return False, f"Image ID={id_hinh_anh} was not found."
    log_review(
        id_user,
        id_hinh_anh,
        action="ai_scan",
        to_status=result.get("trang_thai", STATUS_AI_SCANNED),
        metadata={
            "primary_label": result.get("ai_primary_label", ""),
            "confidence": result.get("ai_confidence", 0),
            "model_name": result.get("ai_model_name", ""),
        },
    )
    return True, "AI scan saved."


def assign_image_to_case(
    id_hinh_anh: int,
    id_user: int,
    *,
    case_id: int | None,
    case_summary: str = "",
) -> tuple[bool, str]:
    result = link_image_case(id_hinh_anh, case_id, case_summary)
    if result is None:
        return False, f"Image ID={id_hinh_anh} was not found."
    log_review(
        id_user,
        id_hinh_anh,
        action="link_case",
        metadata={"case_id": case_id, "case_summary": case_summary},
    )
    return True, "Case link updated."


def get_image_detail(id_hinh_anh: int) -> dict:
    image = get_image_by_id(id_hinh_anh)
    behaviors = get_behaviors_by_image(id_hinh_anh) if image else []
    history = get_review_history(id_hinh_anh=id_hinh_anh) if image else []
    return {"image": image, "behaviors": behaviors, "history": history}


def get_review_summary() -> dict:
    all_images = get_all_images()
    statuses = [item.get("trang_thai") for item in all_images]
    return {
        "total": len(all_images),
        "pending": sum(1 for status in statuses if status in ACTIVE_STATUSES),
        "pending_review": sum(1 for status in statuses if status == STATUS_PENDING_REVIEW),
        "ai_scanned": sum(1 for status in statuses if status == STATUS_AI_SCANNED),
        "needs_verification": sum(1 for status in statuses if status == STATUS_NEEDS_VERIFICATION),
        "waiting_more_data": sum(1 for status in statuses if status == STATUS_WAITING_MORE_DATA),
        "approved": sum(1 for status in statuses if status in APPROVED_STATUSES),
        "rejected": sum(1 for status in statuses if status == STATUS_REJECTED),
    }
