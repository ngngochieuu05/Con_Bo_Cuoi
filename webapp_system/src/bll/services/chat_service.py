"""
Chat Service — Luồng tư vấn Farmer ↔ Expert.
Dùng module-level in-memory store (phù hợp single-process Flet desktop).
"""
from __future__ import annotations
import datetime
import itertools

_id_counter = itertools.count(1)

# _store: list[dict conversation]
# conversation = {
#   "id": int,
#   "farmer_id": int,
#   "farmer_name": str,
#   "expert_id": int,
#   "messages": list[dict],   # {"sender":"farmer"|"expert","text":str|None,"img_src":str|None,"time":str}
#   "unread_expert": int,     # tin chưa đọc chờ expert
# }
_store: list[dict] = []


def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M")


def get_or_create_conversation(farmer_id: int, farmer_name: str,
                                expert_id: int) -> dict:
    """Tìm hoặc tạo mới hội thoại giữa farmer và expert."""
    existing = next(
        (c for c in _store
         if c["farmer_id"] == farmer_id and c["expert_id"] == expert_id),
        None,
    )
    if existing:
        return existing
    convo = {
        "id": next(_id_counter),
        "farmer_id": farmer_id,
        "farmer_name": farmer_name,
        "expert_id": expert_id,
        "messages": [],
        "unread_expert": 0,
    }
    _store.append(convo)
    return convo


def list_conversations_for_expert(expert_id: int) -> list[dict]:
    """Lấy tất cả hội thoại gửi đến expert (kể cả không có tin)."""
    return [c for c in _store if c["expert_id"] == expert_id]


def send_message(convo_id: int, sender: str,
                 text: str | None = None,
                 img_src: str | None = None) -> None:
    """Thêm tin nhắn vào hội thoại. sender = 'farmer' hoặc 'expert'."""
    convo = next((c for c in _store if c["id"] == convo_id), None)
    if convo is None:
        return
    convo["messages"].append({
        "sender": sender,
        "text": text,
        "img_src": img_src,
        "time": _now(),
    })
    if sender == "farmer":
        convo["unread_expert"] = convo.get("unread_expert", 0) + 1


def mark_read_expert(convo_id: int) -> None:
    """Expert đã đọc → reset unread."""
    convo = next((c for c in _store if c["id"] == convo_id), None)
    if convo:
        convo["unread_expert"] = 0
