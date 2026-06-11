import sqlite3
from pathlib import Path

from aegis_core_mcp import tools


def test_task_reminder_feedback_completion_summary_flow(tmp_path: Path):
    db_path = tmp_path / "aegis-core.db"
    context = tools.CoreContext(db_path)
    tools.init_core(context)

    created = tools.create_task(
        context,
        title="20:00 后不吃零食",
        scheduled_time="2026-05-27 20:00:00",
        required_feedback="text",
        metadata={"source": "test"},
    )

    assert created["ok"] is True
    task_id = created["data"]["task"]["id"]
    assert created["data"]["task"]["status"] == "pending"

    listed = tools.list_tasks(context, date="2026-05-27")
    assert listed["ok"] is True
    assert [task["id"] for task in listed["data"]["tasks"]] == [task_id]

    reminder = tools.schedule_reminder(
        context,
        task_id=task_id,
        scheduled_time="2026-05-27 20:00:00",
        level="L1",
        channel="core",
        repeat_interval_minutes=10,
    )

    assert reminder["ok"] is True
    assert reminder["data"]["reminder"]["repeat_interval_minutes"] == 10
    reminder_id = reminder["data"]["reminder"]["id"]

    due = tools.list_due_reminders(context, now="2026-05-27 20:00:01")
    assert due["ok"] is True
    assert [item["id"] for item in due["data"]["reminders"]] == [reminder_id]

    feedback = tools.record_feedback(
        context,
        task_id=task_id,
        feedback_type="text",
        text="没有吃零食",
    )

    assert feedback["ok"] is True
    feedback_id = feedback["data"]["feedback"]["id"]

    event = tools.record_intervention_event(
        context,
        task_id=task_id,
        reminder_id=reminder_id,
        level="L1",
        channel="core",
        result="feedback_received",
    )

    assert event["ok"] is True

    completed = tools.complete_task(context, task_id=task_id, feedback_id=feedback_id)
    assert completed["ok"] is True
    assert completed["data"]["task"]["status"] == "completed"

    summary = tools.get_execution_summary(context, date="2026-05-27")
    assert summary["ok"] is True
    assert summary["data"]["date"] == "2026-05-27"
    assert summary["data"]["tasks_total"] == 1
    assert summary["data"]["tasks_completed"] == 1
    assert summary["data"]["feedbacks_total"] == 1
    assert summary["data"]["intervention_events_total"] == 1


def test_missing_task_returns_structured_error(tmp_path: Path):
    db_path = tmp_path / "aegis-core.db"
    context = tools.CoreContext(db_path)
    tools.init_core(context)

    result = tools.complete_task(context, task_id=999)

    assert result == {
        "ok": False,
        "data": None,
        "error": {
            "code": "not_found",
            "message": "task not found",
        },
    }


def test_dispatch_due_reminders_builds_weixin_payload_and_reschedules(tmp_path: Path):
    db_path = tmp_path / "aegis-core.db"
    context = tools.CoreContext(db_path)
    tools.init_core(context)

    created = tools.create_task(
        context,
        title="20:00 后不吃零食",
        scheduled_time="2026-05-27 20:00:00",
        required_feedback="text",
    )
    task_id = created["data"]["task"]["id"]
    reminder = tools.schedule_reminder(
        context,
        task_id=task_id,
        scheduled_time="2026-05-27 20:00:00",
        channel="core",
        repeat_interval_minutes=15,
        metadata={"wechat_target": "filehelper"},
    )
    reminder_id = reminder["data"]["reminder"]["id"]

    result = tools.dispatch_due_reminders(
        context,
        now="2026-05-27 20:00:01",
        channel="weixin",
    )

    assert result["ok"] is True
    dispatches = result["data"]["dispatches"]
    assert len(dispatches) == 1
    dispatch = dispatches[0]
    assert dispatch["reminder"]["id"] == reminder_id
    assert dispatch["reminder"]["status"] == "triggered"
    assert dispatch["channel"] == "weixin"
    assert dispatch["target"] == "weixin:filehelper"
    assert "20:00 后不吃零食" in dispatch["message"]
    assert dispatch["next_reminder"]["scheduled_time"] == "2026-05-27 20:15:01"
    assert dispatch["next_reminder"]["repeat_interval_minutes"] == 15
    assert dispatch["intervention_event"]["result"] == "reminder_dispatch_required"
    assert dispatch["attempt"] == 1

    sent_event = tools.record_intervention_event(
        context,
        task_id=task_id,
        reminder_id=reminder_id,
        level="L1",
        channel="weixin",
        result="reminder_sent",
    )
    assert sent_event["ok"] is True

    due = tools.list_due_reminders(context, now="2026-05-27 20:00:02")
    assert due["ok"] is True
    assert due["data"]["reminders"] == []

    next_due = tools.list_due_reminders(context, now="2026-05-27 20:15:02")
    assert next_due["ok"] is True
    assert [item["id"] for item in next_due["data"]["reminders"]] == [
        dispatch["next_reminder"]["id"]
    ]

    second = tools.dispatch_due_reminders(
        context,
        now="2026-05-27 20:15:02",
        channel="weixin",
    )
    assert second["ok"] is True
    assert second["data"]["dispatches"][0]["attempt"] == 2


def test_dispatch_due_reminders_auto_scans_due_tasks_without_existing_reminders(tmp_path: Path):
    db_path = tmp_path / "aegis-core.db"
    context = tools.CoreContext(db_path)
    tools.init_core(context)

    created = tools.create_task(
        context,
        title="09:00 站起来活动",
        scheduled_time="2026-05-27 09:00:00",
    )
    task_id = created["data"]["task"]["id"]

    result = tools.dispatch_due_reminders(
        context,
        now="2026-05-27 09:05:00",
        channel="weixin",
    )

    assert result["ok"] is True
    dispatches = result["data"]["dispatches"]
    assert len(dispatches) == 1
    dispatch = dispatches[0]
    assert dispatch["task"]["id"] == task_id
    assert dispatch["reminder"]["scheduled_time"] == "2026-05-27 09:00:00"
    assert dispatch["reminder"]["status"] == "triggered"
    assert dispatch["reminder"]["metadata"]["source"] == "auto_due_task_scan"
    assert dispatch["next_reminder"]["scheduled_time"] == "2026-05-27 09:20:00"
    assert dispatch["next_reminder"]["repeat_interval_minutes"] == 15

    second = tools.dispatch_due_reminders(
        context,
        now="2026-05-27 09:06:00",
        channel="weixin",
    )
    assert second["ok"] is True
    assert second["data"]["dispatches"] == []


def test_set_task_reminders_enabled_disables_pending_reminders(tmp_path: Path):
    db_path = tmp_path / "aegis-core.db"
    context = tools.CoreContext(db_path)
    tools.init_core(context)

    created = tools.create_task(
        context,
        title="22:30 睡前拉伸",
        scheduled_time="2026-05-27 22:30:00",
    )
    task_id = created["data"]["task"]["id"]
    reminder = tools.schedule_reminder(
        context,
        task_id=task_id,
        scheduled_time="2026-05-27 22:30:00",
        repeat_interval_minutes=10,
    )
    reminder_id = reminder["data"]["reminder"]["id"]

    disabled = tools.set_task_reminders_enabled(
        context,
        task_id=task_id,
        enabled=False,
        reason="用户说不用提醒",
    )

    assert disabled["ok"] is True
    assert disabled["data"]["task"]["reminders_enabled"] == 0
    assert disabled["data"]["dismissed_pending_reminders"] == 1
    assert disabled["data"]["intervention_event"]["result"] == "reminders_disabled"

    due = tools.list_due_reminders(context, now="2026-05-27 22:30:01")
    assert due["ok"] is True
    assert due["data"]["reminders"] == []

    dispatch = tools.dispatch_due_reminders(context, now="2026-05-27 22:30:01")
    assert dispatch["ok"] is True
    assert dispatch["data"]["dispatches"] == []

    with sqlite3.connect(db_path) as conn:
        status, dismissed_at = conn.execute(
            "SELECT status, dismissed_at FROM reminders WHERE id = ?",
            (reminder_id,),
        ).fetchone()
    assert status == "dismissed"
    assert dismissed_at is not None


