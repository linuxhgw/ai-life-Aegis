from pathlib import Path

from aegis_core_mcp import tools


def test_task_reminder_feedback_completion_summary_flow(tmp_path: Path):
    db_path = tmp_path / "aegis-core.db"
    context = tools.CoreContext(db_path)
    tools.init_core(context)

    created = tools.create_task(
        context,
        title="20:00 后不吃零食",
        scheduled_time="2026-05-27T20:00:00+08:00",
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
        scheduled_time="2026-05-27T20:00:00+08:00",
        level="L1",
        channel="core",
    )

    assert reminder["ok"] is True
    reminder_id = reminder["data"]["reminder"]["id"]

    due = tools.list_due_reminders(context, now="2026-05-27T20:00:01+08:00")
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


def test_get_current_time_returns_local_iso_value(tmp_path: Path):
    db_path = tmp_path / "aegis-core.db"
    context = tools.CoreContext(db_path)

    result = tools.get_current_time(context)

    assert result["ok"] is True
    assert "iso" in result["data"]
    assert "date" in result["data"]
    assert "timezone" in result["data"]
