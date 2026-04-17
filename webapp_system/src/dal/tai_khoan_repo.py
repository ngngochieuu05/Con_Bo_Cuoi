"""
Repository: tai_khoan
Ánh xạ bảng tai_khoan (PostgreSQL) → tai_khoan.json
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime

from dal.base_repo import BaseRepo

_repo = BaseRepo("tai_khoan", pk_field="id_user")


def _hash_password(raw: str) -> str:
    """PBKDF2-SHA256 with random 16-byte salt. Returns 'salt_hex:hash_hex'."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt, 260_000)
    return salt.hex() + ":" + dk.hex()


def _verify_password(raw: str, stored: str) -> bool:
    """Verify against PBKDF2 hash (new) or legacy SHA-256 (old)."""
    if ":" in stored:
        salt_hex, hash_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt, 260_000)
        return dk.hex() == hash_hex
    # Legacy unsalted SHA-256 — still accepted, upgraded on next password change
    return hashlib.sha256(raw.encode()).hexdigest() == stored


# Seed dữ liệu mặc định
_SEED = [
    {
        "id_user": 1,
        "ten_dang_nhap": "admin",
        "mat_khau": _hash_password("admin123"),
        "vai_tro": "admin",
        "ho_ten": "Quản trị viên",
        "created_at": "2026-01-01T00:00:00",
    },
    {
        "id_user": 2,
        "ten_dang_nhap": "expert01",
        "mat_khau": _hash_password("expert123"),
        "vai_tro": "expert",
        "ho_ten": "Nguyễn Văn Chuyên",
        "created_at": "2026-01-02T00:00:00",
    },
    {
        "id_user": 3,
        "ten_dang_nhap": "farmer01",
        "mat_khau": _hash_password("farmer123"),
        "vai_tro": "farmer",
        "ho_ten": "Trần Thị Nông",
        "created_at": "2026-01-03T00:00:00",
    },
]


def init_seed():
    _repo.seed(_SEED)


def get_all_users() -> list[dict]:
    return _repo.all()


def get_user_by_id(id_user: int) -> dict | None:
    return _repo.find_by_id(id_user)


def get_user_by_username(ten_dang_nhap: str) -> dict | None:
    return _repo.find_one(ten_dang_nhap=ten_dang_nhap)


def authenticate(ten_dang_nhap: str, mat_khau_raw: str) -> dict | None:
    """Xác thực tài khoản. Trả về record nếu đúng, None nếu sai."""
    user = get_user_by_username(ten_dang_nhap)
    if not user:
        return None
    if not _verify_password(mat_khau_raw, user["mat_khau"]):
        return None
    # Upgrade legacy SHA-256 hash to PBKDF2 transparently on successful login
    if ":" not in user["mat_khau"]:
        _repo.update(user["id_user"], {"mat_khau": _hash_password(mat_khau_raw)})
    return user


def create_user(ten_dang_nhap: str, mat_khau_raw: str, vai_tro: str, ho_ten: str = "") -> dict:
    return _repo.insert({
        "ten_dang_nhap": ten_dang_nhap,
        "mat_khau": _hash_password(mat_khau_raw),
        "vai_tro": vai_tro,
        "ho_ten": ho_ten,
        "created_at": datetime.now().isoformat(),
    })


def update_user(id_user: int, updates: dict) -> dict | None:
    # Không cho phép update mat_khau trực tiếp ở đây
    safe = {k: v for k, v in updates.items() if k not in ("mat_khau", "id_user")}
    return _repo.update(id_user, safe)


def change_password(id_user: int, new_password_raw: str) -> bool:
    result = _repo.update(id_user, {"mat_khau": _hash_password(new_password_raw)})
    return result is not None


def delete_user(id_user: int) -> bool:
    return _repo.delete(id_user)


def count_users() -> int:
    return _repo.count()
