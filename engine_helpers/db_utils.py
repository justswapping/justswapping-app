import os
import sqlite3



_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_ROOT, "swaps.db")


def _swap_rows(cursor, status):
    """SELECT id FROM swaps WHERE status = ?"""
    cursor.execute(
        "SELECT id FROM swaps WHERE status = ?",
        (status,),
    )
    return cursor.fetchall()


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)  # ✅ increased from 5 to 30 seconds
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")   # ✅ WAL allows concurrent readers
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn
