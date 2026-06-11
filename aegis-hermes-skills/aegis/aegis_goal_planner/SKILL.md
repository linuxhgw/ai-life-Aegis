---
name: aegis_goal_planner
description: Convert natural language personal goals into Aegis Core MCP tasks and reminders.
version: 0.1.0
metadata:
  hermes:
    tags: [aegis, planning, tasks]
---

# Aegis Goal Planner

Use this skill when the user gives a personal goal, habit, commitment, or plan that should become trackable work in Aegis.

## Operating Rule

Aegis state must be written through the Aegis Core MCP tools. Do not claim that a task, reminder, or feedback requirement has been saved unless the matching MCP call succeeded.

Registered Hermes MCP tool names use the `mcp_aegis_core_` prefix:

- `mcp_aegis_core_get_current_time`
- `mcp_aegis_core_list_tasks`
- `mcp_aegis_core_create_task`
- `mcp_aegis_core_schedule_reminder`

## Procedure

1. Get current local time with `mcp_aegis_core_get_current_time`.
2. Ask only for missing information that prevents a valid task from being created: title, date/time, or feedback requirement.
3. Check existing tasks for the relevant date with `mcp_aegis_core_list_tasks`.
4. Turn the goal into concrete tasks with clear titles and scheduled Shanghai timestamps.
5. Pick a feedback requirement: `text`, `photo`, `choice`, `location`, or a short custom value.
6. Call `mcp_aegis_core_create_task` for each accepted task.
7. If the task needs a reminder, call `mcp_aegis_core_schedule_reminder` using the created task id.
8. For ordinary personal reminders, prefer `channel="weixin"` and set `repeat_interval_minutes=15` unless the user asks for a different cadence.

## Time Format

Use `yyyy-MM-dd HH:mm:ss` for all MCP-facing time strings, interpreted in `Asia/Shanghai`.

Example:

```json
{
  "scheduled_time": "2026-05-27 20:00:00"
}
```

## Task Design

Prefer small tasks that can be verified the same day.

If the user gives a broad goal, split it into today's next action first. Avoid creating many future tasks unless the user asks for a multi-day plan.

Use `metadata` to preserve useful context, for example:

```json
{
  "source": "aegis_goal_planner",
  "original_goal": "User's original wording",
  "reason": "Why this task was created"
}
```

## Response Style

After successful MCP writes, summarize only what was actually created:

- task title
- scheduled time
- feedback requirement
- reminder time and level, if scheduled
- repeat interval and Weixin target/channel, if scheduled

If an MCP call fails, show the structured error and do not pretend the plan was saved.
