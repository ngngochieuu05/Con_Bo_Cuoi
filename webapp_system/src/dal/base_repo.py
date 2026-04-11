"""
Base JSON Repository
Cung cấp CRUD chung cho tất cả bảng, lưu dữ liệu dưới dạng .json.
Cấu trúc file: {"records": [...], "next_id": N}
Khi chuyển sang PostgreSQL, chỉ cần thay thế class này.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Thư mục gốc chứa DB JSON: webapp_system/src/dal/db/
_DB_DIR = Path(__file__).parent / "db"


def _db_path(table_name: str) -> Path:
    return _DB_DIR / f"{table_name}.json"


def _load(table_name: str) -> dict:
    path = _db_path(table_name)
    if not path.exists():
        return {"records": [], "next_id": 1}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"records": [], "next_id": 1}


def _save(table_name: str, store: dict) -> None:
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    with open(_db_path(table_name), "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


class BaseRepo:
    """Repository JSON chuẩn cho một bảng."""

    def __init__(self, table_name: str, pk_field: str = "id"):
        self._table = table_name
        self._pk = pk_field

    # ---------- READ ----------
    def all(self) -> list[dict]:
        return list(_load(self._table)["records"])

    def find_by_id(self, pk_value) -> dict | None:
        for rec in self.all():
            if rec.get(self._pk) == pk_value:
                return dict(rec)
        return None

    def find_one(self, **kwargs) -> dict | None:
        """Tìm bản ghi đầu tiên khớp tất cả kwargs."""
        for rec in self.all():
            if all(rec.get(k) == v for k, v in kwargs.items()):
                return dict(rec)
        return None

    def find_many(self, **kwargs) -> list[dict]:
        """Tìm tất cả bản ghi khớp kwargs."""
        return [dict(r) for r in self.all() if all(r.get(k) == v for k, v in kwargs.items())]

    # ---------- WRITE ----------
    def insert(self, data: dict[str, Any]) -> dict:
        """Thêm bản ghi mới. Tự gán PK nếu chưa có."""
        store = _load(self._table)
        if self._pk not in data:
            data = {self._pk: store["next_id"], **data}
            store["next_id"] += 1
        store["records"].append(data)
        _save(self._table, store)
        return dict(data)

    def update(self, pk_value, updates: dict[str, Any]) -> dict | None:
        """Cập nhật bản ghi theo PK."""
        store = _load(self._table)
        for i, rec in enumerate(store["records"]):
            if rec.get(self._pk) == pk_value:
                store["records"][i] = {**rec, **updates}
                _save(self._table, store)
                return dict(store["records"][i])
        return None

    def delete(self, pk_value) -> bool:
        """Xoá bản ghi theo PK."""
        store = _load(self._table)
        before = len(store["records"])
        store["records"] = [r for r in store["records"] if r.get(self._pk) != pk_value]
        if len(store["records"]) < before:
            _save(self._table, store)
            return True
        return False

    def count(self) -> int:
        return len(self.all())

    def seed(self, records: list[dict]) -> None:
        """Khởi tạo dữ liệu mẫu nếu bảng còn trống."""
        store = _load(self._table)
        if store["records"]:
            return  # Đã có dữ liệu, không seed lại
        max_id = max((r.get(self._pk, 0) for r in records), default=0)
        store["records"] = records
        store["next_id"] = max_id + 1
        _save(self._table, store)
