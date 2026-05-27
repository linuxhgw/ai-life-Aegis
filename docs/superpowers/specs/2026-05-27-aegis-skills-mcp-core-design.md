# Aegis Skills / MCP 拆分与 Core MCP 项目设计

**日期**：2026-05-27
**状态**：设计已确认，待实现
**依据**：`docs/实际开发路线.md`、`docs/superpowers/specs/2026-05-24-aegis-mcp-scope-evaluation.md`

## 目标

本次工作把 `docs/实际开发路线.md` 中的实现方向拆成两类交付物：

1. `docs/skills功能清单.md`：说明 Hermes Skills 要实现的策略、判断、对话和流程规则。
2. `docs/mcp功能清单.md`：说明 MCP 要实现的数据读写、系统动作、提醒执行和审计事实。

同时新增一个 `aegis-core-mcp/` 项目，先支持 Phase 1 的 Core MCP。第一版不改 Hermes 源码，不实现 Windows 强提醒 UI，不引入 Profile、Perception、Android 或跨端同步。

## 职责边界

Hermes 继续作为大脑层。Skills 只定义 Hermes “怎么想、怎么判断、怎么对话”，不直接保存状态，也不执行系统动作。

MCP 作为事实层和执行层。MCP 负责读写 SQLite、创建任务、查询提醒、记录反馈、记录干预事件，并通过结构化返回值让 Hermes 可以审计真实状态。

判断原则：

```text
只影响 Hermes 的推理、计划、表达、追问
  -> Skills

需要持久化、查询、调度、系统副作用、审计记录
  -> MCP
```

## 文档设计

### Skills 功能清单

`docs/skills功能清单.md` 按阶段组织，Phase 1 先列出四个核心 Skill：

- `aegis_goal_planner`：目标拆解、今日任务生成、反馈要求建议。
- `aegis_reminder_policy`：L1-L5 提醒升级策略、反馈方式升级策略。
- `aegis_plan_change_interceptor`：计划调整请求的追问、影响评估、替代方案。
- `aegis_daily_review`：基于 Core MCP 执行摘要生成复盘和今日建议。

文档会明确每个 Skill 的职责、不负责内容、输入事实来源、输出结构，以及与 Core MCP 的调用关系。

### MCP 功能清单

`docs/mcp功能清单.md` 按阶段组织 MCP 能力：

- Phase 1：Core MCP、Intervention MCP、Messaging/WeChat Adapter、Basic Context Tools。
- Phase 2：Profile MCP、Perception MCP、Desktop Bridge。
- Phase 3：Android Control MCP、Android Perception MCP、Device Sync。
- Phase 4+：Analytics / Memory Adapter、Rule Engine。

文档会把 Phase 1 推荐实现收敛为：

- 立即实现：Aegis Core MCP。
- 后续实现：Aegis Intervention MCP。
- 暂不项目化：微信适配和 Basic Context Tools，可先复用 Hermes 或放入 Core/Intervention。

## Core MCP 项目设计

新增目录：

```text
aegis-core-mcp/
  README.md
  pyproject.toml
  src/aegis_core_mcp/
    __init__.py
    server.py
    db.py
    schemas.py
  tests/
    test_core_tools.py
```

第一版使用 Python + FastMCP + SQLite。SQLite 文件默认放在项目目录下的 `.data/aegis-core.db`，也允许通过环境变量 `AEGIS_CORE_DB_PATH` 覆盖。

### 数据模型

第一版只建 Phase 1 需要的数据表：

- `tasks`：任务标题、计划时间、反馈要求、状态、创建和完成时间。
- `reminders`：任务提醒时间、等级、状态、触发时间。
- `feedbacks`：任务反馈类型、文本、内容引用、元数据。
- `intervention_events`：提醒等级、渠道、结果、元数据和发生时间。

目标和 daily plan 暂不作为 P0 数据表强制实现。`tasks` 保留 `goal_id`、`plan_id` 可空字段，方便后续迁移。

### MCP 工具

第一版工具保持小而完整：

```text
create_task(title, scheduled_time?, required_feedback?, goal_id?, plan_id?, metadata?)
list_tasks(date?, status?)
complete_task(task_id, feedback_id?)

schedule_reminder(task_id, scheduled_time, level?, channel?, metadata?)
list_due_reminders(now?)
record_feedback(task_id, feedback_type, text?, content_ref?, metadata?)
record_intervention_event(task_id?, reminder_id?, level, channel, result, metadata?)
get_execution_summary(date)
get_current_time()
```

所有工具统一返回：

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

失败时：

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "not_found",
    "message": "task not found"
  }
}
```

### 错误处理

工具不抛出裸异常给 Hermes。常见错误会转成结构化错误：

- `invalid_input`
- `not_found`
- `conflict`
- `storage_error`

写操作尽量保持幂等友好。第一版不做复杂幂等键，但会返回创建后的实体 ID 和当前状态。

### 测试

测试覆盖：

- 初始化数据库。
- 创建任务并查询。
- 安排提醒并查询 due reminders。
- 记录反馈并完成任务。
- 记录干预事件并生成执行摘要。

测试使用临时 SQLite 文件，不污染本地 `.data`。

## 非目标

本次不做：

- 修改 `hermes-agent/` 源码。
- Windows 通知、弹窗、声音、遮罩、锁屏。
- 微信真实接入。
- Profile 管理。
- 当前 App、WiFi、进程等系统感知。
- Android 控制或跨端同步。
- 自适应学习、服从率统计、长期模式识别。

## 验收标准

完成后应满足：

1. `docs/skills功能清单.md` 和 `docs/mcp功能清单.md` 能清楚说明 Skills 与 MCP 边界。
2. `aegis-core-mcp` 可以安装依赖并运行测试。
3. Core MCP 工具能通过单元测试完成“创建任务 -> 安排提醒 -> 记录反馈 -> 完成任务 -> 生成摘要”的闭环。
4. 项目 README 说明如何运行 MCP Server，以及后续如何接入 Hermes。
