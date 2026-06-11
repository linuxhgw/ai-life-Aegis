---
name: aegis_plan_change_interceptor
description: Handle requests to skip, delay, weaken, or change an Aegis plan without silently losing intent.
version: 0.1.0
metadata:
  hermes:
    tags: [aegis, planning, change-control]
---

# Aegis Plan Change Interceptor

Use this skill when the user asks to skip, postpone, cancel, weaken, or change an Aegis task or plan.

## Operating Rule

This skill can reason about plan changes, but durable state changes must go through Aegis Core MCP. Current Core MCP supports completion, event logging, replacement task creation, and soft task deletion. Do not claim a task was changed, cancelled, completed, or replaced unless the matching MCP call succeeded.

Relevant tools:

- `mcp_aegis_core_get_current_time`
- `mcp_aegis_core_list_tasks`
- `mcp_aegis_core_record_intervention_event`
- `mcp_aegis_core_set_task_reminders_enabled`
- `mcp_aegis_core_complete_task`
- `mcp_aegis_core_delete_task`
- `mcp_aegis_core_create_task`
- `mcp_aegis_core_schedule_reminder`

## Procedure

1. Identify the exact task or plan being changed.
2. Load today's relevant tasks with `mcp_aegis_core_list_tasks`.
3. Ask a concise reason question if the change reason is unclear.
4. Explain the likely impact on the user's stated goal.
5. Offer one conservative alternative before accepting abandonment:
   - delay with a new smaller task
   - reduce scope
   - split into a two-minute starter task
   - require a short accountability note
6. Record the plan-change discussion with `mcp_aegis_core_record_intervention_event`.
7. If the user chooses a replacement, create the replacement task and reminder through Core MCP.
8. If the user only asks to stop reminders ("不用提醒", "别提醒", "停止提醒"), call `mcp_aegis_core_set_task_reminders_enabled(enabled=false, reason=...)`. Do not cancel or complete the task for that reason alone.
9. If the user confirms cancellation or abandonment after the tradeoff is clear, call `mcp_aegis_core_delete_task`. Treat this as soft deletion, not permanent erasure.
10. If the user legitimately completed the task, record feedback first when needed, then call `mcp_aegis_core_complete_task`.

## What Not To Do

Do not directly update task fields. For stopping reminders, use `mcp_aegis_core_set_task_reminders_enabled`. For cancellation, use `mcp_aegis_core_delete_task` only after identifying the exact task and confirming the user's intent.

Do not shame the user. Be firm about tradeoffs and clear about what will be recorded.

Do not create a replacement task without user confirmation when the time, scope, or feedback requirement changes materially.

## Event Metadata

Use metadata similar to:

```json
{
  "source": "aegis_plan_change_interceptor",
  "request": "skip task",
  "reason": "user says tired",
  "decision": "created replacement | soft deleted | kept original",
  "replacement_task_id": 123
}
```
