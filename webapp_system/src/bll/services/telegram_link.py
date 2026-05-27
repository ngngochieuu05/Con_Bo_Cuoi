"""
BLL — Telegram Link Service
Luồng liên kết tài khoản app với Telegram bằng one-time token.

Luồng:
  1. Farmer nhấn "Liên kết Telegram" / đăng ký → UI gọi get_deep_link(username)
  2. UI hiển thị deep-link: https://t.me/Cattle_Farm_Bot?start=<token>
  3. Farmer click link → Telegram mở → Bot nhận /start <token>
  4. telegram_bot._handle_link_token() → validate_token() → bind_telegram()
  5. Bot reply "Liên kết thành công"

Lưu trữ: bảng `telegram_tokens` trong PostgreSQL (json_store).
Schema: {"tokens": {"<uuid>": {"username": ..., "created_at": ..., "expires_at": ...}}}
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta

from bll.services.monitor_service import load_config

TOKEN_TTL_HR = 24   # Token hết hạn sau 24 giờ
_lock        = threading.Lock()
_TABLE       = "telegram_tokens"


# ──────────────────────────────────────────────────────────────────
# DB I/O (dùng BaseRepo → json_store trong PostgreSQL)
# ──────────────────────────────────────────────────────────────────

def _load_tokens() -> dict:
    """Đọc dict tokens từ record đặc biệt id=1 trong bảng telegram_tokens."""
    from dal.base_repo import BaseRepo
    repo = BaseRepo(_TABLE, pk_field="id")
    rec  = repo.find_by_id(1)
    if rec is None:
        return {"tokens": {}}
    return {"tokens": rec.get("tokens", {})}


def _save_tokens(data: dict) -> None:
    """Ghi dict tokens vào record id=1."""
    from dal.base_repo import BaseRepo
    repo    = BaseRepo(_TABLE, pk_field="id")
    payload = {"id": 1, "tokens": data["tokens"]}
    if repo.find_by_id(1) is None:
        repo.insert(payload)
    else:
        repo.update(1, {"tokens": data["tokens"]})


# ──────────────────────────────────────────────────────────────────
# Token management
# ──────────────────────────────────────────────────────────────────

def generate_token(username: str) -> str:
    """
    Tạo one-time token UUID cho user để liên kết Telegram.
    Xóa token cũ của user + hết hạn trước khi tạo mới.
    """
    with _lock:
        data = _load_tokens()
        now  = datetime.now()
        # Xóa token cũ của user + token hết hạn
        data["tokens"] = {
            t: info
            for t, info in data["tokens"].items()
            if info.get("username") != username
            and datetime.fromisoformat(info["expires_at"]) > now
        }
        token = str(uuid.uuid4())
        data["tokens"][token] = {
            "username":   username,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=TOKEN_TTL_HR)).isoformat(),
        }
        _save_tokens(data)
        return token


def validate_token(token: str) -> str | None:
    """
    Validate one-time token.
    Trả về username nếu hợp lệ; None nếu không tìm thấy / hết hạn.
    Token bị XÓA ngay sau khi validate (one-time use).
    """
    with _lock:
        data = _load_tokens()
        if token not in data["tokens"]:
            return None

        info       = data["tokens"][token]
        expires_at = datetime.fromisoformat(info["expires_at"])

        if datetime.now() > expires_at:
            del data["tokens"][token]
            _save_tokens(data)
            return None

        username = info.get("username")
        del data["tokens"][token]   # ONE-TIME: xóa sau khi dùng
        _save_tokens(data)
        return username


def bind_telegram(username: str, chat_id: str, tg_username: str = "") -> bool:
    """
    Ghi telegram_chat_id vào record tài khoản.
    Trả về True nếu liên kết thành công.
    Trả về False nếu user không tồn tại hoặc đã liên kết rồi.
    Dùng rebind_telegram() nếu muốn cập nhật lại.
    """
    from dal.tai_khoan_repo import get_user_by_username, update_user
    user = get_user_by_username(username)
    if not user:
        return False
    if user.get("telegram_chat_id"):   # Đã liên kết rồi
        return False

    update_user(user["id_user"], {
        "telegram_chat_id":    chat_id,
        "telegram_username":   tg_username,
        "telegram_linked_at":  datetime.now().isoformat(),
    })
    return True


def rebind_telegram(username: str, chat_id: str, tg_username: str = "") -> bool:
    """Cập nhật lại liên kết Telegram (kể cả khi đã liên kết trước đó)."""
    from dal.tai_khoan_repo import get_user_by_username, update_user
    user = get_user_by_username(username)
    if not user:
        return False
    update_user(user["id_user"], {
        "telegram_chat_id":    chat_id,
        "telegram_username":   tg_username,
        "telegram_linked_at":  datetime.now().isoformat(),
    })
    return True


def unbind_telegram(username: str) -> bool:
    """Xoá liên kết Telegram của user."""
    from dal.tai_khoan_repo import get_user_by_username, update_user
    user = get_user_by_username(username)
    if not user:
        return False
    update_user(user["id_user"], {
        "telegram_chat_id":   "",
        "telegram_username":  "",
        "telegram_linked_at": "",
    })
    return True


def get_deep_link(username: str, bot_name: str = "") -> str:
    """
    Tạo deep-link Telegram kèm one-time token.
    bot_name đọc từ cấu hình hệ thống nếu không truyền.
    UI hiển thị link này cho farmer click.
    """
    if not bot_name:
        try:
            bot_name = (load_config().get("telegram") or {}).get("bot_name", "Cattle_Farm_Bot")
        except Exception:
            bot_name = "Cattle_Farm_Bot"
    token = generate_token(username)
    return f"https://t.me/{bot_name}?start={token}"


# ──────────────────────────────────────────────────────────────────
# Token management
# ──────────────────────────────────────────────────────────────────

def generate_token(username: str) -> str:
    """
    Tạo one-time token UUID cho user để liên kết Telegram.
    Xóa token cũ của user trước khi tạo mới.
    Returns: token string
    """
    with _lock:
        data = _load_tokens()
        # Xóa token cũ của user này + các token hết hạn
        now = datetime.now()
        data["tokens"] = {
            t: info
            for t, info in data["tokens"].items()
            if info.get("username") != username
            and datetime.strptime(info["expires_at"], "%Y-%m-%d %H:%M:%S") > now
        }
        token = str(uuid.uuid4())
        data["tokens"][token] = {
            "username":   username,
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at": (now + timedelta(hours=TOKEN_TTL_HR)).strftime("%Y-%m-%d %H:%M:%S"),
        }
        _save_tokens(data)
        return token


def validate_token(token: str) -> str | None:
    """
    Validate one-time token.
    Trả về username nếu hợp lệ; None nếu không tìm thấy / hết hạn.
    Token bị XÓA ngay sau khi validate (one-time use).
    """
    with _lock:
        data = _load_tokens()
        if token not in data["tokens"]:
            return None

        info       = data["tokens"][token]
        expires_at = datetime.strptime(info["expires_at"], "%Y-%m-%d %H:%M:%S")

        if datetime.now() > expires_at:
            del data["tokens"][token]
            _save_tokens(data)
            return None

        username = info.get("username")
        del data["tokens"][token]   # ONE-TIME: xóa sau khi dùng
        _save_tokens(data)
        return username


def bind_telegram(username: str, chat_id: str, tg_username: str = "") -> bool:
    """
    Ghi telegram_chat_id vào record tài khoản.
    Trả về True nếu liên kết thành công.
    Trả về False nếu user không tồn tại hoặc đã liên kết rồi (per oa.md spec).
    Dùng rebind_telegram() nếu muốn cập nhật lại.
    """
    from dal.tai_khoan_repo import get_user_by_username, update_user
    user = get_user_by_username(username)
    if not user:
        return False
    if user.get("telegram_chat_id"):   # ← guard per oa.md: Đã liên kết rồi
        return False

    update_user(user["id_user"], {
        "telegram_chat_id":    chat_id,
        "telegram_username":   tg_username,
        "telegram_linked_at":  datetime.now().isoformat(),
    })
    return True


def rebind_telegram(username: str, chat_id: str, tg_username: str = "") -> bool:
    """Cập nhật lại liên kết Telegram (kể cả khi đã liên kết trước đó)."""
    from dal.tai_khoan_repo import get_user_by_username, update_user
    user = get_user_by_username(username)
    if not user:
        return False
    update_user(user["id_user"], {
        "telegram_chat_id":    chat_id,
        "telegram_username":   tg_username,
        "telegram_linked_at":  datetime.now().isoformat(),
    })
    return True


def unbind_telegram(username: str) -> bool:
    """Xoá liên kết Telegram của user."""
    from dal.tai_khoan_repo import get_user_by_username, update_user
    user = get_user_by_username(username)
    if not user:
        return False
    update_user(user["id_user"], {
        "telegram_chat_id":   "",
        "telegram_username":  "",
        "telegram_linked_at": "",
    })
    return True


def get_deep_link(username: str, bot_name: str = "") -> str:
    """
    Tạo deep-link Telegram kèm one-time token.
    bot_name đọc từ cấu hình hệ thống nếu không truyền.
    UI hiển thị link này cho farmer click.
    """
    if not bot_name:
        try:
            bot_name = (load_config().get("telegram") or {}).get("bot_name", "Cattle_Farm_Bot")
        except Exception:
            bot_name = "Cattle_Farm_Bot"
    token = generate_token(username)
    return f"https://t.me/{bot_name}?start={token}"
