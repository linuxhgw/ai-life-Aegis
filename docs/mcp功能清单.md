# Aegis MCP 功能清单

**定位**：MCP 负责事实和动作。凡是需要持久化、查询、调度、系统权限、用户反馈或审计记录的能力，都应通过 MCP 暴露给 Hermes。

## 总体边界

```text
Hermes + Skills:
  理解目标、拆解计划、选择策略、生成话术

MCP:
  保存事实、查询状态、执行动作、记录结果
```

本阶段不改 Hermes 源码。Hermes 通过 MCP 工具调用 Aegis 的能力。

## Phase 1：最小闭环

Phase 1 目标是跑通：

```text
目标输入 -> 任务创建 -> 提醒安排 -> 到期查询 -> 反馈记录 -> 任务完成 -> 执行摘要
```

### Aegis Core MCP

优先级：P0

职责：

- 任务数据。
- 提醒数据。
- 反馈数据。
- 干预事件。
- 执行摘要。
- 基础时间工具。

第一版工具：

| 工具 | 职责 |
|---|---|
| `create_task` | 创建任务，保存计划时间和反馈要求 |
| `list_tasks` | 按日期、状态查询任务 |
| `complete_task` | 将任务标记为完成 |
| `schedule_reminder` | 为任务安排提醒 |
| `list_due_reminders` | 查询已到期但未触发的提醒 |
| `record_feedback` | 记录文字、附件引用或元数据反馈 |
| `record_intervention_event` | 记录通知、弹窗、升级、用户响应等事件 |
| `get_execution_summary` | 汇总某天任务、反馈和干预情况 |
| `get_current_time` | 返回当前本地时间 |

推荐技术栈：

- Python 3.10+
- FastMCP
- SQLite
- pytest

### Aegis Intervention MCP

优先级：P0，Core MCP 跑通后实现。

职责：

- Windows 系统通知。
- 弹窗。
- 声音。
- 文本输入。
- 倒计时遮罩。
- 全屏阻断。
- 锁屏。

工具建议：

| 工具 | 职责 |
|---|---|
| `show_notification` | 展示系统通知 |
| `show_popup` | 展示弹窗，可带按钮和超时 |
| `play_sound` | 播放提醒音 |
| `request_text_input` | 要求用户输入文字反馈 |
| `request_choice_input` | 要求用户选择反馈 |
| `show_countdown_overlay` | 展示倒计时遮罩 |
| `show_fullscreen_block` | 展示全屏阻断 |
| `lock_screen` | 锁屏或进入强制等待 |
| `dismiss_intervention` | 关闭干预 |
| `get_intervention_status` | 查询干预状态 |

安全约束：

- L4/L5 必须有开发者逃生口。
- 所有强制类工具必须返回开始时间、结束时间、用户动作和结果。
- Intervention MCP 不直接改长期任务状态，只返回执行结果，由 Hermes 或 Core MCP 记录事实。

### Messaging / WeChat Adapter

优先级：P0，但第一版不强制独立 MCP 化。

职责：

- 微信入口。
- L1 微信提醒。
- 用户回复和任务反馈关联。

实现顺序：

1. 优先复用 Hermes 现有聊天入口。
2. 不够用时做 Webhook 适配器。
3. 消息通道稳定后再独立成 Messaging MCP。

若 MCP 化，工具建议：

| 工具 | 职责 |
|---|---|
| `send_wechat_message` | 发送微信消息 |
| `get_message_delivery_status` | 查询消息投递状态 |
| `record_inbound_message` | 记录用户入站消息 |

### Basic Context Tools

第一版 `get_current_time` 放入 Core MCP。`get_system_state` 可放入后续 Intervention MCP。

当前 App、WiFi、进程、截图、OCR 不属于 Phase 1。

## Phase 2：Profile 与系统感知

### Aegis Profile MCP

职责：

- Profile CRUD。
- 激活和停用。
- 冲突候选。
- 规则预览。
- 导出 Hermes Skill 草稿。

工具建议：

| 工具 | 职责 |
|---|---|
| `create_profile` | 创建 Profile |
| `update_profile` | 更新 Profile |
| `delete_profile` | 删除 Profile |
| `list_profiles` | 查询 Profile |
| `activate_profile` | 激活 Profile |
| `deactivate_profile` | 停用 Profile |
| `get_current_profiles` | 查询当前激活 Profile |
| `preview_profile_effect` | 预览规则影响 |
| `export_profile_as_hermes_skill` | 导出 Skill 草稿 |

### Aegis Perception MCP

职责：

- 当前 App。
- 当前窗口。
- 运行进程。
- 当前 WiFi。
- 空闲时长。
- 屏幕状态。

工具建议：

| 工具 | 职责 |
|---|---|
| `get_active_app` | 查询当前应用 |
| `get_active_window` | 查询当前窗口标题 |
| `get_running_processes` | 查询进程列表 |
| `get_current_wifi` | 查询 WiFi |
| `get_idle_duration` | 查询空闲时长 |
| `get_screen_state` | 查询屏幕状态 |

隐私风险高的能力，例如截图、OCR、浏览器语义分析，放到基础闭环稳定后再评估。

### Desktop Bridge

桌宠和计划中心优先走本地 WebSocket/Gateway，不急于 MCP 化。Hermes 需要主动控制桌宠时，再暴露少量 MCP 工具：

| 工具 | 职责 |
|---|---|
| `set_pet_emotion` | 设置桌宠表情 |
| `show_plan_center` | 打开计划中心 |
| `show_profile_switcher` | 打开 Profile 切换器 |
| `push_desktop_state` | 推送桌面状态 |

## Phase 3：Android 与跨端

### Android Control MCP

职责：

- Android 通知。
- 弹窗。
- 悬浮窗。
- 遮罩。
- 拍照。
- 位置。
- App 控制。

### Android Perception MCP

职责：

- 前台 App。
- WiFi。
- 屏幕状态。
- 设备状态。
- 最近 App 使用记录。

### Device Sync

跨端同步主链路建议使用 WebSocket 或 gRPC。MCP 只给 Hermes 提供查询和控制入口：

| 工具 | 职责 |
|---|---|
| `list_devices` | 查询设备 |
| `get_device_status` | 查询设备状态 |
| `set_device_profile` | 设置设备 Profile |
| `broadcast_state_update` | 广播状态更新 |

## Phase 4+

### Analytics / Memory Adapter MCP

当 Hermes 自带记忆不足以支撑统计时再实现：

- 完成率。
- 服从率。
- 干预有效性。
- 拖延模式。
- 目标进度。

### Rule Engine MCP

当 Profile、硬拦截、低延迟规则变复杂后再实现：

- 规则创建。
- 规则启停。
- 上下文评估。
- 规则模拟。

## 当前实现决策

本次只创建 `aegis-core-mcp/`：

- 先实现 Core MCP 的 Phase 1 工具。
- 不实现 Windows 强提醒。
- 不改 Hermes。
- 不做微信真实接入。
- 后续 Intervention MCP 通过 Core MCP 的提醒和任务数据联动。
