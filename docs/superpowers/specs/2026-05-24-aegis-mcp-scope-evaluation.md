# Aegis MCP 开发范围评估

**日期**：2026-05-24  
**输入依据**：`docs/superpowers/specs/2026-05-05-aegis-personal-life-assistant-design.md`  
**结论版本**：v0.1

---

## 一、评估结论

按现有设计，Aegis 的 MCP 不应该一开始拆成很多服务。Phase 1 的目标是跑通“微信对话 → 目标拆解 → 今日计划 → 五级提醒 → 反馈记录 → 次日复盘”的闭环，核心开发应收敛为 **2 个 P0 MCP Server**：

1. **Aegis Core MCP**：负责目标、计划、任务、提醒、反馈、执行历史等领域数据。
2. **Aegis Intervention MCP**：负责 Windows 本地提醒、弹窗、声音、遮罩、全屏阻断、锁屏等出口能力。

另外，Phase 1 还需要一个微信入口/出口适配能力。它可以先不做成独立 MCP Server，而是以 Hermes 已有入口、Webhook、脚本适配器或 Core MCP 的轻量工具形式接入。等消息通道稳定后，再独立为 **Aegis Messaging MCP**。

Phase 2 开始再新增 Profile、Perception、Desktop Client Bridge。Phase 3 再新增 Android Control / Android Perception。这样能避免第一阶段被设备感知、跨端同步、Profile 状态机拖慢。

从 Hermes 生态的职责边界看，Aegis 不应该把所有能力都做成 MCP。更合理的拆法是：**Skills 定义 Hermes 怎么想、怎么判断、怎么对话；MCP 负责读写真正的状态、执行系统动作、保存可审计事实。**

---

## 二、Skills 与 MCP 职责拆分

### 2.1 判断原则

```text
只影响 Hermes 怎么想、怎么说、怎么决策
  -> 做成 Skill

需要读写数据库、调用系统、触发通知、收集反馈、产生副作用、保证可审计
  -> 做成 MCP
```

Skills 是“脑内规则”和“决策流程”。它们适合描述目标怎么拆、计划怎么改、提醒怎么升级、复盘怎么说。MCP 是“外部工具”和“事实系统”。它们适合保存任务、查到期提醒、弹出窗口、播放声音、锁屏、记录用户反馈。

如果把强提醒、任务记录、反馈收集都写进 Skills，会出现状态不稳定、动作不可验证、调度不可控、无法审计的问题。反过来，如果把目标拆解、拦截话术、复盘表达都写进 MCP，又会把 MCP 做成另一个大脑，和“Hermes 是大脑，我们只做入口和出口”的定位冲突。

### 2.2 Phase 1 可以拆成 Skills 的部分

| Skill | 优先级 | 职责 | 不负责 |
|-------|--------|------|--------|
| `aegis_goal_planner` | P0 | 把自然语言目标拆成长期目标、短期目标、今日任务、反馈要求 | 不直接写数据库、不调弹窗 |
| `aegis_reminder_policy` | P0 | 定义 L1-L5 通知强度升级和反馈方式升级策略 | 不自己计时、不自己执行提醒 |
| `aegis_plan_change_interceptor` | P0 | 处理“今晚计划要调整”这类请求，执行多层追问、影响评估、替代方案 | 不直接改任务状态，只输出结构化调整意图 |
| `aegis_daily_review` | P0 | 基于 Core MCP 的执行摘要生成昨日复盘、今日建议 | 不直接推断未记录事实 |
| `aegis_feedback_validator` | P1 | 判断用户提交的文字/图片/位置反馈是否满足任务要求 | 不保存附件、不管理文件 |
| `aegis_message_style` | P1 | 统一 Aegis 的提醒语气、追问风格、复盘表达 | 不参与系统动作 |

Phase 1 最小 Skills 集合建议先做 4 个：

```text
1. aegis_goal_planner
2. aegis_reminder_policy
3. aegis_plan_change_interceptor
4. aegis_daily_review
```

`aegis_feedback_validator` 可以先并入 `aegis_reminder_policy` 或由 Hermes 主提示词约束，等图片、位置等反馈真的接入后再独立。

