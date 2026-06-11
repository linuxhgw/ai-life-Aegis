from pathlib import Path

from aegis_core_mcp import tools, worker


class FakeSender:
    def __init__(self, *, success: bool = True):
        self.success = success
        self.calls = []

    def send(self, target: str, message: str) -> worker.SendResult:
        self.calls.append({"target": target, "message": message})
        return worker.SendResult(self.success, {"fake": True})


class RaisingSender:
    def send(self, target: str, message: str) -> worker.SendResult:
        raise RuntimeError("send exploded")


def test_worker_run_once_dispatches_sends_and_records_success(tmp_path: Path):
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
        channel="weixin",
        repeat_interval_minutes=10,
        metadata={"wechat_target": "filehelper"},
    )
    reminder_id = reminder["data"]["reminder"]["id"]
    sender = FakeSender()

    result = worker.run_once(
        context,
        sender,
        now="2026-05-27 20:00:01",
    )

    assert result["ok"] is True
    assert result["data"]["dispatch_count"] == 1
    assert result["data"]["delivery_count"] == 1
    assert sender.calls == [
        {
            "target": "weixin:filehelper",
            "message": sender.calls[0]["message"],
        }
    ]
    assert "20:00 后不吃零食" in sender.calls[0]["message"]

    summary = tools.get_execution_summary(context, date="2026-05-27")
    assert summary["data"]["intervention_events_total"] == 2

    with tools.db.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT result, channel
            FROM intervention_events
            WHERE reminder_id = ? AND result = 'reminder_sent'
            """,
            (reminder_id,),
        ).fetchone()
    assert row["result"] == "reminder_sent"
    assert row["channel"] == "weixin"


def test_worker_run_once_sends_due_task_without_existing_reminder(tmp_path: Path):
    db_path = tmp_path / "aegis-core.db"
    context = tools.CoreContext(db_path)
    tools.init_core(context)

    tools.create_task(
        context,
        title="12:00 吃药",
        scheduled_time="2026-05-27 12:00:00",
    )
    sender = FakeSender()

    result = worker.run_once(
        context,
        sender,
        now="2026-05-27 12:01:00",
    )

    assert result["ok"] is True
    assert result["data"]["dispatch_count"] == 1
    assert sender.calls[0]["target"] == "weixin"
    assert "12:00 吃药" in sender.calls[0]["message"]
    assert result["data"]["deliveries"][0]["dispatch"]["next_reminder"]["scheduled_time"] == (
        "2026-05-27 12:16:00"
    )


def test_worker_run_once_records_send_failure(tmp_path: Path):
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
        channel="weixin",
    )
    reminder_id = reminder["data"]["reminder"]["id"]

    result = worker.run_once(
        context,
        FakeSender(success=False),
        now="2026-05-27 22:30:01",
    )

    assert result["ok"] is True
    assert result["data"]["deliveries"][0]["send_success"] is False

    with tools.db.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT result, channel
            FROM intervention_events
            WHERE reminder_id = ? AND result = 'reminder_send_failed'
            """,
            (reminder_id,),
        ).fetchone()
    assert row["result"] == "reminder_send_failed"
    assert row["channel"] == "weixin"


def test_worker_run_once_records_sender_exception_as_failure(tmp_path: Path):
    db_path = tmp_path / "aegis-core.db"
    context = tools.CoreContext(db_path)
    tools.init_core(context)

    created = tools.create_task(
        context,
        title="08:00 喝水",
        scheduled_time="2026-05-27 08:00:00",
    )
    task_id = created["data"]["task"]["id"]
    reminder = tools.schedule_reminder(
        context,
        task_id=task_id,
        scheduled_time="2026-05-27 08:00:00",
        channel="weixin",
    )
    reminder_id = reminder["data"]["reminder"]["id"]

    result = worker.run_once(
        context,
        RaisingSender(),
        now="2026-05-27 08:00:01",
    )

    assert result["ok"] is True
    assert result["data"]["deliveries"][0]["send_success"] is False
    assert result["data"]["deliveries"][0]["send_metadata"]["error"] == "send exploded"

    with tools.db.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT result
            FROM intervention_events
            WHERE reminder_id = ? AND result = 'reminder_send_failed'
            """,
            (reminder_id,),
        ).fetchone()
    assert row["result"] == "reminder_send_failed"


def test_load_hermes_env_reads_weixin_values(tmp_path: Path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    (hermes_home / ".env").write_text(
        "WEIXIN_TOKEN=token-from-env\n"
        "WEIXIN_ACCOUNT_ID=account-from-env\n"
        "WEIXIN_HOME_CHANNEL=filehelper\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.delenv("WEIXIN_TOKEN", raising=False)
    monkeypatch.delenv("WEIXIN_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("WEIXIN_HOME_CHANNEL", raising=False)

    worker._load_hermes_env()

    import os

    assert os.environ["WEIXIN_TOKEN"] == "token-from-env"
    assert os.environ["WEIXIN_ACCOUNT_ID"] == "account-from-env"
    assert os.environ["WEIXIN_HOME_CHANNEL"] == "filehelper"
