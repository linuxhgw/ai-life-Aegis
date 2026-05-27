from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from . import db


DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / ".data" / "aegis-core.db"


@dataclass(frozen=True)
class CoreContext:
    db_path: Path


def default_context() -> CoreContext:
    configured = os.environ.get("AEGIS_CORE_DB_PATH")
    return CoreContext(Path(configured) if configured else DEFAULT_DB_PATH)


def init_core(context: CoreContext | None = None) -> None:
    db.init_db((context or default_context()).db_path)


def ok(data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": None}


def error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "data": None, "error": {"code": code, "message": message}}


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _ensure_task(conn, task_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return db.decode_row(row)


def _ensure_reminder(conn, reminder_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
    return db.decode_row(row)


def create_task(
    context: CoreContext,
    title: str,
    scheduled_time: str | None = None,
    required_feedback: str = "text",
    goal_id: int | None = None,
    plan_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not title.strip():
        return error("invalid_input", "title is required")

    with db.connect(context.db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (
              goal_id, plan_id, title, scheduled_time, required_feedback, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                goal_id,
                plan_id,
                title.strip(),
                scheduled_time,
                required_feedback,
                db.encode_json(metadata),
            ),
        )
        task = db.decode_row(
            conn.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone()
        )
    return ok({"task": task})


def list_tasks(
    context: CoreContext,
    date: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    clauses: list[str] = []
    params: list[Any] = []

    if date:
        clauses.append("substr(COALESCE(scheduled_time, created_at), 1, 10) = ?")
        params.append(date)
    if status:
        clauses.append("status = ?")
        params.append(status)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with db.connect(context.db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM tasks
            {where}
            ORDER BY COALESCE(scheduled_time, created_at) ASC, id ASC
            """,
            params,
        ).fetchall()
    return ok({"tasks": db.decode_rows(rows)})


def complete_task(
    context: CoreContext,
    task_id: int,
    feedback_id: int | None = None,
) -> dict[str, Any]:
    completed_at = _now()
    with db.connect(context.db_path) as conn:
        if _ensure_task(conn, task_id) is None:
            return error("not_found", "task not found")
        if feedback_id is not None:
            feedback = conn.execute(
                "SELECT id FROM feedbacks WHERE id = ? AND task_id = ?",
                (feedback_id, task_id),
            ).fetchone()
            if feedback is None:
                return error("not_found", "feedback not found")

        conn.execute(
            """
            UPDATE tasks
            SET status = 'completed', completed_at = ?, feedback_id = ?
            WHERE id = ?
            """,
            (completed_at, feedback_id, task_id),
        )
        task = db.decode_row(conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())
    return ok({"task": task})


def schedule_reminder(
    context: CoreContext,
    task_id: int,
    scheduled_time: str,
    level: str = "L1",
    channel: str = "core",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not scheduled_time:
        return error("invalid_input", "scheduled_time is required")

    with db.connect(context.db_path) as conn:
        if _ensure_task(conn, task_id) is None:
            return error("not_found", "task not found")
        cursor = conn.execute(
            """
            INSERT INTO reminders (task_id, scheduled_time, level, channel, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, scheduled_time, level, channel, db.encode_json(metadata)),
        )
        reminder = db.decode_row(
            conn.execute("SELECT * FROM reminders WHERE id = ?", (cursor.lastrowid,)).fetchone()
        )
    return ok({"reminder": reminder})


def list_due_reminders(
    context: CoreContext,
    now: str | None = None,
) -> dict[str, Any]:
    threshold = now or _now()
    with db.connect(context.db_path) as conn:
        rows = conn.execute(
            """
            SELECT reminders.*
            FROM reminders
            JOIN tasks ON tasks.id = reminders.task_id
            WHERE reminders.status = 'pending'
              AND reminders.scheduled_time <= ?
              AND tasks.status != 'completed'
            ORDER BY reminders.scheduled_time ASC, reminders.id ASC
            """,
            (threshold,),
        ).fetchall()
    return ok({"reminders": db.decode_rows(rows)})


def record_feedback(
    context: CoreContext,
    task_id: int,
    feedback_type: str,
    text: str | None = None,
    content_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not feedback_type:
        return error("invalid_input", "feedback_type is required")

    with db.connect(context.db_path) as conn:
        if _ensure_task(conn, task_id) is None:
            return error("not_found", "task not found")
        cursor = conn.execute(
            """
            INSERT INTO feedbacks (task_id, feedback_type, text, content_ref, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, feedback_type, text, content_ref, db.encode_json(metadata)),
        )
        feedback = db.decode_row(
            conn.execute("SELECT * FROM feedbacks WHERE id = ?", (cursor.lastrowid,)).fetchone()
        )
    return ok({"feedback": feedback})


def record_intervention_event(
    context: CoreContext,
    level: str,
    channel: str,
    result: str,
    task_id: int | None = None,
    reminder_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not level or not channel or not result:
        return error("invalid_input", "level, channel, and result are required")

    with db.connect(context.db_path) as conn:
        if task_id is not None and _ensure_task(conn, task_id) is None:
            return error("not_found", "task not found")
        if reminder_id is not None and _ensure_reminder(conn, reminder_id) is None:
            return error("not_found", "reminder not found")

        cursor = conn.execute(
            """
            INSERT INTO intervention_events (
              task_id, reminder_id, level, channel, result, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, reminder_id, level, channel, result, db.encode_json(metadata)),
        )
        event = db.decode_row(
            conn.execute(
                "SELECT * FROM intervention_events WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        )
    return ok({"intervention_event": event})


def get_execution_summary(context: CoreContext, date: str) -> dict[str, Any]:
    with db.connect(context.db_path) as conn:
        tasks_total = conn.execute(
            """
            SELECT COUNT(*) FROM tasks
            WHERE substr(COALESCE(scheduled_time, created_at), 1, 10) = ?
            """,
            (date,),
        ).fetchone()[0]
        tasks_completed = conn.execute(
            """
            SELECT COUNT(*) FROM tasks
            WHERE status = 'completed'
              AND substr(COALESCE(scheduled_time, completed_at, created_at), 1, 10) = ?
            """,
            (date,),
        ).fetchone()[0]
        feedbacks_total = conn.execute(
            "SELECT COUNT(*) FROM feedbacks WHERE substr(created_at, 1, 10) = ?",
            (date,),
        ).fetchone()[0]
        intervention_events_total = conn.execute(
            "SELECT COUNT(*) FROM intervention_events WHERE substr(created_at, 1, 10) = ?",
            (date,),
        ).fetchone()[0]

    return ok(
        {
            "date": date,
            "tasks_total": tasks_total,
            "tasks_completed": tasks_completed,
            "feedbacks_total": feedbacks_total,
            "intervention_events_total": intervention_events_total,
        }
    )


def get_current_time(context: CoreContext | None = None) -> dict[str, Any]:
    current = datetime.now().astimezone()
    return ok(
        {
            "iso": current.isoformat(timespec="seconds"),
            "date": current.date().isoformat(),
            "weekday": current.strftime("%A"),
            "timezone": current.tzname(),
        }
    )
