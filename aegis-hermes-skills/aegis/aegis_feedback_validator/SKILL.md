---
name: aegis_feedback_validator
description: Judge whether user feedback satisfies an Aegis task's required feedback before recording or completing it.
version: 0.1.0
metadata:
  hermes:
    tags: [aegis, feedback, validation]
---

# Aegis Feedback Validator

Use this skill when the user submits text, an attachment reference, a choice, or location-like evidence for an Aegis task.

## Operating Rule

Validation is separate from persistence. Once feedback is acceptable, save it with Aegis Core MCP. Only complete a task after acceptable feedback has been recorded.

Relevant tools:

- `mcp_aegis_core_list_tasks`
- `mcp_aegis_core_record_feedback`
- `mcp_aegis_core_complete_task`

## Procedure

1. Identify the target task.
2. Load the task with `mcp_aegis_core_list_tasks` if the required feedback is not already known.
3. Compare the provided evidence against `required_feedback`.
4. If evidence is insufficient, ask for the smallest missing piece.
5. If evidence is sufficient, call `mcp_aegis_core_record_feedback`.
6. If the task should be done after this feedback, call `mcp_aegis_core_complete_task` with the returned feedback id.

## Validation Rules

`text`: Accept a direct textual answer that addresses the task.

`photo`: Accept only if an attachment or content reference is available. Text saying "I did it" is not photo feedback.

`choice`: Accept a clear option selection. Ask again if the option is ambiguous.

`location`: Accept only if the user supplies a location value or a trusted location reference.

Unknown custom requirement: Ask what evidence should count, then record both the evidence and the interpretation in metadata.

## Metadata

When recording feedback, include validation metadata:

```json
{
  "source": "aegis_feedback_validator",
  "validation": "accepted",
  "requirement": "text"
}
```
