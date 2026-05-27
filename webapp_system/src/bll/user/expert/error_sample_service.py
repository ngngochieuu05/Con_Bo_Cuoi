from __future__ import annotations

from dal.ai_error_sample_repo import (
    create_error_sample as repo_create_error_sample,
    delete_error_sample,
    get_all_error_samples,
    get_error_sample_by_id,
    get_error_samples_by_status,
    update_error_sample,
    update_error_sample_status,
)

STATUS_OPEN = "open"
STATUS_REVIEWING = "reviewing"
STATUS_RELABEL = "relabel_needed"
STATUS_RESOLVED = "resolved"

VALID_STATUSES = {STATUS_OPEN, STATUS_REVIEWING, STATUS_RELABEL, STATUS_RESOLVED}


def list_error_samples(status: str | None = None) -> list[dict]:
    if status and status in VALID_STATUSES:
        return get_error_samples_by_status(status)
    return get_all_error_samples()


def get_error_sample_detail(id_error_sample: int) -> dict | None:
    return get_error_sample_by_id(id_error_sample)


def create_error_sample(**payload) -> dict:
    return repo_create_error_sample(**payload)


def mark_error_sample_status(
    id_error_sample: int,
    status: str,
    *,
    expert_id: int | None = None,
    review_comment: str = "",
) -> dict | None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Unsupported status: {status}")
    return update_error_sample_status(
        id_error_sample,
        status,
        reviewed_by=expert_id,
        review_comment=review_comment,
    )


def update_error_sample_note(id_error_sample: int, review_comment: str) -> dict | None:
    return update_error_sample(id_error_sample, {"review_comment": review_comment.strip()})


def remove_error_sample(id_error_sample: int) -> bool:
    return delete_error_sample(id_error_sample)


def get_error_sample_summary() -> dict:
    rows = get_all_error_samples()
    summary = {
        "total": len(rows),
        STATUS_OPEN: 0,
        STATUS_REVIEWING: 0,
        STATUS_RELABEL: 0,
        STATUS_RESOLVED: 0,
    }
    for row in rows:
        key = row.get("status", STATUS_OPEN)
        if key in summary:
            summary[key] += 1
    return summary


def get_expert_review_history(user_id: int) -> list[dict]:
    """Lấy lịch sử kiểm duyệt của chuyên gia."""
    from dal.dataset_repo import get_review_history
    return get_review_history(user_id)
