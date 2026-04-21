"""
Chat Service — luồng tư vấn Farmer ↔ Expert.
Store in-memory cho single-process Flet desktop/web local mode.
"""
from __future__ import annotations

import datetime
import itertools

_id_counter = itertools.count(1)
_store: list[dict] = []
_seeded_experts: set[int] = set()
_severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_status_order = {"new": 0, "claimed": 1, "under_review": 2, "waiting_farmer": 3, "escalated": 4, "closed": 5}


def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M")


def _now_iso() -> str:
    return datetime.datetime.now().isoformat()


def _future_iso(minutes: int) -> str:
    return (datetime.datetime.now() + datetime.timedelta(minutes=minutes)).isoformat()


def _sort_ts(iso_str: str) -> float:
    try:
        return datetime.datetime.fromisoformat(iso_str[:19]).timestamp()
    except Exception:
        return 0.0


def _ensure_case_defaults(convo: dict) -> dict:
    convo.setdefault("status", "new")
    convo.setdefault("severity", "medium")
    convo.setdefault("case_type", "health-check")
    convo.setdefault("farm_name", "Trang trại chưa gán")
    convo.setdefault("cow_id", "Bò chưa gán")
    convo.setdefault("summary", "Chưa có tóm tắt ca.")
    convo.setdefault("claimed_by", None)
    convo.setdefault("sla_due_at", _future_iso(90))
    convo.setdefault("last_message_at", _now_iso())
    convo.setdefault("internal_notes", [])
    return convo


def get_or_create_conversation(farmer_id: int, farmer_name: str, expert_id: int) -> dict:
    existing = next(
        (c for c in _store if c["farmer_id"] == farmer_id and c["expert_id"] == expert_id),
        None,
    )
    if existing:
        return _ensure_case_defaults(existing)
    convo = {
        "id": next(_id_counter),
        "farmer_id": farmer_id,
        "farmer_name": farmer_name,
        "expert_id": expert_id,
        "messages": [],
        "unread_expert": 0,
    }
    _ensure_case_defaults(convo)
    _store.append(convo)
    return convo


def ensure_demo_data(expert_id: int) -> None:
    if expert_id <= 0 or expert_id in _seeded_experts:
        return
    seeds = [
        {
            "farmer_id": 101,
            "farmer_name": "Trần Thị Nông",
            "severity": "high",
            "status": "new",
            "case_type": "Bất thường hành vi",
            "farm_name": "Khu A",
            "cow_id": "Bò #12",
            "summary": "Hung hăng bất thường từ sáng. Farmer báo giảm ăn.",
            "sla_minutes": 35,
            "unread": 2,
            "messages": [
                {"sender": "farmer", "text": "Chào chuyên gia! Con bò của tôi đang có dấu hiệu bất thường.", "time": "08:12"},
                {"sender": "expert", "text": "Bạn mô tả thêm triệu chứng giúp tôi.", "time": "08:14"},
                {"sender": "farmer", "text": "Con bò bị sưng chân và ăn ít hơn bình thường từ hôm qua.", "time": "08:15"},
            ],
        },
        {
            "farmer_id": 102,
            "farmer_name": "Nguyễn Văn Hùng",
            "severity": "medium",
            "status": "waiting_farmer",
            "case_type": "Tư vấn bệnh",
            "farm_name": "Khu B",
            "cow_id": "Bò #07",
            "summary": "Nghi bệnh lở mồm long móng. Đã phản hồi bước đầu.",
            "sla_minutes": 120,
            "unread": 0,
            "messages": [
                {"sender": "farmer", "text": "Cho tôi hỏi về bệnh lở mồm long móng ạ.", "time": "07:30"},
                {"sender": "expert", "text": "Cần cách ly ngay và theo dõi sốt, ăn uống.", "time": "07:45"},
                {"sender": "farmer", "text": "Cảm ơn chuyên gia nhiều!", "time": "07:46"},
            ],
        },
        {
            "farmer_id": 103,
            "farmer_name": "Lê Thị Mai",
            "severity": "critical",
            "status": "escalated",
            "case_type": "Hô hấp",
            "farm_name": "Khu C",
            "cow_id": "Bò #03",
            "summary": "Ho nhiều, chảy nước mũi, cần đánh giá trực tiếp.",
            "sla_minutes": 15,
            "unread": 1,
            "messages": [
                {"sender": "farmer", "text": "Bò nhà tôi ho nhiều và chảy nước mũi.", "time": "09:00"},
            ],
        },
    ]
    for seed in seeds:
        convo = get_or_create_conversation(seed["farmer_id"], seed["farmer_name"], expert_id)
        update_case(
            convo["id"],
            severity=seed["severity"],
            status=seed["status"],
            case_type=seed["case_type"],
            farm_name=seed["farm_name"],
            cow_id=seed["cow_id"],
            summary=seed["summary"],
            sla_due_at=_future_iso(seed["sla_minutes"]),
        )
        if not convo["messages"]:
            convo["messages"].extend({
                "sender": msg["sender"],
                "text": msg["text"],
                "img_src": None,
                "time": msg["time"],
            } for msg in seed["messages"])
            convo["unread_expert"] = seed["unread"]
    _seeded_experts.add(expert_id)


def list_conversations_for_expert(expert_id: int) -> list[dict]:
    ensure_demo_data(expert_id)
    convos = [_ensure_case_defaults(c) for c in _store if c["expert_id"] == expert_id]
    return sorted(
        convos,
        key=lambda convo: (
            0 if convo.get("unread_expert", 0) else 1,
            _severity_order.get(convo.get("severity"), 9),
            _status_order.get(convo.get("status"), 9),
            -_sort_ts(convo.get("last_message_at", "")),
        ),
    )


def update_case(convo_id: int, **updates) -> dict | None:
    convo = next((c for c in _store if c["id"] == convo_id), None)
    if convo is None:
        return None
    convo.update({key: value for key, value in updates.items() if value is not None})
    convo["last_message_at"] = _now_iso()
    return convo


def add_internal_note(convo_id: int, text: str, author: str = "expert") -> None:
    convo = next((c for c in _store if c["id"] == convo_id), None)
    if convo is None or not text.strip():
        return
    convo.setdefault("internal_notes", []).append({
        "author": author,
        "text": text.strip(),
        "time": _now(),
    })
    convo["last_message_at"] = _now_iso()


def send_message(
    convo_id: int,
    sender: str,
    text: str | None = None,
    img_src: str | None = None,
) -> None:
    convo = next((c for c in _store if c["id"] == convo_id), None)
    if convo is None:
        return
    convo["messages"].append({
        "sender": sender,
        "text": text,
        "img_src": img_src,
        "time": _now(),
    })
    convo["last_message_at"] = _now_iso()
    if sender == "farmer":
        convo["unread_expert"] = convo.get("unread_expert", 0) + 1
        if convo.get("status") == "waiting_farmer":
            convo["status"] = "under_review"
    elif convo.get("status") == "new":
        convo["status"] = "under_review"


def mark_read_expert(convo_id: int) -> None:
    convo = next((c for c in _store if c["id"] == convo_id), None)
    if convo:
        convo["unread_expert"] = 0
