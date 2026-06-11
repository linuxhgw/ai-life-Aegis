from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import db


DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / ".data" / "aegis-core.db"
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIME_FORMAT_LABEL = "yyyy-MM-dd HH:mm:ss"


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


def _format_time(value: datetime) -> str:
    return value.astimezone(SHANGHAI_TZ).strftime(TIME_FORMAT)


def _now() -> str:
    return _format_time(datetime.now(SHANGHAI_TZ))


def _parse_time(value: str) -> datetime:
    text = value.strip()
    try:
        parsed = datetime.strptime(text, TIME_FORMAT)
        return parsed.replace(tzinfo=SHANGHAI_TZ)
    except ValueError:
        pass

    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=SHANGHAI_TZ)
    return parsed.astimezone(SHANGHAI_TZ)


def _normalize_time(value: str | None) -> str | None:
    if value is None or not value.strip():
        return value
    return _format_time(_parse_time(value))


def _time_after(value: str, minutes: int) -> str:
    return _format_time(_parse_time(value) + timedelta(minutes=minutes))


def _normalize_message_channel(channel: str | None) -> str:
    normalized = (channel or "weixin").strip().lower()
    if normalized in {"wechat", "微信"}:
        return "weixin"
    return normalized or "weixin"


def _ensure_task(conn, task_id: int, include_deleted: bool = False) -> dict[str, Any] | None:
    if include_deleted:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND status != 'deleted'",
            (task_id,),
        ).fetchone()
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
    try:
        normalized_scheduled_time = _normalize_time(scheduled_time)
    except ValueError as exc:
        return error("invalid_input", f"invalid scheduled_time: {exc}")
    created_at = _now()

    with db.connect(context.db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (
              goal_id, plan_id, title, scheduled_time, required_feedback, metadata, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                goal_id,
                plan_id,
                title.strip(),
                normalized_scheduled_time,
                required_feedback,
                db.encode_json(metadata),
                created_at,
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
    else:
        clauses.append("status != 'deleted'")

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


def delete_task(
    context: CoreContext,
    task_id: int,
) -> dict[str, Any]:
    deleted_at = _now()
    with db.connect(context.db_path) as conn:
        task = _ensure_task(conn, task_id, include_deleted=True)
        if task is None:
            return error("not_found", "task not found")
        if task["status"] != "deleted":
            conn.execute(
                """
                UPDATE tasks
                SET status = 'deleted', deleted_at = ?
                WHERE id = ?
                """,
                (deleted_at, task_id),
            )
        task = db.decode_row(conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())
    return ok({"task": task})


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
    repeat_interval_minutes: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not scheduled_time:
        return error("invalid_input", "scheduled_time is required")
    if repeat_interval_minutes is not None and repeat_interval_minutes < 0:
        return error("invalid_input", "repeat_interval_minutes must be zero or greater")
    try:
        normalized_scheduled_time = _normalize_time(scheduled_time)
    except ValueError as exc:
        return error("invalid_input", f"invalid scheduled_time: {exc}")
    created_at = _now()

    with db.connect(context.db_path) as conn:
        if _ensure_task(conn, task_id) is None:
            return error("not_found", "task not found")
        cursor = conn.execute(
            """
            INSERT INTO reminders (
              task_id, scheduled_time, level, channel, repeat_interval_minutes, metadata, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                normalized_scheduled_time,
                level,
                channel,
                repeat_interval_minutes,
                db.encode_json(metadata),
                created_at,
            ),
        )
        reminder = db.decode_row(
            conn.execute("SELECT * FROM reminders WHERE id = ?", (cursor.lastrowid,)).fetchone()
        )
    return ok({"reminder": reminder})


def list_due_reminders(
    context: CoreContext,
    now: str | None = None,
) -> dict[str, Any]:
    threshold = _parse_time(now or _now())
    with db.connect(context.db_path) as conn:
        rows = conn.execute(
            """
            SELECT reminders.*
            FROM reminders
            JOIN tasks ON tasks.id = reminders.task_id
            WHERE reminders.status = 'pending'
              AND tasks.reminders_enabled = 1
              AND tasks.status NOT IN ('completed', 'deleted')
            """,
        ).fetchall()
    reminders = [
        reminder
        for reminder in db.decode_rows(rows)
        if _parse_time(reminder["scheduled_time"]) <= threshold
    ]
    reminders.sort(key=lambda item: (_parse_time(item["scheduled_time"]), item["id"]))
    return ok({"reminders": reminders})


def _build_reminder_message(task: dict[str, Any], reminder: dict[str, Any], attempt: int) -> str:
    metadata = reminder.get("metadata") or {}
    configured = metadata.get("message") or metadata.get("wechat_message")
    if configured:
        return str(configured)

    title = task["title"]
    feedback = task.get("required_feedback") or "text"
    prefix = "提醒" if attempt <= 1 else f"第 {attempt} 次提醒"
    if feedback == "text":
        return f"{prefix}：{title}\n完成后请直接回复一句反馈；不需要继续提醒就回复“不用提醒”。"
    return f"{prefix}：{title}\n完成后请按要求提交 {feedback} 反馈；不需要继续提醒就回复“不用提醒”。"


def _resolve_send_message_target(
    channel: str,
    reminder: dict[str, Any],
    override_target: str | None,
) -> str:
    if override_target:
        return override_target
    metadata = reminder.get("metadata") or {}
    configured = metadata.get("send_message_target") or metadata.get("target")
    if configured:
        return str(configured)
    recipient = metadata.get("wechat_target") or metadata.get("weixin_target")
    if recipient:
        return f"{channel}:{recipient}"
    return channel


def _ensure_due_task_reminders(
    conn,
    *,
    threshold: datetime,
    created_at: str,
    channel: str,
    repeat_interval_minutes: int,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT tasks.*
        FROM tasks
        WHERE tasks.scheduled_time IS NOT NULL
          AND tasks.status NOT IN ('completed', 'deleted')
          AND tasks.reminders_enabled = 1
          AND NOT EXISTS (
            SELECT 1
            FROM reminders
            WHERE reminders.task_id = tasks.id
          )
        ORDER BY tasks.scheduled_time ASC, tasks.id ASC
        """
    ).fetchall()
    created: list[dict[str, Any]] = []
    for task in db.decode_rows(rows):
        if _parse_time(task["scheduled_time"]) > threshold:
            continue
        cursor = conn.execute(
            """
            INSERT INTO reminders (
              task_id, scheduled_time, level, channel, repeat_interval_minutes, metadata, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task["id"],
                task["scheduled_time"],
                "L1",
                channel,
                repeat_interval_minutes,
                db.encode_json(
                    {
                        "source": "auto_due_task_scan",
                        "reason": "task scheduled_time is due or overdue",
                    }
                ),
                created_at,
            ),
        )
        reminder = db.decode_row(
            conn.execute(
                "SELECT * FROM reminders WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        )
        if reminder is not None:
            created.append(reminder)
    return created


def dispatch_due_reminders(
    context: CoreContext,
    now: str | None = None,
    channel: str = "weixin",
    target: str | None = None,
    default_repeat_interval_minutes: int = 15,
    limit: int = 20,
) -> dict[str, Any]:
    if default_repeat_interval_minutes < 0:
        return error("invalid_input", "default_repeat_interval_minutes must be zero or greater")
    if limit <= 0:
        return error("invalid_input", "limit must be greater than zero")

    try:
        triggered_at = _normalize_time(now) if now else _now()
    except ValueError as exc:
        return error("invalid_input", f"invalid now: {exc}")
    threshold = _parse_time(triggered_at)
    fallback_channel = _normalize_message_channel(channel)
    dispatches: list[dict[str, Any]] = []

    with db.connect(context.db_path) as conn:
        _ensure_due_task_reminders(
            conn,
            threshold=threshold,
            created_at=triggered_at,
            channel=fallback_channel,
            repeat_interval_minutes=default_repeat_interval_minutes,
        )
        rows = conn.execute(
            """
            SELECT reminders.*
            FROM reminders
            JOIN tasks ON tasks.id = reminders.task_id
            WHERE reminders.status = 'pending'
              AND tasks.reminders_enabled = 1
              AND tasks.status NOT IN ('completed', 'deleted')
            """,
        ).fetchall()
        due_reminders = [
            reminder
            for reminder in db.decode_rows(rows)
            if _parse_time(reminder["scheduled_time"]) <= threshold
        ]
        due_reminders.sort(key=lambda item: (_parse_time(item["scheduled_time"]), item["id"]))

        for reminder in due_reminders[:limit]:
            updated = conn.execute(
                """
                UPDATE reminders
                SET status = 'triggered', triggered_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (triggered_at, reminder["id"]),
            )
            if updated.rowcount != 1:
                continue

            task = _ensure_task(conn, reminder["task_id"])
            if task is None or task["status"] in {"completed", "deleted"}:
                continue
            if not task.get("reminders_enabled", 1):
                continue

            attempts = conn.execute(
                """
                SELECT COUNT(*)
                FROM intervention_events
                WHERE task_id = ?
                  AND result = 'reminder_dispatch_required'
                """,
                (task["id"],),
            ).fetchone()[0] + 1

            actual_channel = _normalize_message_channel(
                reminder["channel"] if reminder["channel"] != "core" else fallback_channel
            )
            send_target = _resolve_send_message_target(actual_channel, reminder, target)
            message = _build_reminder_message(task, reminder, attempts)
            repeat_minutes = reminder.get("repeat_interval_minutes")
            if repeat_minutes is None:
                repeat_minutes = default_repeat_interval_minutes

            next_reminder = None
            if repeat_minutes > 0:
                next_time = _time_after(triggered_at, repeat_minutes)
                next_metadata = {
                    **(reminder.get("metadata") or {}),
                    "previous_reminder_id": reminder["id"],
                    "source": "dispatch_due_reminders",
                }
                cursor = conn.execute(
                    """
                    INSERT INTO reminders (
                      task_id, scheduled_time, level, channel, repeat_interval_minutes, metadata, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task["id"],
                        next_time,
                        reminder["level"],
                        actual_channel,
                        repeat_minutes,
                        db.encode_json(next_metadata),
                        triggered_at,
                    ),
                )
                next_reminder = db.decode_row(
                    conn.execute(
                        "SELECT * FROM reminders WHERE id = ?",
                        (cursor.lastrowid,),
                    ).fetchone()
                )

            event_metadata = {
                "source": "dispatch_due_reminders",
                "send_message_target": send_target,
                "message": message,
                "attempt": attempts,
                "next_repeat_interval_minutes": repeat_minutes,
                "next_reminder_id": next_reminder["id"] if next_reminder else None,
            }
            cursor = conn.execute(
                """
                INSERT INTO intervention_events (
                  task_id, reminder_id, level, channel, result, metadata, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task["id"],
                    reminder["id"],
                    reminder["level"],
                    actual_channel,
                    "reminder_dispatch_required",
                    db.encode_json(event_metadata),
                    triggered_at,
                ),
            )
            event = db.decode_row(
                conn.execute(
                    "SELECT * FROM intervention_events WHERE id = ?",
                    (cursor.lastrowid,),
                ).fetchone()
            )
            reminder = db.decode_row(
                conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder["id"],)).fetchone()
            )
            dispatches.append(
                {
                    "task": task,
                    "reminder": reminder,
                    "intervention_event": event,
                    "channel": actual_channel,
                    "target": send_target,
                    "message": message,
                    "attempt": attempts,
                    "next_reminder": next_reminder,
                }
            )

    return ok({"dispatches": dispatches})