### 2.3 Phase 1 必须做成 MCP 的部分

| MCP | 优先级 | 职责 | 原因 |
|-----|--------|------|------|
| Aegis Core MCP | P0 | 目标、计划、任务、提醒、反馈、执行历史、复盘摘要 | 需要稳定存储和结构化查询 |
| Aegis Intervention MCP | P0 | Windows 通知、弹窗、提示音、输入框、倒计时遮罩、全屏阻断、锁屏 | 需要调用系统能力并产生真实副作用 |
| Messaging / WeChat Adapter | P0 | 微信入口、L1 微信提醒、用户回复与任务关联 | Phase 1 主要入口和轻提醒通道 |
| Basic Context Tools | P1 | 当前时间、日期、PC 在线状态、执行器状态 | Hermes 决策需要事实上下文 |

其中 `Basic Context Tools` 不需要单独成为 Server，可以先放进 Core MCP 或 Intervention MCP。微信适配也不必第一天 MCP 化，可以先用 Hermes 既有入口、Webhook 或脚本适配器。

### 2.4 Phase 2 可以拆成 Skills 的部分

| Skill | 优先级 | 职责 |
|-------|--------|------|
| `aegis_profile_policy` | P0 | 解释 Profile 的行为模式、冲突取舍、用户确认话术 |
| `aegis_profile_rule_generator` | P1 | 把用户配置或自然语言规则转换成 Hermes 可理解的规则草稿 |
| `aegis_focus_mode_coach` | P1 | 专注、假期、夜间等模式下的建议策略和提醒文案 |

Phase 2 的 Profile UI、Profile 数据、激活状态和冲突候选仍然应该由 Profile MCP 管。Skill 只负责“怎么解释和怎么决策”，不负责保存 Profile。

### 2.5 Phase 2 必须做成 MCP 的部分

| MCP | 优先级 | 职责 |
|-----|--------|------|
| Aegis Profile MCP | P0 | Profile CRUD、激活/停用、冲突候选、规则导出 |
| Aegis Perception MCP | P0 | 当前 App、窗口、进程、WiFi、空闲时长 |
| Desktop Bridge MCP / WebSocket Bridge | P1 | 桌宠状态、快捷按钮、计划中心展示 |

Perception 必须是 MCP，因为它读的是系统事实。Profile 数据也必须是 MCP，因为它需要持久化和可编辑。Skill 可以参与解释冲突，但不能作为唯一状态源。

### 2.6 Phase 3 可以拆成 Skills 的部分

| Skill | 优先级 | 职责 |
|-------|--------|------|
| `aegis_cross_device_policy` | P1 | 决定 PC 与 Android 同时在线时提醒优先落在哪端 |
| `aegis_mobile_intervention_policy` | P1 | 判断移动端提醒是否升级到悬浮窗、遮罩、强提醒 |
| `aegis_location_feedback_policy` | P1 | 解释位置反馈是否满足任务要求 |

### 2.7 Phase 3 必须做成 MCP 的部分

| MCP | 优先级 | 职责 |
|-----|--------|------|
| Android Control MCP | P0 | Android 通知、弹窗、悬浮球、遮罩、拍照、位置、App 控制 |
| Android Perception MCP | P0 | 前台 App、WiFi、屏幕状态、设备状态、使用记录 |
| Device Sync 查询工具 | P1 | 设备列表、设备状态、Profile 同步状态 |

Android 能力不能只靠 Skill，因为它涉及系统权限、Accessibility、前台 App 读取、系统遮罩和本地服务。

### 2.8 推荐执行链路

以“20:00 饮食打卡提醒”为例，推荐链路是：

```text
Hermes + aegis_reminder_policy Skill
  -> 判断当前应该触发 L1
  -> Core MCP: list_due_reminders
  -> Intervention MCP: show_notification
  -> Messaging Adapter: send_wechat_message
  -> Core MCP: record_intervention_event

60 秒无反馈
  -> Hermes + aegis_reminder_policy Skill 判断升级到 L2
  -> Intervention MCP: show_popup
  -> Core MCP: record_intervention_event

用户提交反馈
  -> Intervention MCP / Messaging Adapter 收集反馈
  -> Hermes + aegis_feedback_validator Skill 判断是否有效
  -> Core MCP: record_feedback
  -> Core MCP: complete_task
```

