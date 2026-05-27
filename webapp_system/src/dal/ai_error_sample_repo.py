from __future__ import annotations

from datetime import datetime

from dal.base_repo import BaseRepo

_repo = BaseRepo("ai_error_samples", pk_field="id_error_sample")


def get_all_error_samples() -> list[dict]:
    rows = _repo.all()
    return sorted(rows, key=lambda x: x.get("created_at", ""), reverse=True)


def get_error_sample_by_id(id_error_sample: int) -> dict | None:
    return _repo.find_by_id(id_error_sample)


def get_error_samples_by_status(status: str) -> list[dict]:
    rows = _repo.find_many(status=status)
    return sorted(rows, key=lambda x: x.get("created_at", ""), reverse=True)


def create_error_sample(
    *,
    image_path: str = "",
    image_b64: str = "",
    source_type: str = "farmer_ai",
    farmer_id: int | None = None,
    farmer_name: str = "",
    model_name: str = "",
    model_type: str = "",
    predicted_label: str = "",
    confidence: float | None = None,
    note: str = "",
    ai_result: dict | None = None,
) -> dict:
    now = datetime.now().isoformat()
    return _repo.insert(
        {
            "image_path": image_path,
            "image_b64": image_b64,
            "source_type": source_type,
            "farmer_id": farmer_id,
            "farmer_name": farmer_name,
            "model_name": model_name,
            "model_type": model_type,
            "predicted_label": predicted_label,
            "confidence": confidence,
            "note": note,
            "ai_result": ai_result or {},
            "status": "open",
            "review_comment": "",
            "reviewed_by": None,
            "reviewed_at": "",
            "created_at": now,
            "updated_at": now,
        }
    )


def update_error_sample(id_error_sample: int, updates: dict) -> dict | None:
    updates = dict(updates or {})
    updates["updated_at"] = datetime.now().isoformat()
    return _repo.update(id_error_sample, updates)


def update_error_sample_status(
    id_error_sample: int,
    status: str,
    *,
    reviewed_by: int | None = None,
    review_comment: str = "",
) -> dict | None:
    updates = {
        "status": status,
        "reviewed_by": reviewed_by,
        "reviewed_at": datetime.now().isoformat(),
        "review_comment": review_comment.strip(),
    }
    return update_error_sample(id_error_sample, updates)


def delete_error_sample(id_error_sample: int) -> bool:
    return _repo.delete(id_error_sample)
