"""Cache kết quả tìm kiếm và đếm số lượt gọi Google theo tháng.

Mặc định lưu vào SQLite (file cache.db). Đặt DATABASE_URL (Postgres, vd Supabase/Neon)
để cache và bộ đếm không bị mất khi Render khởi động lại.
"""
import hashlib
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL")
SQLITE_PATH = os.getenv("CACHE_DB_PATH", "cache.db")
CACHE_TTL = float(os.getenv("CACHE_TTL_DAYS", "7")) * 86400

_init_lock = threading.Lock()
_initialized = False


@contextmanager
def _db():
    if DATABASE_URL:
        import psycopg
        conn, ph = psycopg.connect(DATABASE_URL), "%s"
    else:
        conn, ph = sqlite3.connect(SQLITE_PATH, timeout=30), "?"
    try:
        cur = conn.cursor()
        yield cur, ph
        conn.commit()
    finally:
        conn.close()


def _ensure_tables():
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        with _db() as (cur, _):
            cur.execute(
                "CREATE TABLE IF NOT EXISTS cache ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL)"
            )
            cur.execute(
                "CREATE TABLE IF NOT EXISTS usage ("
                "month TEXT PRIMARY KEY, calls INTEGER NOT NULL)"
            )
        _initialized = True


def make_key(namespace, params):
    raw = json.dumps(params, sort_keys=True, ensure_ascii=False)
    return f"{namespace}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def get(key):
    """Trả về dữ liệu đã cache, hoặc None nếu chưa có / đã hết hạn / lỗi DB."""
    try:
        _ensure_tables()
        with _db() as (cur, ph):
            cur.execute(f"SELECT value, created_at FROM cache WHERE key = {ph}", (key,))
            row = cur.fetchone()
    except Exception as e:
        print("⚠️ Lỗi đọc cache:", e)
        return None
    if not row or time.time() - row[1] > CACHE_TTL:
        return None
    return json.loads(row[0])


def set(key, value):
    try:
        _ensure_tables()
        with _db() as (cur, ph):
            cur.execute(
                f"INSERT INTO cache (key, value, created_at) VALUES ({ph}, {ph}, {ph}) "
                "ON CONFLICT (key) DO UPDATE SET value = excluded.value, created_at = excluded.created_at",
                (key, json.dumps(value, ensure_ascii=False), time.time()),
            )
    except Exception as e:
        print("⚠️ Lỗi ghi cache:", e)


def _month():
    return time.strftime("%Y-%m")


def monthly_usage():
    try:
        _ensure_tables()
        with _db() as (cur, ph):
            cur.execute(f"SELECT calls FROM usage WHERE month = {ph}", (_month(),))
            row = cur.fetchone()
        return row[0] if row else 0
    except Exception as e:
        print("⚠️ Lỗi đọc bộ đếm:", e)
        return 0


def add_usage(calls):
    if not calls:
        return
    try:
        _ensure_tables()
        with _db() as (cur, ph):
            cur.execute(
                f"INSERT INTO usage (month, calls) VALUES ({ph}, {ph}) "
                "ON CONFLICT (month) DO UPDATE SET calls = usage.calls + excluded.calls",
                (_month(), calls),
            )
    except Exception as e:
        print("⚠️ Lỗi ghi bộ đếm:", e)