这个链路里，Skill 每次只负责判断和生成结构化意图；MCP 负责执行和保存事实。

---

## 三、分阶段 MCP 总览

| 阶段 | MCP / 能力模块 | 优先级 | 是否独立 Server | 主要原因 |
|------|----------------|--------|-----------------|----------|
| Phase 1 | Aegis Core MCP | P0 | 是 | 计划、任务、反馈、复盘都需要稳定结构化数据 |
| Phase 1 | Aegis Intervention MCP | P0 | 是 | Windows 强提醒能力有系统权限和 UI 执行边界 |
| Phase 1 | Messaging / WeChat Adapter | P0 | 暂不强制 | 微信是入口和 L1 通知通道，但实现方式取决于 Hermes/微信接入方案 |
| Phase 1 | Basic Context Tools | P1 | 否 | 时间、日期、PC 在线状态可先放 Core 或 Intervention 内 |
| Phase 2 | Aegis Profile MCP | P0 | 是 | Profile CRUD、激活、冲突检测、规则生成是独立领域 |
| Phase 2 | Aegis Perception MCP | P0 | 是 | 当前 App、进程、WiFi 等属于感知权限边界 |
| Phase 2 | Desktop Bridge MCP | P1 | 可选 | 桌宠表情、计划中心、快捷按钮可先走 WebSocket，必要时再 MCP 化 |
| Phase 3 | Android Control MCP | P0 | 是 | Android 遮罩、通知、悬浮球、强制能力和 Windows 完全不同 |
| Phase 3 | Android Perception MCP | P0 | 可并入 Android Control | 前台 App、WiFi、位置、系统状态需要移动端采集 |
| Phase 3 | Device Sync MCP | P1 | 可选 | 跨端状态同步更适合 WebSocket/gRPC，Hermes 只需要查询状态 |
| Phase 4+ | Analytics / Memory Adapter MCP | P1 | 视 Hermes 能力而定 | 服从率、逃避模式、个性化统计若 Hermes 记忆不够再自研 |
| Phase 4+ | Rule Engine MCP | P1 | 视延迟要求而定 | 硬规则、低延迟拦截、Profile 状态机成熟后再拆 |

---

## 四、Phase 1 推荐开发范围

### 4.1 Aegis Core MCP

**定位**：Aegis 的领域数据层，对 Hermes 暴露“可被调用的生活管理 API”。

Hermes 负责理解、拆解和决策，Core MCP 负责把结果落地为可查询、可更新、可复盘的数据。没有这个 MCP，提醒执行后很难稳定回答“昨天执行得怎么样”“这个任务是否已经反馈”“计划调整后提醒是否重排”。

**建议技术选型**：

- 初期：Python + FastMCP + SQLite，便于快速验证工具协议和数据结构。
- 若后续要和 Rust Intervention 共用模型，可再迁移为 Rust 或拆出独立 SQLite schema。

**核心工具建议**：

```text
create_goal(title, description?, target_date?, metadata?)
update_goal(goal_id, fields)
list_goals(status?, date_range?)

create_daily_plan(date, goal_id?, tasks[])
get_daily_plan(date)
update_daily_plan(plan_id, changes)

create_task(plan_id?, title, scheduled_time?, required_feedback, escalation_policy?)
list_tasks(date?, status?)
update_task(task_id, fields)
complete_task(task_id, feedback_id?)
skip_task(task_id, reason)

schedule_reminder(task_id, scheduled_time, escalation_policy)
reschedule_reminder(reminder_id, scheduled_time)
cancel_reminder(reminder_id)
list_due_reminders(now?)

record_feedback(task_id, feedback_type, content_ref?, text?, metadata?)
validate_feedback(task_id, feedback_id)

record_intervention_event(task_id?, reminder_id?, level, channel, result, metadata?)
get_execution_summary(date)
get_task_history(goal_id?, date_range?)
```

