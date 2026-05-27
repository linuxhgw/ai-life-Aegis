# Aegis Core MCP

Aegis Core MCP 是 Aegis Phase 1 的领域数据层。它给 Hermes 暴露任务、提醒、反馈、干预事件和执行摘要工具。

第一版只负责 Core 数据闭环，不负责 Windows 弹窗、声音、遮罩、微信或 Android。

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

- `create_task`
- `list_tasks`
- `complete_task`
- `schedule_reminder`
- `list_due_reminders`
- `record_feedback`
- `record_intervention_event`
- `get_execution_summary`
- `get_current_time`

所有工具返回统一结构：

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```
