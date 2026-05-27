from __future__ import annotations

import json
from pathlib import Path

import psycopg2
import psycopg2.extras

_CFG_PATH = Path(__file__).parent / "db" / "app_config.json"

_COMMON_DEFAULTS = {
    "anh_dai_dien": "",
    "so_dien_thoai": "",
    "email": "",
    "dia_chi": "",
    "ghi_chu": "",
}

_ROLE_DEFAULTS = {
    "admin": {
        "bo_phan": "Điều hành hệ thống",
        "pham_vi_quan_tri": "full_access",
    },
    "expert": {
        "chuyen_mon": "Chẩn đoán bệnh bò",
        "ma_chung_chi": "",
        "so_nam_kinh_nghiem": 0,
    },
    "farmer": {
        "ten_trang_trai": "",
        "dia_diem_trang_trai": "",
        "quy_mo_dan": 0,
    },
}

_COMMON_FIELDS = set(_COMMON_DEFAULTS.keys())
_ROLE_FIELDS = {
    "admin": set(_ROLE_DEFAULTS["admin"].keys()),
    "expert": set(_ROLE_DEFAULTS["expert"].keys()),
    "farmer": set(_ROLE_DEFAULTS["farmer"].keys()),
}


def _load_db_config() -> dict:
    data = json.loads(_CFG_PATH.read_text(encoding="utf-8"))
    db = data.get("database", {})
    return {
        "host": db.get("host", "localhost"),
        "port": int(db.get("port", 5432)),
        "dbname": db.get("dbname", "ConBoCuoi_DB"),
        "user": db.get("user", "postgres"),
        "password": db.get("password", ""),
    }


def _get_conn():
    conn = psycopg2.connect(**_load_db_config())
    conn.autocommit = False
    return conn


def init_profile_tables() -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id_user INTEGER PRIMARY KEY,
                    anh_dai_dien TEXT NOT NULL DEFAULT '',
                    so_dien_thoai VARCHAR(32) NOT NULL DEFAULT '',
                    email VARCHAR(255) NOT NULL DEFAULT '',
                    dia_chi TEXT NOT NULL DEFAULT '',
                    ghi_chu TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_profiles (
                    id_user INTEGER PRIMARY KEY,
                    bo_phan VARCHAR(120) NOT NULL DEFAULT 'Điều hành hệ thống',
                    pham_vi_quan_tri VARCHAR(120) NOT NULL DEFAULT 'full_access',
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS expert_profiles (
                    id_user INTEGER PRIMARY KEY,
                    chuyen_mon VARCHAR(160) NOT NULL DEFAULT 'Chẩn đoán bệnh bò',
                    ma_chung_chi VARCHAR(120) NOT NULL DEFAULT '',
                    so_nam_kinh_nghiem INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS farmer_profiles (
                    id_user INTEGER PRIMARY KEY,
                    ten_trang_trai VARCHAR(160) NOT NULL DEFAULT '',
                    dia_diem_trang_trai TEXT NOT NULL DEFAULT '',
                    quy_mo_dan INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        conn.commit()
    finally:
        conn.close()


def _role_table(role: str) -> str | None:
    role = (role or "").strip().lower()
    return {
        "admin": "admin_profiles",
        "expert": "expert_profiles",
        "farmer": "farmer_profiles",
    }.get(role)


def ensure_profiles_for_user(user: dict) -> None:
    if not user:
        return
    init_profile_tables()
    user_id = int(user.get("id_user") or 0)
    role = str(user.get("vai_tro") or "farmer").lower()
    if not user_id:
        return

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_profiles (id_user)
                VALUES (%s)
                ON CONFLICT (id_user) DO NOTHING
                """,
                (user_id,),
            )
            table = _role_table(role)
            defaults = _ROLE_DEFAULTS.get(role)
            if table and defaults:
                cols = ["id_user", *defaults.keys()]
                values = [user_id, *defaults.values()]
                placeholders = ", ".join(["%s"] * len(cols))
                cur.execute(
                    f"""
                    INSERT INTO {table} ({", ".join(cols)})
                    VALUES ({placeholders})
                    ON CONFLICT (id_user) DO NOTHING
                    """,
                    values,
                )
        conn.commit()
    finally:
        conn.close()


def ensure_profiles_for_users(users: list[dict]) -> None:
    for user in users:
        ensure_profiles_for_user(user)


def _load_common_profile(cur, user_id: int) -> dict:
    cur.execute(
        """
        SELECT id_user, anh_dai_dien, so_dien_thoai, email, dia_chi, ghi_chu, created_at, updated_at
        FROM user_profiles
        WHERE id_user = %s
        """,
        (user_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else {}


def _load_role_profile(cur, role: str, user_id: int) -> dict:
    table = _role_table(role)
    if not table:
        return {}
    cur.execute(f"SELECT * FROM {table} WHERE id_user = %s", (user_id,))
    row = cur.fetchone()
    return dict(row) if row else {}


def get_merged_profile(user: dict | None) -> dict | None:
    if not user:
        return None
    ensure_profiles_for_user(user)
    user_id = int(user.get("id_user") or 0)
    role = str(user.get("vai_tro") or "farmer").lower()

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            common = _load_common_profile(cur, user_id)
            role_profile = _load_role_profile(cur, role, user_id)
    finally:
        conn.close()

    merged = dict(user)
    merged.update(common)
    merged.update(role_profile)
    merged["role_profile"] = role_profile
    return merged


def merge_user_list(users: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for user in users:
        merged.append(get_merged_profile(user) or dict(user))
    return merged


def update_profile_fields(user: dict, updates: dict) -> dict | None:
    if not user:
        return None
    ensure_profiles_for_user(user)
    user_id = int(user.get("id_user") or 0)
    role = str(user.get("vai_tro") or "farmer").lower()

    common_updates = {k: updates[k] for k in updates if k in _COMMON_FIELDS}
    role_updates = {k: updates[k] for k in updates if k in _ROLE_FIELDS.get(role, set())}

    if not common_updates and not role_updates:
        return get_merged_profile(user)

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            if common_updates:
                set_clause = ", ".join(f"{key} = %s" for key in common_updates)
                cur.execute(
                    f"""
                    UPDATE user_profiles
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE id_user = %s
                    """,
                    [*common_updates.values(), user_id],
                )
            if role_updates:
                table = _role_table(role)
                set_clause = ", ".join(f"{key} = %s" for key in role_updates)
                cur.execute(
                    f"""
                    UPDATE {table}
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE id_user = %s
                    """,
                    [*role_updates.values(), user_id],
                )
        conn.commit()
    finally:
        conn.close()

    updated = dict(user)
    updated.update(updates)
    return get_merged_profile(updated)
