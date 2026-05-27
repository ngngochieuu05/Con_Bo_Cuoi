from __future__ import annotations

import datetime

from bll.services import local_chat_store

# conversation = {
#   "id": int,
#   "farmer_id": int,
#   "farmer_name": str,
#   "expert_id": int,
#   "messages": list[dict],   # {"sender","text","img_src","img_b64","time"}
#   "unread_expert": int,
# }
_store: list[dict] = local_chat_store.load_expert_conversations()


def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M")


def get_or_create_conversation(
    farmer_id: int,
    farmer_name: str,
    expert_id: int,
) -> dict:
    refresh_store()
    existing = next(
        (
            c for c in _store
            if c["farmer_id"] == farmer_id and c["expert_id"] == expert_id
        ),
        None,
    )
    if existing:
        return existing
    convo = local_chat_store.create_expert_conversation(farmer_id, farmer_name, expert_id)
    _store.append(convo)
    return convo


def list_conversations_for_expert(expert_id: int) -> list[dict]:
    refresh_store()
    return [c for c in _store if c["expert_id"] == expert_id]


def refresh_store() -> list[dict]:
    global _store
    _store = local_chat_store.load_expert_conversations()
    return _store


def get_conversation_by_id(convo_id: int) -> dict | None:
    refresh_store()
    return next((c for c in _store if c["id"] == convo_id), None)


def get_conversation_pair(farmer_id: int, expert_id: int) -> dict | None:
    refresh_store()
    return next(
        (c for c in _store if c["farmer_id"] == farmer_id and c["expert_id"] == expert_id),
        None,
    )


def send_message(
    convo_id: int,
    sender: str,
    text: str | None = None,
    img_src: str | None = None,
    img_b64: str | None = None,
    time_text: str | None = None,
) -> None:
    refresh_store()
    convo = next((c for c in _store if c["id"] == convo_id), None)
    if convo is None:
        return
    time_text = time_text or _now()
    img_src, img_b64 = local_chat_store.resolve_message_image(
        img_src=img_src,
        img_b64=img_b64,
    )
    message = {
        "sender": sender,
        "text": text,
        "img_src": img_src,
        "img_b64": img_b64,
        "time": time_text,
    }
    convo["messages"].append(message)
    local_chat_store.update_expert_typing(convo_id, sender, False)
    convo[f"typing_{sender}_at"] = ""
    if sender == "farmer":
        convo["unread_expert"] = convo.get("unread_expert", 0) + 1
        local_chat_store.update_expert_unread(convo_id, convo["unread_expert"])
    else:
        local_chat_store.update_expert_unread(convo_id, convo.get("unread_expert", 0))
    local_chat_store.save_expert_message(
        convo_id=convo_id,
        sender=sender,
        text=text,
        img_src=img_src,
        img_b64=img_b64,
        time_text=time_text,
    )


def mark_read_expert(convo_id: int) -> None:
    refresh_store()
    convo = next((c for c in _store if c["id"] == convo_id), None)
    if convo:
        convo["unread_expert"] = 0
        local_chat_store.update_expert_unread(convo_id, 0)


def set_typing(convo_id: int, sender: str, is_typing: bool) -> None:
    local_chat_store.update_expert_typing(convo_id, sender, is_typing)
    convo = get_conversation_by_id(convo_id)
    if convo is not None:
        convo[f"typing_{sender}_at"] = datetime.datetime.now().isoformat() if is_typing else ""


def is_typing_active(convo: dict | None, sender: str, timeout_seconds: int = 5) -> bool:
    if not convo:
        return False
    raw = str(convo.get(f"typing_{sender}_at") or "").strip()
    if not raw:
        return False
    try:
        started = datetime.datetime.fromisoformat(raw[:19])
    except Exception:
        return False
    return (datetime.datetime.now() - started).total_seconds() <= timeout_seconds