**最小可用闭环**：

```text
create_task
list_tasks
schedule_reminder
record_feedback
complete_task
record_intervention_event
get_execution_summary
```

**不建议 Phase 1 放入的内容**：

- Profile 状态机。
- App/WiFi 感知规则。
- 自适应学习和服从率模型。
- Hermes Skill 自动生成。

这些会把 Core MCP 从“领域数据 API”变成“大脑替代品”，和现有设计的“Phase 1 不动 Hermes 内部”冲突。

### 4.2 Aegis Intervention MCP

**定位**：Aegis 的 Windows 出口执行器，专注做 Hermes 和系统 UI/强提醒能力之间的安全隔离层。

它只关心“执行什么提醒动作”和“用户如何响应”，不负责理解目标、不负责长期记忆、不负责计划拆解。

**建议技术选型**：

- Rust 优先：更适合 Windows 原生窗口、置顶、全屏、锁屏、声音播放、进程生命周期管理。
- MCP 包装层可用 Rust 原生 MCP SDK，或先用 Python MCP Server 调用 Rust sidecar。若 Phase 1 时间紧，推荐“Python MCP + Rust 执行器”过渡。

**核心工具建议**：

```text
show_notification(title, body, urgency?)
show_popup(title, message, buttons?, timeout_seconds?, always_on_top?)
play_sound(sound_type, repeat?, volume?)

request_text_input(prompt, timeout_seconds?)
request_choice_input(prompt, options, timeout_seconds?)
request_photo_input(prompt, timeout_seconds?)
request_location_input(prompt, timeout_seconds?)

show_countdown_overlay(message, seconds, required_feedback?)
show_fullscreen_block(message, required_feedback, unblock_policy?)
lock_screen(duration_seconds?)

dismiss_intervention(intervention_id, reason?)
get_intervention_status(intervention_id)
```

**对应 Phase 1 五级提醒**：

| 等级 | Intervention MCP 工具组合 |
|------|---------------------------|
| L1 | `show_notification`，以及微信消息适配器 |
| L2 | `show_notification` + `show_popup` |
| L3 | `show_popup(always_on_top=true)` + `play_sound` + 输入类工具 |
| L4 | `show_countdown_overlay` + 输入类工具 |
| L5 | `show_fullscreen_block`，必要时 `lock_screen` |

**关键约束**：

- 所有强制类工具必须返回可审计结果，包括开始时间、结束时间、用户是否提交反馈、是否超时。
- L5 工具必须留开发者逃生口，例如本地调试密钥、环境变量开关或安全模式，否则开发测试风险很高。
- UI 执行器不直接写长期计划数据，只把结果回传给 Core MCP 或 Hermes。

### 4.3 Messaging / WeChat Adapter

**定位**：连接微信入口和 L1 消息出口。

现有设计把微信作为 Phase 1 的主要用户入口，同时 L1 也包含微信消息。因此这个能力必需存在，但不一定第一天就做成 MCP Server。

**三种实现路径**：

| 方案 | 做法 | 优点 | 缺点 | 建议 |
|------|------|------|------|------|
| 复用 Hermes 已有入口 | 使用 Hermes 支持的聊天入口或已有插件 | 开发量最小 | 受 Hermes 支持范围限制 | 首选 |
| Webhook 适配器 | 自建 HTTP/Webhook，把消息转给 Hermes | 可控，易调试 | 需要处理微信侧接入 | 可作为 Phase 1 方案 |
| 独立 Messaging MCP | `send_message/get_message_status` 等工具化 | 边界清晰 | 早期拆分成本偏高 | Phase 1 后半或 Phase 2 |

**若独立 MCP 化，工具建议**：

```text
send_wechat_message(to, message, mention?)
send_wechat_template(to, template_id, variables)
get_message_delivery_status(message_id)
record_inbound_message(source, sender, text, attachments?)
```

### 4.4 Basic Context Tools

