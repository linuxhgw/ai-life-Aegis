from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  goal_id INTEGER,
  plan_id INTEGER,
  title TEXT NOT NULL,
  scheduled_time TEXT,
  required_feedback TEXT NOT NULL DEFAULT 'text',
  status TEXT NOT NULL DEFAULT 'pending',
  reminders_enabled INTEGER NOT NULL DEFAULT 1,
  metadata TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TEXT,
  deleted_at TEXT,
  feedback_id INTEGER
);

CREATE TABLE IF NOT EXISTS reminders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL,
  scheduled_time TEXT NOT NULL,
  level TEXT NOT NULL DEFAULT 'L1',
  channel TEXT NOT NULL DEFAULT 'core',
  repeat_interval_minutes INTEGER,
  status TEXT NOT NULL DEFAULT 'pending',
  metadata TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  triggered_at TEXT,
  dismissed_at TEXT,
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS feedbacks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL,
  feedback_type TEXT NOT NULL,
  text TEXT,
  content_ref TEXT,
  metadata TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS intervention_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER,
  reminder_id INTEGER,
  level TEXT NOT NULL,
  channel TEXT NOT NULL,
  result TEXT NOT NULL,
  metadata TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(task_id) REFERENCES tasks(id),
  FOREIGN KEY(reminder_id) REFERENCES reminders(id)
);
"""


JSON_FIELDS = {"metadata"}


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    task_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(tasks)").fetchall()
    }
    if "deleted_at" not in task_columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN deleted_at TEXT")
    if "reminders_enabled" not in task_columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN reminders_enabled INTEGER NOT NULL DEFAULT 1")

    reminder_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(reminders)").fetchall()
    }
    if "repeat_interval_minutes" not in reminder_columns:
        conn.execute("ALTER TABLE reminders ADD COLUMN repeat_interval_minutes INTEGER")
    if "dismissed_at" not in reminder_columns:
        conn.execute("ALTER TABLE reminders ADD COLUMN dismissed_at TEXT")


def encode_json(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


def decode_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    for field in JSON_FIELDS:
        if field in item:
            item[field] = json.loads(item[field] or "{}")
    return item


def decode_rows(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [decode_row(row) for row in rows if row is not None]