def set_task_reminders_enabled(
    context: CoreContext,
    task_id: int,
    enabled: bool,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    changed_at = _now()
    with db.connect(context.db_path) as conn:
        if _ensure_task(conn, task_id) is None:
            return error("not_found", "task not found")

        conn.execute(
            """
            UPDATE tasks
            SET reminders_enabled = ?
            WHERE id = ?
            """,
            (1 if enabled else 0, task_id),
        )
        dismissed_count = 0
        if not enabled:
            dismissed = conn.execute(
                """
                UPDATE reminders
                SET status = 'dismissed', dismissed_at = ?
                WHERE task_id = ? AND status = 'pending'
                """,
                (changed_at, task_id),
            )
            dismissed_count = dismissed.rowcount

        event_metadata = {
            "source": "set_task_reminders_enabled",
            "enabled": enabled,
            "reason": reason,
            "dismissed_pending_reminders": dismissed_count,
            **(metadata or {}),
        }
        cursor = conn.execute(
            """
            INSERT INTO intervention_events (
              task_id, reminder_id, level, channel, result, metadata, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                None,
                "L1",
                "core",
                "reminders_enabled" if enabled else "reminders_disabled",
                db.encode_json(event_metadata),
                changed_at,
            ),
        )
        task = db.decode_row(conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())
        event = db.decode_row(
            conn.execute(
                "SELECT * FROM intervention_events WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        )

    return ok(
        {
            "task": task,
            "intervention_event": event,
            "dismissed_pending_reminders": dismissed_count,
        }
    )


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
    created_at = _now()

    with db.connect(context.db_path) as conn:
        if _ensure_task(conn, task_id) is None:
            return error("not_found", "task not found")
        cursor = conn.execute(
            """
            INSERT INTO feedbacks (task_id, feedback_type, text, content_ref, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, feedback_type, text, content_ref, db.encode_json(metadata), created_at),
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
    created_at = _now()

    with db.connect(context.db_path) as conn:
        if task_id is not None and _ensure_task(conn, task_id) is None:
            return error("not_found", "task not found")
        if reminder_id is not None and _ensure_reminder(conn, reminder_id) is None:
            return error("not_found", "reminder not found")

        cursor = conn.execute(
            """
            INSERT INTO intervention_events (
              task_id, reminder_id, level, channel, result, metadata, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, reminder_id, level, channel, result, db.encode_json(metadata), created_at),
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
              AND status != 'deleted'
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
            """
            SELECT COUNT(*)
            FROM feedbacks
            JOIN tasks ON tasks.id = feedbacks.task_id
            WHERE substr(COALESCE(tasks.scheduled_time, tasks.created_at), 1, 10) = ?
              AND tasks.status != 'deleted'
            """,
            (date,),
        ).fetchone()[0]
        intervention_events_total = conn.execute(
            """
            SELECT COUNT(*)
            FROM intervention_events
            LEFT JOIN reminders ON reminders.id = intervention_events.reminder_id
            LEFT JOIN tasks ON tasks.id = COALESCE(intervention_events.task_id, reminders.task_id)
            WHERE substr(
              COALESCE(tasks.scheduled_time, reminders.scheduled_time, intervention_events.created_at),
              1,
              10
            ) = ?
              AND COALESCE(tasks.status, 'pending') != 'deleted'
            """,
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
    current = datetime.now(SHANGHAI_TZ)
    return ok(
        {
            "time": _format_time(current),
            "date": current.date().isoformat(),
            "weekday": current.strftime("%A"),
            "timezone": "Asia/Shanghai",
            "format": TIME_FORMAT_LABEL,
        }
    )