原设计中提到 `get_current_time()` 和 `get_system_state()`，但又明确写了 Phase 1 不需要 Perception MCP。建议 Phase 1 不单独拆 Perception MCP，而是将这些工具作为 Core 或 Intervention 的基础工具。

**工具建议**：

```text
get_current_time()
get_system_state()
```

**边界**：

- `get_current_time` 是基础上下文，不属于真正的感知。
- `get_system_state` Phase 1 只返回 PC 在线、屏幕状态、Intervention 执行器是否可用。
- 当前 App、进程、WiFi、截图等延后到 Phase 2 Perception MCP。

---

## 五、Phase 2 推荐新增 MCP

### 5.1 Aegis Profile MCP

**定位**：管理 Profile 的创建、激活、冲突处理和规则绑定。

Profile 是 Phase 2 的独立领域，不应塞进 Core MCP。Core 关心任务和计划，Profile 关心场景规则和系统行为模式。

**核心工具建议**：

```text
create_profile(name, icon?, activation_conditions, rules, reminder_channels)
update_profile(profile_id, fields)
delete_profile(profile_id)
list_profiles(active_only?)

activate_profile(profile_id, reason?)
deactivate_profile(profile_id, reason?)
get_current_profiles()
resolve_profile_conflict(profile_ids, strategy?)

preview_profile_effect(profile_id, context?)
export_profile_as_hermes_skill(profile_id)
```

**注意**：`export_profile_as_hermes_skill` 可以先只生成 YAML 草稿，不要在 Phase 2 一开始就自动热加载，避免规则错误直接影响用户系统。

### 5.2 Aegis Perception MCP

**定位**：采集 Windows 环境状态，为 Profile 自动激活和行为判断提供事实输入。

**核心工具建议**：

```text
get_active_app()
get_active_window()
get_running_processes()
get_current_wifi()
get_idle_duration()
get_screen_state()
```

**Phase 2 暂不建议做**：

- 屏幕 OCR。
- 截图 + VLM 分析。
- 键盘鼠标细粒度监听。
- 浏览器页面语义分析。

这些能力隐私风险和误判成本高，应该等基础闭环稳定后再加。

### 5.3 Desktop Bridge MCP / WebSocket Bridge

**定位**：连接 Tauri 桌宠、计划中心、快捷按钮和 Hermes。

桌宠本质是交互入口和状态展示，不一定需要 MCP。更自然的方式是：

```text
Tauri 桌宠  <->  Aegis 本地 WebSocket/Gateway  <->  Hermes/Core MCP
```

只有当 Hermes 需要主动控制桌宠状态时，才暴露少量工具：

```text
set_pet_emotion(type)
show_plan_center(date?)
show_profile_switcher()
push_desktop_state(state)
```

---

## 六、Phase 3 推荐新增 MCP

### 6.1 Android Control MCP

**定位**：Android 端执行器，对应 Windows Intervention MCP，但权限模型、UI 实现和系统能力完全不同，因此建议独立。

**核心工具建议**：

```text
show_android_notification(title, body, urgency?)
show_android_popup(title, message, buttons?)
show_android_overlay(message, required_feedback?)
show_android_countdown_overlay(message, seconds)
show_android_fullscreen_block(message, required_feedback)

get_android_location()
request_android_photo(prompt)
request_android_choice(prompt, options)

set_floating_ball_state(state)
force_stop_app(package_name)
open_app(package_name)
```

### 6.2 Android Perception MCP

**定位**：采集 Android 当前 App、WiFi、位置、通知状态等。

它可以和 Android Control MCP 同进程部署，但工具边界应分开，避免“感知”和“控制”混在一起后难以授权。

**核心工具建议**：

```text
get_foreground_app()
get_android_wifi()
get_android_screen_state()
get_android_device_state()
get_recent_app_usage(duration_minutes?)
```

### 6.3 Device Sync

跨设备同步更适合 WebSocket/gRPC，不建议强行做成 MCP 主链路。MCP 工具只需要给 Hermes 查询或设置跨端状态：

```text
list_devices()
get_device_status(device_id)
set_device_profile(device_id, profile_id)
broadcast_state_update(state)
```

---

## 七、Phase 4+ 视情况新增

