from __future__ import annotations

import base64
import json
import sqlite3
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

_LOCK = threading.RLock()
_CIPHER: Fernet | None = None
_ROOT_DIR = Path(__file__).resolve().parents[3]
_DATA_DIR = _ROOT_DIR / "data"
_DB_PATH = _DATA_DIR / "local_consultations.db"
_KEY_PATH = _DATA_DIR / "local_consultations.key"
_UPLOADS_DIR = _ROOT_DIR.parent / "uploads"


def _ensure_dirs() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _get_cipher() -> Fernet:
    global _CIPHER
    with _LOCK:
        if _CIPHER is not None:
            return _CIPHER
        _ensure_dirs()
        if _KEY_PATH.exists():
            key = _KEY_PATH.read_bytes().strip()
        else:
            key = Fernet.generate_key()
            _KEY_PATH.write_bytes(key)
        _CIPHER = Fernet(key)
        return _CIPHER


def _connect() -> sqlite3.Connection:
    _ensure_dirs()
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _encrypt_text(value: str | None) -> bytes | None:
    if value in (None, ""):
        return None
    return _get_cipher().encrypt(value.encode("utf-8"))


def _decrypt_text(value: bytes | None) -> str | None:
    if not value:
        return None
    return _get_cipher().decrypt(value).decode("utf-8")


def _encrypt_json(value: Any) -> bytes | None:
    if value in (None, "", {}, []):
        return None
    return _encrypt_text(json.dumps(_make_json_safe(value), ensure_ascii=False))


def _decrypt_json(value: bytes | None) -> Any:
    plain = _decrypt_text(value)
    if not plain:
        return None
    return json.loads(plain)


def _make_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    return value


def _normalize_upload_src(src: str) -> Path:
    clean = src.replace("\\", "/")
    if clean.startswith("/uploads/"):
        return _UPLOADS_DIR / clean.removeprefix("/uploads/")
    return Path(src)


def read_image_base64_from_source(src: str | None) -> str | None:
    if not src:
        return None
    try:
        path = _normalize_upload_src(src)
        if not path.exists() or not path.is_file():
            return None
        return base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return None


def resolve_message_image(
    img_src: str | None = None,
    img_b64: str | None = None,
) -> tuple[str | None, str | None]:
    if img_b64:
        return img_src, img_b64
    return img_src, read_image_base64_from_source(img_src)


def init_db() -> None:
    with _LOCK, _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS expert_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farmer_id INTEGER NOT NULL,
                farmer_name TEXT,
                expert_id INTEGER NOT NULL,
                unread_expert INTEGER NOT NULL DEFAULT 0,
                typing_farmer_at TEXT,
                typing_expert_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_expert_conversations_pair
            ON expert_conversations(farmer_id, expert_id);

            CREATE TABLE IF NOT EXISTS expert_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                convo_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                text_enc BLOB,
                img_src_enc BLOB,
                img_b64_enc BLOB,
                time_text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(convo_id) REFERENCES expert_conversations(id)
            );

            CREATE TABLE IF NOT EXISTS ai_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                text_enc BLOB,
                img_src_enc BLOB,
                img_b64_enc BLOB,
                file_name_enc BLOB,
                ai_result_enc BLOB,
                time_text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS local_user_profiles (
                id_user INTEGER PRIMARY KEY,
                profile_enc BLOB,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        for ddl in (
            "ALTER TABLE expert_conversations ADD COLUMN typing_farmer_at TEXT",
            "ALTER TABLE expert_conversations ADD COLUMN typing_expert_at TEXT",
        ):
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                pass
        conn.commit()


def _row_to_message(row: sqlite3.Row) -> dict:
    return {
        "sender": row["sender"],
        "text": _decrypt_text(row["text_enc"]),
        "img_src": _decrypt_text(row["img_src_enc"]),
        "img_b64": _decrypt_text(row["img_b64_enc"]),
        "file_name": _decrypt_text(row["file_name_enc"]) if "file_name_enc" in row.keys() else None,
        "time": row["time_text"] or "",
        "ai_result": _decrypt_json(row["ai_result_enc"]) if "ai_result_enc" in row.keys() else None,
        "created_at": row["created_at"] if "created_at" in row.keys() else None,
    }


def load_expert_conversations() -> list[dict]:
    init_db()
    with _LOCK, _connect() as conn:
        convo_rows = conn.execute(
            """
            SELECT id, farmer_id, farmer_name, expert_id, unread_expert, typing_farmer_at, typing_expert_at
            FROM expert_conversations
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()
        msg_rows = conn.execute(
            """
            SELECT convo_id, sender, text_enc, img_src_enc, img_b64_enc, time_text
            FROM expert_messages
            ORDER BY id ASC
            """
        ).fetchall()

    messages_by_convo: dict[int, list[dict]] = {}
    for row in msg_rows:
        convo_id = int(row["convo_id"])
        messages_by_convo.setdefault(convo_id, []).append(_row_to_message(row))

    return [
        {
            "id": int(row["id"]),
            "farmer_id": int(row["farmer_id"]),
            "farmer_name": row["farmer_name"] or "Nông dân",
            "expert_id": int(row["expert_id"]),
            "messages": messages_by_convo.get(int(row["id"]), []),
            "unread_expert": int(row["unread_expert"] or 0),
            "typing_farmer_at": row["typing_farmer_at"] or "",
            "typing_expert_at": row["typing_expert_at"] or "",
        }
        for row in convo_rows
    ]


def create_expert_conversation(farmer_id: int, farmer_name: str, expert_id: int) -> dict:
    init_db()
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO expert_conversations (farmer_id, farmer_name, expert_id)
            VALUES (?, ?, ?)
            """,
            (farmer_id, farmer_name, expert_id),
        )
        row = conn.execute(
            """
            SELECT id, farmer_id, farmer_name, expert_id, unread_expert, typing_farmer_at, typing_expert_at
            FROM expert_conversations
            WHERE farmer_id = ? AND expert_id = ?
            """,
            (farmer_id, expert_id),
        ).fetchone()
        conn.commit()
    return {
        "id": int(row["id"]),
        "farmer_id": int(row["farmer_id"]),
        "farmer_name": row["farmer_name"] or farmer_name or "Nông dân",
        "expert_id": int(row["expert_id"]),
        "messages": [],
        "unread_expert": int(row["unread_expert"] or 0),
        "typing_farmer_at": row["typing_farmer_at"] or "",
        "typing_expert_at": row["typing_expert_at"] or "",
    }


def save_expert_message(
    convo_id: int,
    sender: str,
    text: str | None = None,
    img_src: str | None = None,
    img_b64: str | None = None,
    time_text: str | None = None,
) -> None:
    img_src, img_b64 = resolve_message_image(img_src=img_src, img_b64=img_b64)
    init_db()
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO expert_messages (convo_id, sender, text_enc, img_src_enc, img_b64_enc, time_text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                convo_id,
                sender,
                _encrypt_text(text),
                _encrypt_text(img_src),
                _encrypt_text(img_b64),
                time_text,
            ),
        )
        conn.execute(
            """
            UPDATE expert_conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (convo_id,),
        )
        conn.commit()


def update_expert_unread(convo_id: int, unread_expert: int) -> None:
    init_db()
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            UPDATE expert_conversations
            SET unread_expert = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (int(unread_expert), convo_id),
        )
        conn.commit()


def update_expert_typing(convo_id: int, sender: str, is_typing: bool) -> None:
    init_db()
    column = "typing_farmer_at" if sender == "farmer" else "typing_expert_at"
    value = datetime.now().isoformat() if is_typing else ""
    with _LOCK, _connect() as conn:
        conn.execute(
            f"""
            UPDATE expert_conversations
            SET {column} = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (value, int(convo_id)),
        )
        conn.commit()


