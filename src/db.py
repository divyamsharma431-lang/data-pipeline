"""
Database layer. One long-format table holds rows from every source, each
tagged by a "source" column. This is what lets the dashboard filter with
a single WHERE clause instead of needing a different query per source.
"""

import json
import os
import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    label TEXT,
    metadata TEXT,
    UNIQUE(source, timestamp, metric, label)
);
CREATE INDEX IF NOT EXISTS idx_readings_source ON readings(source);
CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings(timestamp);
"""


@contextmanager
def get_connection(db_path: str):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def insert_rows(db_path: str, rows: list[dict]) -> int:
    """
    Insert rows, skipping exact duplicates (same source/timestamp/metric/label).
    Returns the number of rows actually inserted.
    """
    if not rows:
        return 0

    with get_connection(db_path) as conn:
        cursor = conn.executemany(
            """
            INSERT OR IGNORE INTO readings
                (source, timestamp, metric, value, label, metadata)
            VALUES (:source, :timestamp, :metric, :value, :label, :metadata)
            """,
            [
                {
                    "source": r["source"],
                    "timestamp": r["timestamp"],
                    "metric": r["metric"],
                    "value": r["value"],
                    "label": r.get("label"),
                    "metadata": json.dumps(r.get("metadata", {})),
                }
                for r in rows
            ],
        )
        conn.commit()
        return cursor.rowcount


def query_source(db_path: str, source: str, limit: int = 500) -> list[dict]:
    with get_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT source, timestamp, metric, value, label, metadata
            FROM readings
            WHERE source = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (source, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


def distinct_sources(db_path: str) -> list[str]:
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT DISTINCT source FROM readings ORDER BY source")
        return [row[0] for row in cursor.fetchall()]
