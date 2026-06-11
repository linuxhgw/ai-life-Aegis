# Aegis Core MCP

Aegis Core MCP 是 Aegis Phase 1 的领域数据层。它给 Hermes 暴露任务、提醒、反馈、干预事件和执行摘要工具。

第一版负责 Core 数据闭环和微信提醒派发状态，不直接内置 Windows 弹窗、声音、遮罩或 Android。微信真实发送复用 Hermes 现有 `send_message` / `weixin` 通道。

## 安装

```bash
cd aegis-core-mcp
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

## 测试

```bash
.venv/bin/python -m pytest -q
```

## 运行 MCP Server

默认数据库路径是 `.data/aegis-core.db`。

```bash
.venv/bin/aegis-core-mcp
```

也可以指定数据库路径：

```bash
AEGIS_CORE_DB_PATH=/absolute/path/aegis-core.db .venv/bin/aegis-core-mcp
```

## Hermes 配置示例

字段名需要按实际 Hermes 版本调整，核心是通过 stdio 启动这个命令：

```yaml
mcp_servers:
  aegis_core:
    command: /root/codeSpace/oneselfProject/ai-life-Aegis/aegis-core-mcp/.venv/bin/aegis-core-mcp
```

## 工具

对 Hermes 展示、接收和新写入的时间字符串统一使用上海时区 `Asia/Shanghai`，格式为 `yyyy-MM-dd HH:mm:ss`。日期参数仍使用 `yyyy-MM-dd`。

- `create_task`
- `list_tasks`
- `complete_task`
- `delete_task`
- `schedule_reminder`
- `list_due_reminders`
- `dispatch_due_reminders`
- `set_task_reminders_enabled`
- `record_feedback`
- `record_intervention_event`
- `get_execution_summary`
- `get_current_time`

`delete_task` 是软删除：任务会被标记为 `deleted` 并写入 `deleted_at`，默认 `list_tasks`、提醒和执行摘要不会再把它当作活跃任务；需要查看已删除任务时可用 `list_tasks(status="deleted")`。

`dispatch_due_reminders` 给定时循环使用：它会先扫描任务列表，把已到时间或已超时、未完成、未关闭提醒、且还没有 reminder 的任务自动生成第一条 reminder；然后领取已到期提醒、标记当前提醒为 `triggered`、返回要通过 Hermes `send_message` 发出的微信消息 payload，并按 `repeat_interval_minutes` 或默认 15 分钟自动排下一次提醒。

`set_task_reminders_enabled(task_id, enabled=false)` 用于用户说“不用提醒/别提醒我了”时关闭该任务后续提醒；它不会删除任务，只会把待触发提醒标记为 `dismissed`。

## Hermes 定时循环

可创建一个每分钟运行的 Hermes cron job，并加载 `aegis_reminder_policy`：

```text
每分钟检查 Aegis 到期提醒：
1. 调用 mcp_aegis_core_dispatch_due_reminders(channel="weixin")。
2. 如果没有 dispatches，回复 [SILENT]。
3. 对每个 dispatch，用 send_message(target=dispatch.target, message=dispatch.message) 主动发微信。
4. 发送成功后记录 mcp_aegis_core_record_intervention_event(result="reminder_sent", task_id=dispatch.task.id, reminder_id=dispatch.reminder.id, level=dispatch.reminder.level, channel=dispatch.channel)。
5. 发送失败则记录 result="reminder_send_failed" 和错误信息。
6. 最终回复 [SILENT]，避免 cron 自动再发一条摘要。
```

## Aegis Reminder Worker

如果不想依赖 Hermes cron，可以直接运行常驻 worker：

```bash
cd aegis-core-mcp
.venv/bin/aegis-reminder-worker \
  --db-path /absolute/path/aegis-core.db \
  --interval-seconds 30
```

worker 每轮会：

1. 调用 `dispatch_due_reminders(channel="weixin")` 扫描任务列表和到期提醒。
2. 复用 Hermes `send_message` 工具发送微信消息。
3. 写回 `record_intervention_event(result="reminder_sent")` 或 `result="reminder_send_failed"`。

默认建议是每 30 秒扫描一次任务列表，但同一个未完成任务的提醒间隔是 15 分钟。也就是说：任务 20:00 到时间，20:00 附近提醒一次；如果没完成，20:15、20:30、20:45 继续提醒，直到任务完成、删除，或用户说“不用提醒”。

本仓库布局下，worker 默认会从同级 `hermes-agent` 目录导入 `tools.send_message_tool`。如果 Hermes 不在默认位置，可指定：

```bash
.venv/bin/aegis-reminder-worker --hermes-agent-path /absolute/path/hermes-agent
```

先验证但不真实发微信：

```bash
.venv/bin/aegis-reminder-worker --once --dry-run
```

指定微信目标，例如文件传输助手：

```bash
.venv/bin/aegis-reminder-worker --target weixin:filehelper
```

所有工具返回统一结构：

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```
