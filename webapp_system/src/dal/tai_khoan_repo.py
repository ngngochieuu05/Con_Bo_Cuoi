"""
Repository: tai_khoan
Ánh xạ bảng tai_khoan (PostgreSQL) → tai_khoan.json
"""
from __future__ import annotations

import hashlib
from datetime import datetime

from dal.base_repo import BaseRepo

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
    hashed = hashlib.sha256(mat_khau_raw.encode()).hexdigest()
    if user["mat_khau"] == hashed:
        return user
    return None


def create_user(ten_dang_nhap: str, mat_khau_raw: str, vai_tro: str, ho_ten: str = "") -> dict:
    return _repo.insert({
        "ten_dang_nhap": ten_dang_nhap,
        "mat_khau": hashlib.sha256(mat_khau_raw.encode()).hexdigest(),
        "vai_tro": vai_tro,
        "ho_ten": ho_ten,
        "created_at": datetime.now().isoformat(),
    })


def update_user(id_user: int, updates: dict) -> dict | None:
    # Không cho phép update mat_khau trực tiếp ở đây
    safe = {k: v for k, v in updates.items() if k not in ("mat_khau", "id_user")}
    return _repo.update(id_user, safe)


def change_password(id_user: int, new_password_raw: str) -> bool:
    result = _repo.update(id_user, {
        "mat_khau": hashlib.sha256(new_password_raw.encode()).hexdigest()
    })
    return result is not None


def delete_user(id_user: int) -> bool:
    return _repo.delete(id_user)


def count_users() -> int:
    return _repo.count()
