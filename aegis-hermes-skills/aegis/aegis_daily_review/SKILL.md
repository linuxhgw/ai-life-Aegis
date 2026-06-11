---
name: aegis_daily_review
description: Produce daily Aegis reviews from Core MCP execution summaries without inventing facts.
version: 0.1.0
metadata:
  hermes:
    tags: [aegis, review, summary]
---

# Aegis Daily Review

Use this skill for yesterday reviews, today planning based on prior execution, or summaries of task and feedback behavior.

## Operating Rule

Only review facts returned by Aegis Core MCP. Do not infer that a task was completed, skipped, or successful unless the data says so.

Relevant tools:

- `mcp_aegis_core_get_current_time`
- `mcp_aegis_core_get_execution_summary`
- `mcp_aegis_core_list_tasks`

Core MCP time strings use `yyyy-MM-dd HH:mm:ss` in `Asia/Shanghai`; dates for summaries remain `yyyy-MM-dd`.

## Procedure

1. Resolve the review date. If the user says "yesterday" or "today", call `mcp_aegis_core_get_current_time`.
2. Call `mcp_aegis_core_get_execution_summary` for that date.
3. Call `mcp_aegis_core_list_tasks` for the same date when task details are needed.
4. Report counts from the summary exactly.
5. Separate recorded facts from recommendations.
6. For incomplete tasks, say "not completed in Aegis" rather than guessing why.
7. Treat soft-deleted tasks as outside the active-task summary unless the user asks for cancelled/deleted task audit; then call `mcp_aegis_core_list_tasks` with `status="deleted"`.
8. Suggest today's adjustments only as proposals unless you create tasks through the goal planner flow.

## Review Format

Keep the review short and operational:

- completion count
- feedback count
- intervention count
- notable unfinished tasks
- one or two changes for today

## Constraints

Do not fabricate reasons for non-completion.

Do not treat missing feedback as proof of failure; call it missing feedback.

Do not say "I remembered" or "I tracked" unless the MCP summary confirms the data exists.
