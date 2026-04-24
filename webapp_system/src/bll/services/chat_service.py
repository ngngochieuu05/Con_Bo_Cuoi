"""
In-memory case service for farmer <-> expert consultation.
"""
from __future__ import annotations

import datetime
import itertools

_id_counter = itertools.count(1)
_store: list[dict] = []
_seeded_experts: set[int] = set()
_severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_status_order = {
    "new": 0,
    "claimed": 1,
    "under_review": 2,
    "waiting_farmer": 3,
    "escalated": 4,
    "closed": 5,
}


def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M")


def _now_iso() -> str:
    return datetime.datetime.now().isoformat()


def _future_iso(minutes: int) -> str:
    return (datetime.datetime.now() + datetime.timedelta(minutes=minutes)).isoformat()


def _days_ago_iso(days: int, hour: int = 9, minute: int = 0) -> str:
    dt = datetime.datetime.now() - datetime.timedelta(days=days)
    return dt.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()


def _parse_iso(iso_str: str) -> datetime.datetime | None:
    if not iso_str:
        return None
    try:
        return datetime.datetime.fromisoformat(iso_str[:19])
    except Exception:
        return None


def _sort_ts(iso_str: str) -> float:
    dt = _parse_iso(iso_str)
    return dt.timestamp() if dt else 0.0


def _past_days(count: int) -> list[datetime.date]:
    today = datetime.date.today()
    return [today - datetime.timedelta(days=offset) for offset in reversed(range(count))]


def _ensure_case_defaults(convo: dict) -> dict:
    convo.setdefault("created_at", _now_iso())
    convo.setdefault("status", "new")
    convo.setdefault("severity", "medium")
    convo.setdefault("case_type", "health-check")
    convo.setdefault("farm_name", "Unassigned farm")
    convo.setdefault("cow_id", "Unassigned cow")
    convo.setdefault("summary", "Case summary is empty.")
    convo.setdefault("claimed_by", None)
    convo.setdefault("owner_name", "")
    convo.setdefault("sla_due_at", _future_iso(90))
    convo.setdefault("last_message_at", _now_iso())
    convo.setdefault("internal_notes", [])
    convo.setdefault("final_conclusion", "")
    convo.setdefault("waiting_reason", "")
    convo.setdefault("closed_at", "")
    return convo


