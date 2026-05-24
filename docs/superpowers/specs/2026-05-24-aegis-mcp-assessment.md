# Aegis MCP 需求评估与清单

**版本**：v1.0
**日期**：2026-05-24
**依据**：《Aegis 个人生活助手 — 需求与架构设计 v0.6》

---

## 一、评估结论（TL;DR）

原设计文档在 Perception（感知）和 Intervention（干预）两类 MCP 上定义较完整，但**缺失了数据持久化、任务调度、Profile 管理、跨端同步四大类 MCP**。完整跑通 Phase 1 功能闭环，实际需要 **5 个 MCP Server、约 35+ 个工具**。以下是按 Phase 梳理的完整清单。

---

## 二、MCP 架构原则

```
┌─────────────────────────────────────────────────────────────┐
│                     Hermes（大脑层）                           │
│              理解意图 · 记忆历史 · 决策 · 生成技能               │
└──────────────────────────┬──────────────────────────────────┘
                           │ 调用 MCP Tools
┌──────────────────────────▼──────────────────────────────────┐
│                   Aegis MCP Server 集群                       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ aegis-perception │  │ aegis-intervention │  │ aegis-storage    │      │
│  │ （感知现实世界）  │  │ （执行干预动作）    │  │ （数据持久化）    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ aegis-scheduler  │  │ aegis-device       │                        │
│  │ （定时与提醒）    │  │ （跨端协同）        │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

**分组原则**：
1. **单一职责**：每个 MCP Server 只干一类事，方便独立开发、测试、替换
2. **Hermes 直接调用**：所有工具都设计为 Hermes 可直接调用的原子操作
3. **本地优先**：Phase 1-2 全部工具基于本地 PC，不依赖云服务
4. **状态外置**：Hermes 是无状态的，所有状态通过 `aegis-storage` 存取

---

## 三、Phase 1 MCP 清单（功能闭环）

Phase 1 目标：跑通「目标→拆解→计划→提醒→记录」闭环。原设计认为 Phase 1 只需要 `aegis-intervention`，但实际**必须补充 `aegis-storage` 和 `aegis-scheduler`**，否则 Hermes 无法保存计划、无法触发定时提醒。

### 3.1 aegis-intervention（干预执行）

负责所有「出口层」用户触达与反馈收集。技术栈：Rust，Windows API。

| 类别 | 工具名 | 输入 | 输出 | 对应 L1-L5 |
|------|--------|------|------|-----------|
| **微信通知** | `send_wechat_message` | `message: string` | `{ sent: bool, error?: string }` | L1 |
| **系统通知** | `show_notification` | `title, body: string` | `{ shown: bool }` | L1-L2 |
| **弹窗** | `show_popup` | `title, message, buttons?: string[]` | `{ clicked?: string, timeout: bool }` | L2-L3 |
| **提示音** | `play_sound` | `sound_type: "gentle" \| "alert" \| "alarm"` | `{ played: bool }` | L3 |
| **文本输入** | `get_text_input` | `prompt: string` | `{ submitted: bool, text: string }` | 反馈收集 |
| **拍照上传** | `get_photo_input` | `prompt: string` | `{ submitted: bool, photo_base64: string }` | 反馈收集 |
| **位置确认** | `get_location_input` | `prompt: string` | `{ submitted: bool, lat, lng, address }` | 反馈收集 |
| **多选确认** | `get_choice_input` | `prompt, options: string[]` | `{ submitted: bool, choice: string }` | 反馈收集 |
| **倒计时遮罩** | `show_countdown_overlay` | `message, seconds, required_feedback?` | `{ completed: bool, waited_seconds, feedback? }` | L4 |
| **全屏阻断** | `show_fullscreen_block` | `message, required_feedback: string` | `{ completed: bool, feedback_submitted: string }` | L5 |
| **屏幕锁定** | `lock_screen` | `duration_seconds: number` | `{ unlocked: bool }` | L5 |

> **与原设计差异**：无。此 Server 原设计已较完整。

### 3.2 aegis-perception（系统感知）— Phase 1 最小集

负责向 Hermes 提供当前环境上下文。Phase 1 只需要基础时间/在线状态。

| 工具名 | 输入 | 输出 | 用途 |
|--------|------|------|------|
| `get_current_time` | — | `{ time, weekday, date: string }` | 判断提醒时机、生成计划 |
| `get_system_state` | — | `{ pc_online, screen_on: bool }` | 判断 PC 是否可用 |

> **与原设计差异**：无。但原设计说「Phase 1 不需要 Perception MCP」，这是错误的——`get_current_time` 是生成今日计划和判断提醒时机的必要条件，应纳入 Phase 1。

### 3.3 aegis-storage（数据持久化）— **原设计缺失，Phase 1 必需**

Hermes 生成的计划、任务执行记录、用户反馈、拦截历史都需要落盘。原设计提到「本地数据库（SQLite）」，但没有定义 Hermes 如何通过 MCP 操作它。

| 工具名 | 输入 | 输出 | 用途 |
|--------|------|------|------|
| **目标管理** | | | |
| `goal_create` | `title, category, deadline?` | `{ goal_id }` | 保存长期/短期目标 |
| `goal_list` | `status?, category?` | `{ goals[] }` | 查询历史目标 |
| `goal_update` | `goal_id, fields` | `{ updated }` | 修改目标状态 |
| **任务管理** | | | |
| `task_create` | `goal_id, title, scheduled_time, required_feedback, reminder_level` | `{ task_id }` | 创建今日任务 |
| `task_list` | `date?, status?, goal_id?` | `{ tasks[] }` | 查询今日/历史任务 |
| `task_update` | `task_id, status, feedback?, completed_at?` | `{ updated }` | 更新任务状态 |
| `task_delete` | `task_id` | `{ deleted }` | 删除任务 |
| **执行记录** | | | |
| `record_create` | `task_id, action, detail, timestamp` | `{ record_id }` | 记录提醒/反馈/升级事件 |
| `record_list` | `task_id?, date?, action?` | `{ records[] }` | 查询执行历史 |
| **拦截记录** | | | |
| `intercept_create` | `task_id, level, user_input, hermes_response, result` | `{ intercept_id }` | 记录多层拦截过程 |
| `intercept_list` | `task_id?, date?` | `{ intercepts[] }` | 查询拦截历史 |

> **关键决策**：Hermes 生成目标拆解后，调用 `goal_create` + `task_create` 写入 SQLite；提醒执行器读取 SQLite 触发提醒；用户反馈后 Hermes 调用 `task_update` + `record_create` 更新状态。

### 3.4 aegis-scheduler（定时调度）— **原设计缺失，Phase 1 必需**

双线升级提醒的核心是「定时触发」。没有调度器，Hermes 只能即时响应，无法实现「20:00 提醒 → 20:01 升级 → 20:02 再升级」。

| 工具名 | 输入 | 输出 | 用途 |
|--------|------|------|------|
| `reminder_schedule` | `task_id, trigger_at, level, channels[]` | `{ schedule_id }` | 预约一次提醒 |
| `reminder_cancel` | `schedule_id` | `{ cancelled }` | 取消预约 |
| `reminder_list` | `status?, after?` | `{ reminders[] }` | 查看待触发提醒 |
| `reminder_escalate` | `task_id, current_level, next_level, delay_seconds` | `{ scheduled }` | 预约下一次升级提醒 |

> **关键决策**：调度器是独立进程，到点后通过某种机制（如本地 HTTP/WebSocket）通知 Hermes，由 Hermes 决策具体调用哪个 intervention 工具。或者，调度器可直接调用 intervention，但这样会绕过 Hermes 的决策层。推荐：**调度器只负责"到时通知 Hermes"，执行动作仍由 Hermes 决策**。

---

## 四、Phase 2 MCP 清单（多入口 + Profile）

### 4.1 aegis-perception（扩展）

| 工具名 | 输入 | 输出 | 用途 |
|--------|------|------|------|
| `get_active_app` | — | `{ app, title: string }` | Profile 规则匹配：当前在用什么 App |
| `get_running_processes` | — | `{ processes: string[] }` | 检测特定进程是否存在 |
| `get_current_wifi` | — | `{ ssid, connected: bool }` | Profile 激活条件：判断所在位置 |

### 4.2 aegis-intervention（扩展）

| 工具名 | 输入 | 输出 | 用途 |
|--------|------|------|------|
| `set_pet_emotion` | `type: "normal"\|"happy"\|"angry"\|"sad"\|"worried"` | `{ set }` | 桌宠表情配合提醒 |
| `activate_profile` | `profile_id` | `{ activated }` | 激活指定 Profile |
| `deactivate_profile` | `profile_id` | `{ deactivated }` | 停用指定 Profile |

### 4.3 aegis-storage（扩展）— Profile 管理

| 工具名 | 输入 | 输出 | 用途 |
|--------|------|------|------|
| `profile_create` | `name, icon, triggers[], rules[]` | `{ profile_id }` | 新建 Profile |
| `profile_list` | `status?` | `{ profiles[] }` | 列出所有 Profile |
| `profile_update` | `profile_id, fields` | `{ updated }` | 编辑 Profile |
| `profile_delete` | `profile_id` | `{ deleted }` | 删除 Profile |
| `profile_get_active` | — | `{ profile_id?, profile_name? }` | 获取当前激活 Profile |
| `profile_log_switch` | `from_profile, to_profile, reason` | `{ logged }` | 记录 Profile 切换历史 |

> **关键决策**：Profile 编辑器（UI 向导）生成 YAML → 调用 `profile_create` 存入 SQLite → Hermes 加载为 Skill。Profile 的激活可以是 UI 直接调用 `activate_profile`，也可以是 Hermes 根据时间/WiFi 条件判断后调用。

### 4.4 aegis-scheduler（扩展）— 周期性任务

| 工具名 | 输入 | 输出 | 用途 |
|--------|------|------|------|
| `cron_schedule` | `cron_expr, task_type, payload` | `{ cron_id }` | 周期性任务（如每日生成计划） |
| `cron_cancel` | `cron_id` | `{ cancelled }` | 取消周期性任务 |

---

## 五、Phase 3 MCP 清单（Android + 跨端协同）

### 5.1 aegis-device（跨端同步）— **新增 Server**

负责 PC 与 Android 之间的状态同步。技术栈：Rust（PC端）+ Kotlin（Android端），WebSocket 通信。

| 工具名 | 输入 | 输出 | 执行端 |
|--------|------|------|--------|
| `device_register` | `device_type, device_name` | `{ device_id }` | 任意端 |
| `device_list` | — | `{ devices[] }` | PC |
| `device_sync_profile` | `profile_id, target_device?` | `{ synced }` | PC |
| `device_sync_task` | `task_id, target_device?` | `{ synced }` | PC |
| `device_push_notification` | `device_id, title, body` | `{ pushed }` | PC |
| `device_get_state` | `device_id` | `{ online, profile_id?, battery? }` | PC |

### 5.2 aegis-perception（Android 扩展）

Android 端作为 Perception 数据源，将感知到的信息上报给 Hermes。

| 工具名 | 输入 | 输出 | 执行端 |
|--------|------|------|--------|
| `get_active_app` | — | `{ app, package: string }` | Android |
| `get_current_wifi` | — | `{ ssid, connected }` | Android |
| `get_location` | — | `{ lat, lng, accuracy }` | Android |
| `get_battery_level` | — | `{ level, charging }` | Android |

### 5.3 aegis-intervention（Android 扩展）

| 工具名 | 输入 | 输出 | 执行端 |
|--------|------|------|--------|
| `show_notification` | `title, body, priority` | `{ shown }` | Android |
| `show_overlay` | `message, duration` | `{ shown }` | Android |
| `show_fullscreen_block` | `message, required_feedback` | `{ completed, feedback }` | Android |
| `vibrate` | `pattern: string` | `{ vibrated }` | Android |

---

## 六、原设计文档 Gap 分析

| 缺失项 | 影响 | 建议纳入阶段 |
|--------|------|-------------|
| **aegis-storage 全部工具** | Hermes 无法保存计划、查询历史、记录执行结果，Phase 1 闭环断裂 | Phase 1 |
| **aegis-scheduler 全部工具** | 无法实现定时提醒和升级策略，L1-L5 无法自动触发 | Phase 1 |
| **Profile CRUD 工具** | Phase 2 用户可通过 UI 新建 Profile，但 Hermes 没有接口管理 Profile | Phase 2 |
| **aegis-device 全部工具** | Phase 3 双端协同无通信机制 | Phase 3 |
| **Webhook 入口 MCP** | 架构图中有 Webhook 入口，但无对应的 MCP 接收外部事件 | Phase 2（可选） |
| **文件系统 MCP** | 架构图中有「写文件」出口，但未定义工具 | Phase 1（可选） |

---

## 七、MCP Server 职责矩阵

| Server | Phase 1 | Phase 2 | Phase 3 | 核心职责 |
|--------|---------|---------|---------|----------|
| `aegis-intervention` | 11 tools | +3 tools | +4 tools | 用户触达、反馈收集、强制阻断 |
| `aegis-perception` | 2 tools | +3 tools | +4 tools | 环境感知、状态采集 |
| `aegis-storage` | 9 tools | +6 tools | — | 数据持久化、历史查询 |
| `aegis-scheduler` | 4 tools | +2 tools | — | 定时触发、升级调度 |
| `aegis-device` | — | — | 6 tools | 跨端注册、状态同步、消息推送 |
| **合计** | **26 tools** | **+14 tools** | **+14 tools** | |

---

## 八、关键架构决策

### 8.1 调度器与 Hermes 的协作模式

**方案 A（推荐）：调度器只通知，Hermes 决策**
```
Scheduler → 到点通知 Hermes → Hermes 查询任务详情 → Hermes 调用 Intervention
```
- 优点：Hermes 保留完整决策权，可在提醒前做个性化调整（如"你昨晚没睡好，今晚任务减轻"）
- 缺点：需要 Hermes 常驻运行，不能离线

**方案 B：调度器直接执行**
```
Scheduler → 到点直接调用 Intervention → 同时通知 Hermes 记录
```
- 优点：Hermes 不需要常驻
- 缺点：绕过大脑层，无法做动态调整

**结论**：选方案 A。Aegis 的核心价值是 Hermes 的决策能力，不应为技术便利牺牲架构完整性。

### 8.2 Storage 是否暴露给 Hermes？

**必须暴露**。原设计暗示 SQLite 由应用层直接管理，但 Hermes 需要：
- 生成计划后立即写入（`task_create`）
- 用户问"昨天执行怎么样"时查询（`task_list` + `record_list`）
- 多层拦截时查询历史（`intercept_list`）

如果 Hermes 不能直接调用 Storage MCP，就需要应用层做大量桥接逻辑，反而增加复杂度。

### 8.3 跨端通信协议

Phase 3 推荐 **WebSocket + 局域网广播发现**：
- PC 和 Android 处于同一局域网时自动发现
- WebSocket 全双工，适合实时同步 Profile 和任务状态
- 断网时各端独立运行，恢复后自动同步

---

## 九、开发优先级建议

| 优先级 | MCP Server | 关键工具 | 阻塞关系 |
|--------|-----------|----------|----------|
| P0 | `aegis-intervention` | `show_notification`, `show_popup`, `show_fullscreen_block`, `get_text_input`, `get_photo_input` | 无 |
| P0 | `aegis-storage` | `task_create`, `task_list`, `task_update`, `record_create` | 无 |
| P0 | `aegis-scheduler` | `reminder_schedule`, `reminder_escalate` | 依赖 storage |
| P0 | `aegis-perception` | `get_current_time`, `get_system_state` | 无 |
| P1 | `aegis-intervention` | `send_wechat_message`, `play_sound`, `show_countdown_overlay` | 无 |
| P1 | `aegis-storage` | `goal_create`, `goal_list`, `intercept_create` | 无 |
| P2 | `aegis-perception` | `get_active_app`, `get_current_wifi` | Phase 2 |
| P2 | `aegis-storage` | `profile_create`, `profile_list`, `profile_get_active` | Phase 2 |
| P2 | `aegis-intervention` | `set_pet_emotion`, `activate_profile` | Phase 2 |
| P3 | `aegis-device` | 全部 | Phase 3 |
| P3 | `aegis-perception` | Android 扩展 | Phase 3 |
| P3 | `aegis-intervention` | Android 扩展 | Phase 3 |

---

## 十、与原设计文档的对照表

| 原设计章节 | 原内容 | 本评估调整 |
|-----------|--------|-----------|
| 3.4 Phase 1 MCP 工具清单 | 只列 Intervention（11）+ Perception（2） | 补充 Storage（9）+ Scheduler（4），Perception 纳入 Phase 1 |
| 3.5 Phase 1 架构 | Intervention MCP Server（自研，Rust） | 明确为 4 个 Server：intervention, perception, storage, scheduler |
| 5.4 Phase 2 新增 MCP | Perception（3）+ Intervention（3） | 补充 Storage（6）+ Scheduler（2） |
| — | 未提及 | 新增 `aegis-device` Server（Phase 3） |

---

## 十一、下一步行动

1. **确认本评估**：是否有遗漏的业务场景需要额外 MCP？
2. **细化接口**：选择优先级最高的 P0 MCP，输出详细的 JSON Schema + 错误码定义
3. **技术选型确认**：`aegis-intervention` 和 `aegis-perception` 用 Rust 无异议；`aegis-storage` 是否也用 Rust（rusqlite）还是嵌入在应用层？
4. **开始实现**：建议从 `aegis-storage` + `aegis-scheduler` 开始，因为 intervention 需要它们提供数据才能测试完整闭环。
