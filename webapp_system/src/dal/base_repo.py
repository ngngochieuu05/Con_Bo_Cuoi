"""
Base PostgreSQL Repository
Cung cấp CRUD chung cho tất cả bảng, lưu dữ liệu trong PostgreSQL.
Dùng 1 bảng `json_store` với cấu trúc: table_name, records (JSONB), next_id.
→ API hoàn toàn giống BaseRepo JSON cũ, không cần sửa bất kỳ repo nào.
→ Bảng mới tự động được tạo khi dùng lần đầu — không cần tạo tay.

Thread-safety:
  - Dùng psycopg2.pool.ThreadedConnectionPool: mỗi thread có connection riêng
  - _op_lock (RLock) bảo vệ toàn bộ read-modify-write trong insert/update/delete
    tránh race condition giữa các threads của Flet web mode
"""
from __future__ import annotations

import json
import threading
from typing import Any

import psycopg2
import psycopg2.extras
import psycopg2.pool

# ──────────────────────────────────────────────────────────────────
# Connection config
# ──────────────────────────────────────────────────────────────────
_DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "ConBoCuoi_DB",
    "user":     "postgres",
    "password": "Hieudz125@@",
}

# Pool: tối thiểu 2, tối đa 10 connections — thread-safe
_pool: psycopg2.pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()

# RLock bảo vệ toàn bộ chuỗi read-modify-write trong một repo call
_op_lock = threading.RLock()


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Trả về connection pool, khởi tạo lần đầu nếu cần."""
    global _pool
    with _pool_lock:
        if _pool is None or _pool.closed:
            _pool = psycopg2.pool.ThreadedConnectionPool(2, 10, **_DB_CONFIG)
            # Đảm bảo bảng json_store tồn tại
            conn = _pool.getconn()
            try:
                _ensure_store_table(conn)
                conn.commit()
            finally:
                _pool.putconn(conn)
            print(
                f"[DB] Pool khoi dong - {_DB_CONFIG['dbname']}@"
                f"{_DB_CONFIG['host']}:{_DB_CONFIG['port']}"
            )
    return _pool


def _ensure_store_table(conn) -> None:
    """Tạo bảng json_store nếu chưa tồn tại."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS json_store (
                table_name TEXT PRIMARY KEY,
                records    JSONB NOT NULL DEFAULT '[]',
                next_id    INTEGER NOT NULL DEFAULT 1
            )
        """)


# ──────────────────────────────────────────────────────────────────
# Internal load / save — mỗi lần lấy connection riêng từ pool
# ──────────────────────────────────────────────────────────────────

def _load(table_name: str) -> dict:
    """Đọc store từ PostgreSQL. Trả về connection về pool ngay sau khi dùng."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT records, next_id FROM json_store WHERE table_name = %s",
                (table_name,),
            )
            row = cur.fetchone()
        # Kết thúc transaction đọc để không giữ lock
        conn.rollback()
    finally:
        pool.putconn(conn)

    if row is None:
        return {"records": [], "next_id": 1}
    records = row["records"]
    if isinstance(records, str):
        records = json.loads(records)
    return {"records": list(records), "next_id": row["next_id"]}


def _save(table_name: str, store: dict) -> None:
    """Ghi store vào PostgreSQL (UPSERT) và commit ngay."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO json_store (table_name, records, next_id)
                VALUES (%s, %s::jsonb, %s)
                ON CONFLICT (table_name) DO UPDATE
                    SET records  = EXCLUDED.records,
                        next_id  = EXCLUDED.next_id
                """,
                (
                    table_name,
                    json.dumps(store["records"], ensure_ascii=False),
                    store["next_id"],
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


# ──────────────────────────────────────────────────────────────────
# BaseRepo — API giữ nguyên 100%
# ──────────────────────────────────────────────────────────────────

class BaseRepo:
    """Repository PostgreSQL chuẩn cho một bảng.
    Bảng mới tự động link vào DB khi khởi tạo lần đầu.
    Tất cả write operations đều thread-safe nhờ _op_lock.
    """

    def __init__(self, table_name: str, pk_field: str = "id"):
        self._table = table_name
        self._pk = pk_field

    # ---------- READ ----------
    def all(self) -> list[dict]:
        return _load(self._table)["records"]

    def find_by_id(self, pk_value) -> dict | None:
        for rec in self.all():
            if rec.get(self._pk) == pk_value:
                return dict(rec)
        return None

    def find_one(self, **kwargs) -> dict | None:
        for rec in self.all():
            if all(rec.get(k) == v for k, v in kwargs.items()):
                return dict(rec)
        return None

    def find_many(self, **kwargs) -> list[dict]:
        return [
            dict(r) for r in self.all()
            if all(r.get(k) == v for k, v in kwargs.items())
        ]

    # ---------- WRITE (thread-safe read-modify-write) ----------
    def insert(self, data: dict[str, Any]) -> dict:
        """Thêm bản ghi mới. Tự gán PK nếu chưa có."""
        with _op_lock:
            store = _load(self._table)
            if self._pk not in data:
                data = {self._pk: store["next_id"], **data}
                store["next_id"] += 1
            store["records"].append(data)
            _save(self._table, store)
        return dict(data)

    def update(self, pk_value, updates: dict[str, Any]) -> dict | None:
        with _op_lock:
            store = _load(self._table)
            for i, rec in enumerate(store["records"]):
                if rec.get(self._pk) == pk_value:
                    store["records"][i] = {**rec, **updates}
                    _save(self._table, store)
                    return dict(store["records"][i])
        return None

    def delete(self, pk_value) -> bool:
        with _op_lock:
            store = _load(self._table)
            before = len(store["records"])
            store["records"] = [
                r for r in store["records"] if r.get(self._pk) != pk_value
            ]
            if len(store["records"]) < before:
                _save(self._table, store)
                return True
        return False

    def count(self) -> int:
        return len(self.all())

    def seed(self, records: list[dict]) -> None:
        """Khởi tạo dữ liệu mẫu nếu bảng còn trống."""
        with _op_lock:
            store = _load(self._table)
            if store["records"]:
                return
            max_id = max((r.get(self._pk, 0) for r in records), default=0)
            store["records"] = list(records)
            store["next_id"] = max_id + 1
            _save(self._table, store)
