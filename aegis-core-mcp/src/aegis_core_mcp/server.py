from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import tools


mcp = FastMCP("Aegis Core")


def _context() -> tools.CoreContext:
    context = tools.default_context()
    tools.init_core(context)
    return context


@mcp.tool()
def create_task(
    title: str,
    scheduled_time: str | None = None,
    required_feedback: str = "text",
    goal_id: int | None = None,
    plan_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return tools.create_task(
        _context(),
        title=title,
        scheduled_time=scheduled_time,
        required_feedback=required_feedback,
        goal_id=goal_id,
        plan_id=plan_id,
        metadata=metadata,
    )


@mcp.tool()
def list_tasks(date: str | None = None, status: str | None = None) -> dict[str, Any]:
    return tools.list_tasks(_context(), date=date, status=status)


@mcp.tool()
def complete_task(task_id: int, feedback_id: int | None = None) -> dict[str, Any]:
    return tools.complete_task(_context(), task_id=task_id, feedback_id=feedback_id)


@mcp.tool()
def schedule_reminder(
    task_id: int,
    scheduled_time: str,
    level: str = "L1",
    channel: str = "core",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return tools.schedule_reminder(
        _context(),
        task_id=task_id,
        scheduled_time=scheduled_time,
        level=level,
        channel=channel,
        metadata=metadata,
    )


@mcp.tool()
def list_due_reminders(now: str | None = None) -> dict[str, Any]:
    return tools.list_due_reminders(_context(), now=now)


@mcp.tool()
def record_feedback(
    task_id: int,
    feedback_type: str,
    text: str | None = None,
    content_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return tools.record_feedback(
        _context(),
        task_id=task_id,
        feedback_type=feedback_type,
        text=text,
        content_ref=content_ref,
        metadata=metadata,
    )


@mcp.tool()
def record_intervention_event(
    level: str,
    channel: str,
    result: str,
    task_id: int | None = None,
    reminder_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return tools.record_intervention_event(
        _context(),
        task_id=task_id,
        reminder_id=reminder_id,
        level=level,
        channel=channel,
        result=result,
        metadata=metadata,
    )


@mcp.tool()
def get_execution_summary(date: str) -> dict[str, Any]:
    return tools.get_execution_summary(_context(), date=date)


@mcp.tool()
def get_current_time() -> dict[str, Any]:
    return tools.get_current_time(_context())


def main() -> None:
    tools.init_core()
    mcp.run()


if __name__ == "__main__":
    main()