def get_or_create_conversation(farmer_id: int, farmer_name: str, expert_id: int) -> dict:
    existing = next(
        (item for item in _store if item["farmer_id"] == farmer_id and item["expert_id"] == expert_id),
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
            "farmer_name": "Tran Thi Nong",
            "severity": "high",
            "status": "new",
            "case_type": "Behavior anomaly",
            "farm_name": "Zone A",
            "cow_id": "Cow #12",
            "summary": "Aggressive behavior since morning. Farmer also reports reduced appetite.",
            "sla_minutes": 35,
            "unread": 2,
            "created_days_ago": 0,
            "created_hour": 8,
            "messages": [
                {"sender": "farmer", "text": "My cow is showing unusual behavior.", "time": "08:12"},
                {"sender": "expert", "text": "Describe the symptoms in more detail.", "time": "08:14"},
                {"sender": "farmer", "text": "The cow is limping and eating less than usual since yesterday.", "time": "08:15"},
            ],
        },
        {
            "farmer_id": 102,
            "farmer_name": "Nguyen Van Hung",
            "severity": "medium",
            "status": "waiting_farmer",
            "case_type": "Disease consultation",
            "farm_name": "Zone B",
            "cow_id": "Cow #07",
            "summary": "Suspected foot-and-mouth disease. First response already sent.",
            "sla_minutes": 120,
            "unread": 0,
            "created_days_ago": 2,
            "created_hour": 10,
            "messages": [
                {"sender": "farmer", "text": "I need advice about foot-and-mouth symptoms.", "time": "07:30"},
                {"sender": "expert", "text": "Isolate the cow and monitor fever and intake immediately.", "time": "07:45"},
                {"sender": "farmer", "text": "Thanks, I will do that.", "time": "07:46"},
            ],
            "waiting_reason": "Waiting for more close-up photos.",
        },
        {
            "farmer_id": 103,
            "farmer_name": "Le Thi Mai",
            "severity": "critical",
            "status": "escalated",
            "case_type": "Respiratory",
            "farm_name": "Zone C",
            "cow_id": "Cow #03",
            "summary": "Frequent coughing and nasal discharge. Needs direct assessment.",
            "sla_minutes": 15,
            "unread": 1,
            "created_days_ago": 1,
            "created_hour": 11,
            "messages": [
                {"sender": "farmer", "text": "The cow is coughing heavily and has nasal discharge.", "time": "09:00"},
            ],
        },
        {
            "farmer_id": 104,
            "farmer_name": "Pham Duc An",
            "severity": "medium",
            "status": "claimed",
            "case_type": "Digestive",
            "farm_name": "Zone D",
            "cow_id": "Cow #09",
            "summary": "Loose stool and lower water intake after feed change.",
            "sla_minutes": 90,
            "unread": 0,
            "created_days_ago": 4,
            "created_hour": 9,
            "messages": [
                {"sender": "farmer", "text": "The cow has had digestive issues since yesterday.", "time": "10:20"},
            ],
        },
        {
            "farmer_id": 105,
            "farmer_name": "Hoang Thi Lan",
            "severity": "high",
            "status": "under_review",
            "case_type": "Hoof injury",
            "farm_name": "Zone E",
            "cow_id": "Cow #21",
            "summary": "Swelling near hoof joint, gait worsening through the afternoon.",
            "sla_minutes": 45,
            "unread": 1,
            "created_days_ago": 6,
            "created_hour": 14,
            "messages": [
                {"sender": "farmer", "text": "The cow can barely place weight on one leg.", "time": "14:30"},
            ],
        },
        {
            "farmer_id": 106,
            "farmer_name": "Vu Quang Loc",
            "severity": "low",
            "status": "closed",
            "case_type": "Skin irritation",
            "farm_name": "Zone F",
            "cow_id": "Cow #05",
            "summary": "Mild rash responded after cleaning and ointment guidance.",
            "sla_minutes": 180,
            "unread": 0,
            "created_days_ago": 10,
            "created_hour": 8,
            "closed_days_ago": 8,
            "messages": [
                {"sender": "farmer", "text": "There is a light rash near the neck.", "time": "08:10"},
            ],
        },
        {
            "farmer_id": 107,
            "farmer_name": "Do Thi Huyen",
            "severity": "critical",
            "status": "closed",
            "case_type": "Respiratory",
            "farm_name": "Zone B",
            "cow_id": "Cow #14",
            "summary": "Acute breathing distress was escalated and resolved after intervention.",
            "sla_minutes": 20,
            "unread": 0,
            "created_days_ago": 15,
            "created_hour": 7,
            "closed_days_ago": 14,
            "messages": [
                {"sender": "farmer", "text": "The cow is breathing very fast and looks distressed.", "time": "07:05"},
            ],
        },
        {
            "farmer_id": 108,
            "farmer_name": "Bui Minh Khoa",
            "severity": "medium",
            "status": "closed",
            "case_type": "Fever",
            "farm_name": "Zone G",
            "cow_id": "Cow #17",
            "summary": "Short fever cycle ended after hydration and monitoring.",
            "sla_minutes": 120,
            "unread": 0,
            "created_days_ago": 22,
            "created_hour": 13,
            "closed_days_ago": 21,
            "messages": [
                {"sender": "farmer", "text": "Body temperature was above normal last night.", "time": "13:10"},
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
            waiting_reason=seed.get("waiting_reason", ""),
        )
        convo["created_at"] = _days_ago_iso(seed.get("created_days_ago", 0), seed.get("created_hour", 9))
        convo["last_message_at"] = convo["created_at"]
        if seed.get("closed_days_ago") is not None:
            convo["closed_at"] = _days_ago_iso(seed["closed_days_ago"], 17, 0)
        if not convo["messages"]:
            convo["messages"].extend(
                {
                    "sender": msg["sender"],
                    "text": msg["text"],
                    "img_src": None,
                    "time": msg["time"],
                }
                for msg in seed["messages"]
            )
            convo["unread_expert"] = seed["unread"]
    _seeded_experts.add(expert_id)


def list_conversations_for_expert(expert_id: int) -> list[dict]:
    ensure_demo_data(expert_id)
    convos = [_ensure_case_defaults(item) for item in _store if item["expert_id"] == expert_id]
    return sorted(
        convos,
        key=lambda convo: (
            0 if convo.get("unread_expert", 0) else 1,
            _severity_order.get(convo.get("severity"), 9),
            _status_order.get(convo.get("status"), 9),
            -_sort_ts(convo.get("last_message_at", "")),
        ),
    )


def get_conversation(convo_id: int) -> dict | None:
    convo = next((item for item in _store if item["id"] == convo_id), None)
    return _ensure_case_defaults(convo) if convo else None


def update_case(convo_id: int, **updates) -> dict | None:
    convo = next((item for item in _store if item["id"] == convo_id), None)
    if convo is None:
        return None
    convo.update({key: value for key, value in updates.items() if value is not None})
    if convo.get("claimed_by") and not convo.get("owner_name"):
        convo["owner_name"] = f"Expert #{convo['claimed_by']}"
    if convo.get("status") == "closed" and not convo.get("closed_at"):
        convo["closed_at"] = _now_iso()
    convo["last_message_at"] = _now_iso()
    return convo


def add_internal_note(convo_id: int, text: str, author: str = "expert") -> None:
    convo = next((item for item in _store if item["id"] == convo_id), None)
    if convo is None or not text.strip():
        return
    convo.setdefault("internal_notes", []).append(
        {
            "author": author,
            "text": text.strip(),
            "time": _now(),
        }
    )
    convo["last_message_at"] = _now_iso()


def send_message(
    convo_id: int,
    sender: str,
    text: str | None = None,
    img_src: str | None = None,
) -> None:
    convo = next((item for item in _store if item["id"] == convo_id), None)
    if convo is None:
        return
    convo["messages"].append(
        {
            "sender": sender,
            "text": text,
            "img_src": img_src,
            "time": _now(),
        }
    )
    convo["last_message_at"] = _now_iso()
    if sender == "farmer":
        convo["unread_expert"] = convo.get("unread_expert", 0) + 1
        if convo.get("status") == "waiting_farmer":
            convo["status"] = "under_review"
    elif convo.get("status") == "new":
        convo["status"] = "under_review"


def mark_read_expert(convo_id: int) -> None:
    convo = next((item for item in _store if item["id"] == convo_id), None)
    if convo:
        convo["unread_expert"] = 0


def get_case_overview_series(expert_id: int, period: str = "7d") -> dict:
    ensure_demo_data(expert_id)
    period_days = 30 if period == "30d" else 7
    days = _past_days(period_days)
    buckets = {
        day: {
            "date_key": day.isoformat(),
            "label": day.strftime("%d/%m"),
            "total_cases": 0,
            "severe_cases": 0,
        }
        for day in days
    }
    for case in _store:
        if case.get("expert_id") != expert_id:
            continue
        created_at = _parse_iso(case.get("created_at") or case.get("last_message_at", ""))
        if created_at is None:
            continue
        day = created_at.date()
        if day not in buckets:
            continue
        buckets[day]["total_cases"] += 1
        if case.get("severity") in ("high", "critical"):
            buckets[day]["severe_cases"] += 1
    items = list(buckets.values())
    total_cases = sum(item["total_cases"] for item in items)
    severe_cases = sum(item["severe_cases"] for item in items)
    return {
        "period": "30d" if period == "30d" else "7d",
        "days": items,
        "summary": {
            "total_cases": total_cases,
            "severe_cases": severe_cases,
            "severe_ratio": (severe_cases / total_cases) if total_cases else 0.0,
        },
    }