def test_delete_task_soft_deletes_and_hides_from_active_flows(tmp_path: Path):
    db_path = tmp_path / "aegis-core.db"
    context = tools.CoreContext(db_path)
    tools.init_core(context)

    created = tools.create_task(
        context,
        title="20:00 后不吃零食",
        scheduled_time="2026-05-27 20:00:00",
    )
    task_id = created["data"]["task"]["id"]

    reminder = tools.schedule_reminder(
        context,
        task_id=task_id,
        scheduled_time="2026-05-27 20:00:00",
    )
    reminder_id = reminder["data"]["reminder"]["id"]

    deleted = tools.delete_task(context, task_id=task_id)
    assert deleted["ok"] is True
    assert deleted["data"]["task"]["status"] == "deleted"
    assert deleted["data"]["task"]["deleted_at"] is not None

    listed = tools.list_tasks(context, date="2026-05-27")
    assert listed["ok"] is True
    assert listed["data"]["tasks"] == []

    deleted_list = tools.list_tasks(context, date="2026-05-27", status="deleted")
    assert deleted_list["ok"] is True
    assert [task["id"] for task in deleted_list["data"]["tasks"]] == [task_id]

    due = tools.list_due_reminders(context, now="2026-05-27 20:00:01")
    assert due["ok"] is True
    assert [item["id"] for item in due["data"]["reminders"]] != [reminder_id]
    assert due["data"]["reminders"] == []

    completed = tools.complete_task(context, task_id=task_id)
    assert completed["ok"] is False
    assert completed["error"]["code"] == "not_found"

    summary = tools.get_execution_summary(context, date="2026-05-27")
    assert summary["ok"] is True
    assert summary["data"]["tasks_total"] == 0
    assert summary["data"]["tasks_completed"] == 0


def test_init_core_migrates_existing_database_for_soft_delete(tmp_path: Path):
    db_path = tmp_path / "aegis-core.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE tasks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              goal_id INTEGER,
              plan_id INTEGER,
              title TEXT NOT NULL,
              scheduled_time TEXT,
              required_feedback TEXT NOT NULL DEFAULT 'text',
              status TEXT NOT NULL DEFAULT 'pending',
              metadata TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              completed_at TEXT,
              feedback_id INTEGER
            )
            """
        )

    context = tools.CoreContext(db_path)
    tools.init_core(context)

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        reminder_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(reminders)").fetchall()
        }

    assert "deleted_at" in columns
    assert "reminders_enabled" in columns
    assert "repeat_interval_minutes" in reminder_columns
    assert "dismissed_at" in reminder_columns


def test_get_current_time_returns_shanghai_display_value(tmp_path: Path):
    db_path = tmp_path / "aegis-core.db"
    context = tools.CoreContext(db_path)

    result = tools.get_current_time(context)

    assert result["ok"] is True
    assert "time" in result["data"]
    assert "date" in result["data"]
    assert result["data"]["timezone"] == "Asia/Shanghai"
    assert result["data"]["format"] == "yyyy-MM-dd HH:mm:ss"
    assert "T" not in result["data"]["time"]


def test_iso_inputs_are_normalized_to_shanghai_display_format(tmp_path: Path):
    db_path = tmp_path / "aegis-core.db"
    context = tools.CoreContext(db_path)
    tools.init_core(context)

    created = tools.create_task(
        context,
        title="兼容旧 ISO 输入",
        scheduled_time="2026-05-27T20:00:00+08:00",
    )
    task_id = created["data"]["task"]["id"]
    reminder = tools.schedule_reminder(
        context,
        task_id=task_id,
        scheduled_time="2026-05-27T20:00:00+08:00",
    )

    assert created["data"]["task"]["scheduled_time"] == "2026-05-27 20:00:00"
    assert reminder["data"]["reminder"]["scheduled_time"] == "2026-05-27 20:00:00"
