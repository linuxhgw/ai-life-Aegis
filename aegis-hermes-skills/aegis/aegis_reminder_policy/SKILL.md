---
name: aegis_reminder_policy
description: Decide Aegis reminder escalation levels and channels from due reminders and recorded events.
version: 0.1.0
metadata:
  hermes:
    tags: [aegis, reminders, escalation]
---

# Aegis Reminder Policy

Use this skill when processing due reminders, deciding whether to escalate, or choosing how to ask the user for feedback.

## Operating Rule

This skill decides policy only. It does not execute popups, sounds, overlays, locks, or messages by itself. Execution must happen through MCP or an available platform channel, and the result must be recorded with Aegis Core MCP.

Relevant Aegis Core MCP tools:

- `mcp_aegis_core_list_due_reminders`
- `mcp_aegis_core_dispatch_due_reminders`
- `mcp_aegis_core_list_tasks`
- `mcp_aegis_core_record_intervention_event`
- `mcp_aegis_core_record_feedback`
- `mcp_aegis_core_complete_task`
- `mcp_aegis_core_delete_task`
- `mcp_aegis_core_schedule_reminder`
- `mcp_aegis_core_set_task_reminders_enabled`

When Hermes has the cross-platform messaging tool available, use `send_message` for actual Weixin delivery. Core MCP decides and records reminder state; `send_message` performs the external message send.

## Time Format

All MCP-facing time strings use `yyyy-MM-dd HH:mm:ss` in `Asia/Shanghai`. Do not emit ISO timestamps in reminder scheduling or cron prompt examples.

## Escalation Levels

Use the lowest level that is likely to work:

| Level | Policy |
|---|---|
| L1 | Light reminder: chat message or system notification |
| L2 | Clear reminder: notification plus normal popup |
| L3 | Strong reminder: pinned popup, sound, and requested feedback |
| L4 | Blocking reminder: countdown overlay and required feedback |
| L5 | Forced block: fullscreen block or lock screen, with an escape path |

L4 and L5 require an explicit escape path and should explain why escalation is happening.

## Decision Procedure

1. In a scheduled reminder loop, call `mcp_aegis_core_dispatch_due_reminders(channel="weixin")`. This tool scans both the task list and pending reminders: due or overdue incomplete tasks without an existing reminder are turned into reminders automatically.
2. If it returns no dispatches, do not send a message; cron jobs should return `[SILENT]` when supported.
3. For each dispatch, send `dispatch.message` to `dispatch.target` with `send_message`.
4. Record the delivery result with `mcp_aegis_core_record_intervention_event`:
   - `result="reminder_sent"` when the Weixin send succeeded
   - `result="reminder_send_failed"` when the send failed
5. If using manual policy review instead of dispatch, get due reminders with `mcp_aegis_core_list_due_reminders`, choose level/channel, execute through the best available channel, and record every attempt.
6. If the user provides valid feedback, record it with `mcp_aegis_core_record_feedback`; complete the task only when feedback satisfies the requirement.
7. If the user says "不用提醒", "别提醒", "停止提醒", or equivalent, identify the exact task and call `mcp_aegis_core_set_task_reminders_enabled(enabled=false, reason=...)`. Do not delete the task unless the user also cancels the task itself.
8. If the user explicitly says the task should be cancelled or is no longer valid, confirm the exact task, record the reason with `mcp_aegis_core_record_intervention_event`, then call `mcp_aegis_core_delete_task`.
9. If no feedback arrives, rely on the next reminder already scheduled by `mcp_aegis_core_dispatch_due_reminders`. The default notification cadence is every 15 minutes unless a reminder has its own `repeat_interval_minutes`.

## Event Metadata

When recording an intervention event, include metadata like:

```json
{
  "source": "aegis_reminder_policy",
  "selected_level": "L2",
  "reason": "First missed reminder, task requires text feedback",
  "next_escalation_minutes": 10
}
```

## Constraints

Do not mark a task complete just because a reminder was delivered.

Do not infer feedback from silence.

Do not delete a task just because the user ignored a reminder; soft deletion requires an explicit cancellation or invalidation signal.

Do not use L4 or L5 for low-stakes tasks unless the user explicitly configured that behavior.