### 7.1 Analytics / Memory Adapter MCP

当 Hermes 自带记忆无法高效回答以下问题时，再新增：

- 某类任务最近 30 天完成率。
- 某个提醒等级的服从率。
- 用户在哪些时间段最容易拖延。
- 哪些文案或干预组合最有效。
- 计划调整后的恢复率。

**工具建议**：

```text
get_compliance_stats(date_range, group_by?)
get_intervention_effectiveness(level?, channel?, date_range?)
detect_user_patterns(date_range?)
get_goal_progress(goal_id)
```

### 7.2 Rule Engine MCP

当 Profile 规则、硬拦截规则和低延迟判断变复杂后，再从 Profile MCP 或 Core MCP 中拆出。

**工具建议**：

```text
evaluate_rules(context)
create_rule(rule)
update_rule(rule_id, fields)
enable_rule(rule_id)
disable_rule(rule_id)
simulate_rules(context)
```

---

## 八、推荐的 Server 拆分原则

### 8.1 按权限边界拆

有系统权限、强制 UI、锁屏、App 控制的能力要独立，例如 Intervention MCP 和 Android Control MCP。这样可以单独做安全开关、日志审计和崩溃隔离。

### 8.2 按数据领域拆

目标、任务、反馈、提醒历史属于 Core MCP。Profile 属于 Profile MCP。不要因为工具数量多就拆 Server，要看领域边界是否稳定。

### 8.3 按设备平台拆

Windows 和 Android 的系统 API、权限申请、失败模式完全不同，不建议放在同一个 MCP Server 里。

### 8.4 早期少拆，接口先稳

Phase 1 最重要的是让 Hermes 能稳定调用工具并形成闭环。建议先合并实现以下轻量能力：

```text
Aegis Core MCP:
  - 计划/任务/反馈/执行历史
  - get_current_time

Aegis Intervention MCP:
  - Windows 通知/弹窗/声音/遮罩/全屏阻断
  - get_system_state

Messaging Adapter:
  - 微信入口
  - 微信 L1 消息
```

---

## 九、Phase 1 最小开发清单

如果只看第一阶段，建议按下面顺序开发：

1. **Core MCP 数据模型**
   - `goals`
   - `daily_plans`
   - `tasks`
   - `reminders`
   - `feedbacks`
   - `intervention_events`

2. **Core MCP 最小工具**
   - `create_task`
   - `list_tasks`
   - `schedule_reminder`
   - `list_due_reminders`
   - `record_feedback`
   - `complete_task`
   - `record_intervention_event`
   - `get_execution_summary`

3. **Intervention MCP 最小工具**
   - `show_notification`
   - `show_popup`
   - `play_sound`
   - `request_text_input`
   - `show_countdown_overlay`
   - `show_fullscreen_block`
   - `lock_screen`

4. **微信适配**
   - 用户消息进入 Hermes。
   - Hermes 或工具可发送 L1 微信提醒。
   - 微信回复可关联到 `task_id` 或当前待反馈任务。

5. **升级调度闭环**
   - 到点查询 due reminder。
   - 未反馈时每 60 秒升级。
   - 每次升级记录 `intervention_event`。
   - 收到有效反馈后停止升级并完成任务。

---

## 十、关键接口边界

### 10.1 Hermes、Skills 与 MCP 的职责分工

| 职责 | Hermes 主体 | Skills | MCP |
|------|-------------|--------|-----|
| 理解用户自然语言 | 是 | 提供领域规则 | 否 |
| 拆解目标和生成计划 | 是 | 定义拆解方法和输出格式 | 只存储结果 |
| 选择提醒策略 | 是 | 定义升级规则 | 可校验策略合法性 |
| 执行通知/弹窗/遮罩 | 否 | 否 | 是 |
| 收集反馈证明 | 否 | 可判断反馈是否满足要求 | 是 |
| 记录执行事实 | 可发起 | 否 | 是 |
| 次日复盘表达 | 是 | 定义复盘结构和语气 | 提供结构化统计 |
| Profile 冲突决策 | 是 | 定义冲突决策原则 | 提供候选和规则结果 |

