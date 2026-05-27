"""
Repository: tai_khoan
Ánh xạ bảng tai_khoan (PostgreSQL) → tai_khoan.json
"""
from __future__ import annotations

import hashlib
from datetime import datetime

from dal.base_repo import BaseRepo
from dal.profile_repo import (
    _get_conn,
    ensure_profiles_for_user,
    get_merged_profile,
    merge_user_list,
)

_repo = BaseRepo("tai_khoan", pk_field="id_user")

# Seed dữ liệu mặc định
_SEED = [
    {
        "id_user": 1,
        "ten_dang_nhap": "admin",
        "mat_khau": hashlib.sha256("admin123".encode()).hexdigest(),
        "vai_tro": "admin",
        "ho_ten": "Quản trị viên",
        "created_at": "2026-01-01T00:00:00",
    },
    {
        "id_user": 2,
        "ten_dang_nhap": "expert01",
        "mat_khau": hashlib.sha256("expert123".encode()).hexdigest(),
        "vai_tro": "expert",
        "ho_ten": "Nguyễn Văn Chuyên",
        "created_at": "2026-01-02T00:00:00",
    },
    {
        "id_user": 3,
        "ten_dang_nhap": "farmer01",
        "mat_khau": hashlib.sha256("farmer123".encode()).hexdigest(),
        "vai_tro": "farmer",
        "ho_ten": "Trần Thị Nông",
        "created_at": "2026-01-03T00:00:00",
    },
]


def init_seed():
    _repo.seed(_SEED)


def _normalize_sql_user(row: dict) -> dict:
    created_at = row.get("created_at")
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    elif created_at is None:
        created_at = datetime.now().isoformat()
    return {
        "id_user": int(row.get("id_user") or 0),
        "ten_dang_nhap": row.get("ten_dang_nhap") or "",
        "mat_khau": row.get("mat_khau") or "",
        "vai_tro": row.get("vai_tro") or "farmer",
        "ho_ten": row.get("ho_ten") or "",
        "created_at": created_at,
    }


def _sync_sql_table_into_store() -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id_user, ten_dang_nhap, mat_khau, vai_tro, ho_ten, created_at
                FROM tai_khoan
                ORDER BY id_user ASC
                """
            )
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description or []]
    finally:
        conn.close()

    if not rows:
        return

    existing_by_id = {
        int(rec.get("id_user") or 0): rec
        for rec in _repo.all()
        if int(rec.get("id_user") or 0)
    }
    for row in rows:
        sql_user = _normalize_sql_user(dict(zip(cols, row)))
        user_id = sql_user["id_user"]
        if not user_id:
            continue
        current = existing_by_id.get(user_id)
        if current is None:
            _repo.insert(sql_user)
            ensure_profiles_for_user(sql_user)
            continue

        updates = {
            key: value
            for key, value in sql_user.items()
            if current.get(key) != value
        }
        if updates:
            _repo.update(user_id, updates)
        ensure_profiles_for_user({**current, **sql_user})


def _upsert_sql_table_user(user: dict) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tai_khoan (
                    id_user, ten_dang_nhap, mat_khau, vai_tro, ho_ten, anh_dai_dien, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id_user) DO UPDATE SET
                    ten_dang_nhap = EXCLUDED.ten_dang_nhap,
                    mat_khau = EXCLUDED.mat_khau,
                    vai_tro = EXCLUDED.vai_tro,
                    ho_ten = EXCLUDED.ho_ten,
                    anh_dai_dien = EXCLUDED.anh_dai_dien,
                    created_at = EXCLUDED.created_at
                """,
                (
                    int(user.get("id_user") or 0),
                    user.get("ten_dang_nhap") or "",
                    user.get("mat_khau") or "",
                    user.get("vai_tro") or "farmer",
                    user.get("ho_ten") or "",
                    user.get("anh_dai_dien") or None,
                    user.get("created_at") or datetime.now(),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def _delete_sql_table_user(id_user: int) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tai_khoan WHERE id_user = %s", (int(id_user),))
        conn.commit()
    finally:
        conn.close()


def get_all_users() -> list[dict]:
    _sync_sql_table_into_store()
    users = _repo.all()
    return merge_user_list(users)


def get_user_by_id(id_user: int) -> dict | None:
    _sync_sql_table_into_store()
    return get_merged_profile(_repo.find_by_id(id_user))


def get_user_by_username(ten_dang_nhap: str) -> dict | None:
    _sync_sql_table_into_store()
    return get_merged_profile(_repo.find_one(ten_dang_nhap=ten_dang_nhap))


def authenticate(ten_dang_nhap: str, mat_khau_raw: str) -> dict | None:
    """Xác thực tài khoản. Trả về record nếu đúng, None nếu sai."""
    user = get_user_by_username(ten_dang_nhap)
    if not user:
        return None
    hashed = hashlib.sha256(mat_khau_raw.encode()).hexdigest()
    if user["mat_khau"] == hashed:
        return get_merged_profile(user)
    return None


def create_user(ten_dang_nhap: str, mat_khau_raw: str, vai_tro: str, ho_ten: str = "") -> dict:
    user = _repo.insert({
        "ten_dang_nhap": ten_dang_nhap,
        "mat_khau": hashlib.sha256(mat_khau_raw.encode()).hexdigest(),
        "vai_tro": vai_tro,
        "ho_ten": ho_ten,
        "created_at": datetime.now().isoformat(),
    })
    _upsert_sql_table_user(user)
    ensure_profiles_for_user(user)
    return get_merged_profile(user) or user


def update_user(id_user: int, updates: dict) -> dict | None:
    # Không cho phép update mat_khau trực tiếp ở đây
    safe = {k: v for k, v in updates.items() if k not in ("mat_khau", "id_user")}
    updated = _repo.update(id_user, safe)
    if updated:
        _upsert_sql_table_user(updated)
        ensure_profiles_for_user(updated)
    return get_merged_profile(updated)


def change_password(id_user: int, new_password_raw: str) -> bool:
    result = _repo.update(id_user, {
        "mat_khau": hashlib.sha256(new_password_raw.encode()).hexdigest()
    })
    if result:
        _upsert_sql_table_user(result)
    return result is not None


def delete_user(id_user: int) -> bool:
    deleted = _repo.delete(id_user)
    if deleted:
        _delete_sql_table_user(id_user)
    return deleted


def count_users() -> int:
    _sync_sql_table_into_store()
    return _repo.count()