def load_ai_messages(limit: int | None = None) -> list[dict]:
    init_db()
    sql = """
        SELECT sender, text_enc, img_src_enc, img_b64_enc, file_name_enc, ai_result_enc, time_text, created_at
        FROM ai_messages
        ORDER BY id ASC
    """
    params: tuple[Any, ...] = ()
    if limit:
        sql = """
            SELECT sender, text_enc, img_src_enc, img_b64_enc, file_name_enc, ai_result_enc, time_text, created_at
            FROM (
                SELECT *
                FROM ai_messages
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id ASC
        """
        params = (int(limit),)
    with _LOCK, _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_message(row) for row in rows]


def save_ai_message(message: dict) -> None:
    init_db()
    img_src, img_b64 = resolve_message_image(
        img_src=message.get("img_src"),
        img_b64=message.get("img_b64"),
    )
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO ai_messages (sender, text_enc, img_src_enc, img_b64_enc, file_name_enc, ai_result_enc, time_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.get("sender", "system"),
                _encrypt_text(message.get("text")),
                _encrypt_text(img_src),
                _encrypt_text(img_b64),
                _encrypt_text(message.get("file_name")),
                _encrypt_json(message.get("ai_result")),
                message.get("time"),
            ),
        )
        conn.commit()


def list_ai_history_groups(limit_days: int = 20) -> list[dict]:
    init_db()
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                DATE(created_at, 'localtime') AS day_key,
                COUNT(*) AS total_messages,
                MAX(created_at) AS last_created_at,
                MAX(CASE WHEN text_enc IS NOT NULL THEN text_enc END) AS preview_text_enc
            FROM ai_messages
            GROUP BY DATE(created_at, 'localtime')
            ORDER BY day_key DESC
            LIMIT ?
            """,
            (int(limit_days),),
        ).fetchall()

    groups: list[dict] = []
    for row in rows:
        preview = _decrypt_text(row["preview_text_enc"]) if row["preview_text_enc"] else None
        groups.append(
            {
                "day_key": row["day_key"],
                "total_messages": int(row["total_messages"] or 0),
                "last_created_at": row["last_created_at"],
                "preview": preview or "Ảnh hoặc kết quả AI",
            }
        )
    return groups


def load_ai_messages_by_day(day_key: str) -> list[dict]:
    init_db()
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            """
            SELECT sender, text_enc, img_src_enc, img_b64_enc, file_name_enc, ai_result_enc, time_text, created_at
            FROM ai_messages
            WHERE DATE(created_at, 'localtime') = ?
            ORDER BY id ASC
            """,
            (day_key,),
        ).fetchall()
    return [_row_to_message(row) for row in rows]


def load_local_profile_snapshot(id_user: int) -> dict:
    init_db()
    with _LOCK, _connect() as conn:
        row = conn.execute(
            """
            SELECT profile_enc
            FROM local_user_profiles
            WHERE id_user = ?
            """,
            (int(id_user),),
        ).fetchone()
    if not row:
        return {}
    return _decrypt_json(row["profile_enc"]) or {}


def save_local_profile_snapshot(id_user: int, updates: dict[str, Any] | None) -> dict:
    init_db()
    current = load_local_profile_snapshot(id_user)
    merged = {**current, **(updates or {})}
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO local_user_profiles (id_user, profile_enc, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id_user) DO UPDATE SET
                profile_enc = excluded.profile_enc,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                int(id_user),
                _encrypt_json(merged),
            ),
        )
        conn.commit()
    return merged
