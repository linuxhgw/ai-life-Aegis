# Aegis Skills 功能清单

**定位**：Skills 负责让 Hermes 知道“怎么想、怎么判断、怎么追问、怎么表达”。Skills 不保存状态，不直接调用系统能力，不替代 MCP。

判断原则：

```text
只影响 Hermes 的推理、计划、表达、追问
  -> 放到 Skills

需要数据库、系统权限、提醒执行、反馈落盘、审计记录
  -> 放到 MCP
```

## Phase 1：计划与执行闭环

Phase 1 的 Skills 目标是约束 Hermes 使用 Core MCP，把用户目标变成可执行任务，并在提醒、反馈、复盘时遵守统一策略。

| Skill | 优先级 | 职责 | 不负责 |
|---|---:|---|---|
| `aegis_goal_planner` | P0 | 把自然语言目标拆成今日任务、计划时间、反馈要求 | 不写数据库、不安排提醒 |
| `aegis_reminder_policy` | P0 | 判断 L1-L5 提醒升级策略、反馈方式升级策略 | 不计时、不弹窗、不锁屏 |
| `aegis_plan_change_interceptor` | P0 | 处理“想改计划/跳过/取消任务”的追问、影响评估、替代方案 | 不绕过 Core MCP 改状态 |
| `aegis_daily_review` | P0 | 基于 Core MCP 执行摘要生成昨日复盘和今日建议 | 不编造未记录事实 |
| `aegis_feedback_validator` | P1 | 判断文字、图片、位置等反馈是否满足任务要求 | 不保存附件、不管理文件 |
| `aegis_message_style` | P1 | 统一提醒语气、追问风格、复盘表达 | 不参与系统动作 |

### `aegis_goal_planner`

输入：

- 用户自然语言目标。
- 当前日期时间。
- 已存在任务列表。

输出：

- 可执行任务标题。
- 建议计划时间。
- 反馈要求，例如 `text`、`photo`、`choice`、`location`。
- 是否需要创建提醒。

调用关系：

```text
Hermes + aegis_goal_planner
  -> Core MCP: create_task
  -> Core MCP: schedule_reminder
```

### `aegis_reminder_policy`

输入：

- 到期提醒。
- 任务反馈要求。
- 已发生的干预事件。
- 用户是否已反馈。

输出：

- 当前应该触发的提醒等级。
- 建议渠道，例如微信、系统通知、弹窗、遮罩。
- 下一次升级延迟。
- 用户要求停止提醒时，保留任务并关闭该任务提醒。

等级约定：

| 等级 | 策略 |
|---|---|
| L1 | 轻提醒：微信或系统通知 |
| L2 | 明确提醒：通知 + 普通弹窗 |
| L3 | 强提醒：置顶弹窗 + 声音 + 输入反馈 |
| L4 | 阻断提醒：倒计时遮罩 + 必填反馈 |
| L5 | 强制阻断：全屏阻断或锁屏，需要逃生口 |

定时循环约定：

```text
Hermes cron + aegis_reminder_policy
  -> Core MCP: dispatch_due_reminders(channel="weixin") 扫描任务列表和到期提醒
  -> Hermes send_message: 对每条 dispatch 发送微信
  -> Core MCP: record_intervention_event(result="reminder_sent" 或 "reminder_send_failed")
```

默认同一个未完成任务每 15 分钟提醒一次。用户回复“不用提醒/别提醒/停止提醒”时，先识别具体任务，再调用 `set_task_reminders_enabled(enabled=false)`；不要把这类回复等同于取消任务。

### `aegis_plan_change_interceptor`

输入：

- 用户提出的计划调整请求。
- 相关任务和执行历史。
- 今日剩余计划。

输出：

- 是否允许调整。
- 需要追问的问题。
- 对目标影响的解释。
- 替代方案，例如推迟、降低强度、拆成更小任务。

调用关系：

```text
Hermes + aegis_plan_change_interceptor
  -> Core MCP: list_tasks
  -> Core MCP: record_intervention_event
  -> Core MCP: set_task_reminders_enabled / complete_task / delete_task / create_task + schedule_reminder
```

取消任务时只能走 Core MCP 的软删除：`delete_task` 将任务标记为 `deleted` 并写入 `deleted_at`。默认复盘和提醒不再把软删除任务当作活跃任务。

### `aegis_daily_review`

输入：

- `get_execution_summary(date)` 返回的执行摘要。
- 用户当天目标和任务。

输出：

- 完成情况。
- 未完成原因的结构化总结。
- 今日建议。
- 需要继续、调整或取消的任务建议。

硬约束：

- 只能基于 MCP 返回的事实复盘。
- 不把未记录的任务说成已完成。
- 不把没有反馈的任务推断为有效完成。

## Phase 2：Profile 与场景策略

| Skill | 优先级 | 职责 |
|---|---:|---|
| `aegis_profile_policy` | P0 | 解释 Profile 行为模式、冲突取舍、用户确认话术 |
| `aegis_profile_rule_generator` | P1 | 把自然语言规则转换成 Profile 规则草稿 |
| `aegis_focus_mode_coach` | P1 | 专注、假期、夜间等模式下的建议策略和提醒文案 |

Profile 的 CRUD、激活状态、冲突候选由 Profile MCP 管理。Skill 只负责解释和辅助决策。

## Phase 3：跨端与移动端策略

| Skill | 优先级 | 职责 |
|---|---:|---|
| `aegis_cross_device_policy` | P1 | 判断 PC 和 Android 同时在线时提醒落在哪端 |
| `aegis_mobile_intervention_policy` | P1 | 判断移动端提醒是否升级到悬浮窗、遮罩或强提醒 |
| `aegis_location_feedback_policy` | P1 | 判断位置反馈是否满足任务要求 |

Android 权限、前台 App、位置、通知、遮罩和 App 控制都属于 MCP 或移动端执行器，不放到 Skill。

## Skills 输出约束

Skills 应尽量让 Hermes 输出结构化意图，便于调用 MCP：

所有传给 MCP 的时间字符串统一使用上海时区格式 `yyyy-MM-dd HH:mm:ss`；日期字段使用 `yyyy-MM-dd`。

```json
{
  "intent": "create_task",
  "title": "20:00 后不吃零食",
  "scheduled_time": "2026-05-27 20:00:00",
  "required_feedback": "text"
}
```

Skills 不应该输出“我会记住”这类没有落库动作的承诺。涉及任务、反馈、提醒、完成状态时，Hermes 必须优先调用 MCP。