### 10.2 Core MCP 与 Intervention MCP 的职责分工

```text
Core MCP:
  记录“应该做什么、什么时候做、结果如何”

Intervention MCP:
  执行“现在怎么提醒、怎么阻断、用户如何响应”
```

一次提醒的推荐链路：

```text
Hermes / Scheduler
  -> Core MCP: list_due_reminders
  -> Intervention MCP: show_popup / overlay / fullscreen
  -> Core MCP: record_intervention_event
  -> Core MCP: record_feedback / complete_task
```

---

## 十一、主要风险与处理建议

| 风险 | 影响 | 建议 |
|------|------|------|
| MCP 数量过多 | Phase 1 集成成本高，调试困难 | 第一阶段只做 Core + Intervention |
| 强制 UI 误触发 | 用户体验和系统安全风险高 | L4/L5 增加开发者逃生口和测试模式 |
| 微信接入不稳定 | Phase 1 主入口受阻 | 预留 CLI/Webhook 备用入口 |
| 全部做成 Skills | 状态不可审计，真实动作不可验证 | Skills 只写策略，状态和动作必须落到 MCP |
| 全部做成 MCP | MCP 变成另一个大脑，复杂度失控 | 目标拆解、话术、策略保留在 Skills |
| Hermes 工具调用不稳定 | 计划和提醒状态不一致 | Core MCP 工具幂等化，所有写操作返回结构化状态 |
| 反馈附件存储混乱 | 照片/位置/文字难以复盘 | Core 只存 `content_ref`，二进制附件放文件或对象存储 |
| 调度权不清 | Hermes Cron、Core due reminder、Intervention timer 互相冲突 | Phase 1 明确只保留一个升级调度 owner |

---

## 十二、建议的阶段性目标

### M1：工具可调用

- Hermes 能调用 Core MCP 创建任务。
- Hermes 能调用 Intervention MCP 弹出系统通知。
- 所有工具返回统一 `{ ok, data, error }` 风格结果。

### M2：提醒可升级

- Core MCP 能查询到期提醒。
- Intervention MCP 能执行 L1-L5。
- 忽略提醒后能每 60 秒升级一次。

### M3：反馈可闭环

- 文本反馈和确认反馈能关联任务。
- 至少一种附件反馈能落库，例如照片路径或模拟照片。
- 任务完成后升级停止。

### M4：复盘可回答

- Core MCP 能返回昨日执行摘要。
- Hermes 能基于摘要回答“昨天执行得怎么样”。

---

## 十三、最终推荐

现阶段不要按“所有可能能力”一次性规划成 8 到 10 个 MCP Server，也不要把所有东西都塞进 Skills。推荐采用“Skills 管策略，MCP 管事实和动作”的演进顺序：

```text
Phase 1:
  Skills:
    1. aegis_goal_planner
    2. aegis_reminder_policy
    3. aegis_plan_change_interceptor
    4. aegis_daily_review

  MCP / Adapter:
    1. Aegis Core MCP
    2. Aegis Intervention MCP
    3. Messaging / WeChat Adapter

Phase 2:
  Skills:
    5. aegis_profile_policy
    6. aegis_profile_rule_generator

  MCP / Bridge:
    4. Aegis Profile MCP
    5. Aegis Perception MCP
    6. Desktop Bridge MCP 或 WebSocket Bridge

Phase 3:
  Skills:
    7. aegis_cross_device_policy
    8. aegis_mobile_intervention_policy

  MCP:
    7. Android Control MCP
    8. Android Perception MCP
    9. Device Sync 查询工具

Phase 4+:
  MCP:
    10. Analytics / Memory Adapter MCP
    11. Rule Engine MCP
```

其中真正需要马上开发的是 **4 个 Phase 1 Skills + Core MCP + Intervention MCP**。Skills 让 Hermes 按 Aegis 的产品逻辑思考和表达；两个 MCP 让 Aegis 有可运行的计划数据、提醒执行、反馈记录和复盘基础。Profile、感知、Android、规则引擎都应该建立在这个闭环之上。
