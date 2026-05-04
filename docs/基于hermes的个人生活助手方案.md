
**方案代号：Aegis-Hermes（赫耳墨斯之盾）**  
**定位**：基于 Hermes Agent 框架的个人强干预数字管家系统  
**核心原则**：**不造轮子，只造接口**——所有认知、记忆、决策、技能生成全部委托 Hermes，自研部分只做三件事：**感知探头、干预肌肉、交互皮肤**。

---

## 一、方案边界与假设

| 维度 | 设定 |
|------|------|
| **宿主平台** | Windows 11（x64）为主脑；Android（Root，API 33+）为感官/手 |
| **网络拓扑** | 局域网主从，可离线运行，无外网依赖 |
| **AI 大脑** | Hermes Agent（本地 Ollama/Qwen 或远程 API），通过 MCP 调用工具 |
| **干预强度** | 系统级：弹窗置顶、进程冻结、屏幕锁定、App 强杀、全屏遮罩 |
| **现实惩罚** | 邮件/IM Webhook（不可撤销）、社会问责（老婆/朋友） |
| **自研范围** | 3 个 MCP Server + 2 个客户端壳子 + 1 套规则 DSL |
| **Hermes 范围** | 决策 Agent、记忆 Agent、计划 Agent、技能 Agent、网关 |

---

## 二、总架构：洋葱模型

```
┌──────────────────────────────────────────────────────────────────────┐
│                        L5 交互层（自研）                              │
│   Win桌宠(Tauri)  │  Win弹窗(Rust)  │  Android悬浮球(Flutter)        │
│   └───────────────┴─────────────────┴──────────────────────────────┘ │
│                              ↑↓                                      │
│   协议：WebSocket / gRPC（局域网）                                     │
├──────────────────────────────────────────────────────────────────────┤
│                        L4 网关层（Hermes 自带）                        │
│   Hermes Gateway：WebSocket Server / mDNS 发现 / 设备心跳              │
├──────────────────────────────────────────────────────────────────────┤
│                        L3 认知层（Hermes 自带）                        │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐  │
│   │  决策Agent   │ │  记忆Agent   │ │  技能Agent   │ │  计划Agent    │  │
│   │  ReAct Loop │ │ SQLite+Vec  │ │ Auto-Skill  │ │  Cron/Trig   │  │
│   └─────────────┘ └─────────────┘ └─────────────┘ └──────────────┘  │
│                              ↑↓                                      │
│   协议：MCP (Model Context Protocol)                                  │
├──────────────────────────────────────────────────────────────────────┤
│                        L2 工具层（自研 MCP Server）                    │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐  │
│   │ Intervention│ │ Perception  │ │ Notification│ │ AndroidCtl   │  │
│   │  干预工具    │ │  感知工具    │ │  通知工具    │ │ 安卓控制      │  │
│   └─────────────┘ └─────────────┘ └─────────────┘ └──────────────┘  │
│                              ↑↓                                      │
│   调用：Win32 API / Android ADB+Root / SMTP / Webhook                 │
├──────────────────────────────────────────────────────────────────────┤
│                        L1 系统层（OS 原生能力）                        │
│   Windows (user32/kernel32) │ Android (Accessibility/LSPosed/Shell)  │
└──────────────────────────────────────────────────────────────────────┘
```

**关键设计**：Hermes 位于核心，自研模块像插件一样挂在它的 MCP 总线上。未来替换任何一个模块（比如把 Win 弹窗换成 Mac 弹窗），Hermes 零感知。

---

## 三、模块职责矩阵：Hermes 自带 vs 自研

### 3.1 Hermes 自带（零开发，只配置）

| 模块 | 职责 | 配置方式 |
|------|------|----------|
| **决策 Agent** | 接收感知事件 → 查询记忆 → 决策是否干预 → 选择工具组合 | 写 System Prompt + Skill 文件 |
| **记忆 Agent** | 存储干预历史、用户服从率、逃避借口、有效文案；支持语义检索 | 自动使用 SQLite + 向量扩展 |
| **技能 Agent** | 根据历史数据自动生成新 Skill（如发现"用户每次周二下午都逃避"，自动生成周二强化规则） | 开启 `auto_skill_generation: true` |
| **计划 Agent** | Cron 定时触发检查；支持动态调整（如"每工作 25 分钟检查一次，连续逃逸后缩短到 5 分钟"） | Skill 中写 `triggers.cron` |
| **网关 Agent** | 接收来自 Win/Android 的消息，统一路由到决策 Agent | `hermes gateway add websocket` |

### 3.2 自研（必须自己写）

| 模块 | 职责 | 技术选型 |
|------|------|----------|
| **Intervention MCP** | 提供弹窗、锁屏、杀进程、倒计时遮罩等工具 | Python + `fastmcp` / Rust + `rmcp` |
| **Perception MCP** | 提供"当前活跃窗口/进程/App/屏幕内容"等感知数据 | Rust（Win）+ Kotlin（Android） |
| **Notification MCP** | 提供邮件、Webhook、短信发送能力 | Python `smtplib` / `httpx` |
| **AndroidCtl MCP** | 提供 Android 端的悬浮窗、全屏遮罩、ForceStop、截屏 | Kotlin Service + ADB Bridge |
| **Win 客户端** | 桌宠渲染、全局热键、弹窗宿主 | Tauri 2.0（Rust + Webview） |
| **Android 客户端** | 悬浮球、后台保活、系统遮罩、与 PC 通信 | Flutter + Kotlin Plugin |

---

## 四、标准化数据流：一条干预的完整生命周期

以 **"用户工作时间打开抖音"** 为例：

```
[Android 系统]
    │
    ▼
[Perception MCP ← Android Accessibility/LSPosed]
    读取前台 App：com.ss.android.ugc.aweme
    封装为 MCP Tool Result → 推送给 Hermes
    │
    ▼
[Hermes 网关 Agent]
    收到事件：{device: "android-node-1", event: "app_launched", target: "douyin"}
    路由给决策 Agent
    │
    ▼
[Hermes 决策 Agent]
    1. 调用记忆 Agent：查询今日逃避次数 → 返回 2
    2. 调用计划 Agent：查询当前是否处于免疫期 → 返回 false
    3. 调用规则引擎：匹配规则 "工作时间禁止娱乐 App" → 命中
    4. 决策：触发 Level-3 干预（倒计时遮罩 + 邮件预警）
    │
    ▼
[Hermes 通过 MCP 调用工具]
    并行调用：
    ├── AndroidCtl MCP: show_blocking_overlay(duration=60, message="...")
    ├── Notification MCP: send_email(to="wife@xxx.com", template="escape_alert")
    └── Intervention MCP(Win): set_pet_emotion("angry")  [桌宠同步生气]
    │
    ▼
[各端执行]
    Android：全屏遮罩，60 秒倒计时，不可返回
    邮件：Resend/SMTP 发送报告（异步，不可撤销）
    Win桌宠：Live2D 切换愤怒表情
    │
    ▼
[用户操作]
    用户等待 60 秒 → 遮罩消失 → 打开抖音
    │
    ▼
[Perception MCP]
    再次检测到抖音前台
    推送事件给 Hermes
    │
    ▼
[Hermes 决策 Agent]
    记忆显示：同一行为 3 分钟内第 2 次
    升级策略：Level-4（ForceStop + 锁屏 5 分钟 + 邮件已发送无需重复）
    │
    ▼
[AndroidCtl MCP]
    am force-stop com.ss.android.ugc.aweme
    show_lock_screen(duration=300)
```

**关键**：Hermes 在整个链路中只做**决策编排**，不动系统。所有"脏活"（Hook、弹窗、杀进程）由 MCP Server 完成。

---

## 五、入口矩阵（Input Surface）

所有入口统一封装为 MCP Tool 或 WebSocket Message，Hermes 无差别消费。

| 入口 ID | 名称 | 触发源 | 接入 Hermes 方式 | 优先级 |
|---------|------|--------|-----------------|--------|
| `IN-01` | **语音唤醒** | 用户主动 | Win: Porcupine 本地唤醒 → 音频流 → Hermes STT Skill | P0 |
| `IN-02` | **全局热键** | 用户主动 | Win: `RegisterHotKey` → WebSocket → Hermes Gateway | P0 |
| `IN-03` | **桌宠交互** | 用户主动 | Tauri 窗口点击/语音 → WebSocket → Hermes | P0 |
| `IN-04` | **悬浮球点击** | 用户主动 | Flutter → WebSocket → Hermes | P0 |
| `IN-05` | **定时心跳** | 系统被动 | Hermes 计划 Agent Cron → 触发 Perception MCP 扫描 | P1 |
| `IN-06` | **行为检测** | 环境被动 | Perception MCP 轮询（Win 500ms / Android 事件驱动）→ 推 Hermes | P1 |
| `IN-07` | **屏幕视觉** | 环境被动 | Perception MCP 截屏 → Base64 → 可选 VLM 分析 | P2 |
| `IN-08` | **外部 Webhook** | 第三方 | 本地 HTTP Server → Hermes Gateway | P2 |
| `IN-09` | **邮件/消息回执** | 第三方 | IMAP 轮询/回调 → Hermes Gateway | P3 |

**扩展设计**：新增入口只需实现一个 WebSocket Client 或 MCP Tool，向 Hermes 发送标准事件 JSON，无需改 Hermes 核心。

---

## 六、出口矩阵（Output Surface）

所有出口由 Hermes 通过 MCP 调用，支持**链式编排**。

| 出口 ID | 名称 | 目标 | 强度 | MCP Server | 工具名 | 可撤销性 |
|---------|------|------|------|-----------|--------|----------|
| `OUT-01` | 边缘提醒 | Win/Android | ★☆☆☆☆ | Intervention / AndroidCtl | `show_toast` | 自动 |
| `OUT-02` | 桌宠表情 | Win | ★☆☆☆☆ | Intervention | `set_pet_emotion` | 用户主动 |
| `OUT-03` | 居中弹窗 | Win/Android | ★★☆☆☆ | Intervention / AndroidCtl | `show_popup` | 单次点击 |
| `OUT-04` | 理由输入窗 | Win/Android | ★★★☆☆ | Intervention / AndroidCtl | `show_blocking_input` | 认知成本 |
| `OUT-05` | 倒计时遮罩 | Win/Android | ★★★★☆ | Intervention / AndroidCtl | `show_countdown_overlay` | 时间成本 |
| `OUT-06` | 进程冻结 | Win | ★★★★☆ | Intervention | `suspend_process` | 需恢复 |
| `OUT-07` | App 强杀 | Android | ★★★★☆ | AndroidCtl | `force_stop_app` | 需手动重开 |
| `OUT-08` | 屏幕锁定 | Win/Android | ★★★★★ | Intervention / AndroidCtl | `lock_screen` | 需密码 |
| `OUT-09` | 邮件发送 | 外部 | ★★★★★ | Notification | `send_email` | **不可撤销** |
| `OUT-10` | IM 告警 | 外部 | ★★★★★ | Notification | `send_webhook` | **不可撤销** |
| `OUT-11` | 音频警报 | Win/Android | ★★★☆☆ | Intervention | `play_alert_sound` | 物理静音 |

**链式编排示例**（Hermes Skill 中定义）：
```yaml
intervention_chain:
  level_1: [OUT-02, OUT-01]           # 桌宠皱眉 + 边缘提醒
  level_2: [OUT-03]                    # 居中弹窗，一键确认
  level_3: [OUT-04, OUT-05]            # 需输入理由 + 30秒倒计时
  level_4: [OUT-06, OUT-09]            # 冻结进程 + 邮件给老婆
  level_5: [OUT-08, OUT-10]            # 锁屏 + IM 告警
```

---

## 七、分级干预状态机（核心逻辑）

这是系统的灵魂，由 Hermes 决策 Agent 维护状态。

```
                    ┌─────────────┐
                    │   免疫期     │ ← 用户主动签到/完成番茄钟后进入
                    │  (2小时)    │
                    └──────┬──────┘
                           │ 超时或用户主动结束
                           ▼
┌──────────┐      ┌─────────────┐      ┌─────────────┐
│  感知逃逸  │─────→│  Level 1    │─────→│  Level 2    │
│ (打开娱乐) │      │  边缘提醒    │      │  居中弹窗    │
└──────────┘      │  桌宠提醒    │      │  一键确认    │
                  └──────┬──────┘      └──────┬──────┘
                         │ 用户关闭/忽略        │ 用户关闭
                         ▼                    ▼
                  ┌─────────────┐      ┌─────────────┐
                  │  状态重置    │      │  Level 3    │
                  │ (计数器+1)   │      │  理由输入窗  │
                  └─────────────┘      │  30秒倒计时  │
                                       └──────┬──────┘
                                              │ 用户关闭/超时
                                              ▼
                                       ┌─────────────┐
                                       │  Level 4    │
                                       │  冻结/强杀   │
                                       │  邮件告警    │
                                       └──────┬──────┘
                                              │ 用户再次逃逸（5分钟内）
                                              ▼
                                       ┌─────────────┐
                                       │  Level 5    │
                                       │  锁屏5分钟   │
                                       │  IM 告警     │
                                       └──────┬──────┘
                                              │ 锁屏结束
                                              ▼
                                       ┌─────────────┐
                                       │  休息模式    │
                                       │ (1小时免干预) │
                                       └─────────────┘
```

**自适应规则**（Hermes 记忆 Agent 维护）：
- 若用户连续 3 天在 Level 1 服从 → 次日跳过 Level 1，直接从 Level 2 开始（减少打扰）
- 若用户连续 2 天冲到 Level 5 → 次日任务难度自动降低 30%，或 Hermes 主动询问"任务是否不合理"
- 若用户在 Level 3 输入理由"在查资料" → 记忆 Agent 记录该理由，下次类似场景 Hermes 询问"这次也是在查资料吗？"

---

## 八、记忆与规则设计

### 8.1 Hermes 记忆结构（自动管理）

Hermes 自带记忆 Agent，你只需定义**记忆 Schema**，它会自动存储和检索。

```yaml
# memory_schema.yaml
entities:
  - name: daily_focus
    fields:
      - date: string
      - planned_task: string
      - escape_count: int
      - max_level_reached: int
      - compliance_rate: float
      
  - name: intervention_outcome
    fields:
      - timestamp: datetime
      - level: int
      - outlet: string
      - user_response: [complied, closed, ignored, lied]
      - reason_text: string  # Level 3 输入的理由
      
  - name: user_pattern
    fields:
      - pattern_id: string
      - description: string  # 如"周二下午易逃避"
      - confidence: float
      - generated_skill: string  # 自动生成的 Skill 文件名
```

### 8.2 硬规则 DSL（兜底）

Hermes 规则引擎支持 YAML DSL，用于**零延迟**（<50ms）的硬拦截，不走 LLM。

```yaml
# rules/focus_guardian.yaml
rules:
  - id: block-entertainment-workhours
    condition: |
      device.type == "android" 
      AND app.package in ["com.ss.android.ugc.aweme", "tv.danmaku.bili"]
      AND time.between("09:00", "18:00")
      AND NOT memory.is_immune_period()
    action:
      chain: ["OUT-05", "OUT-09"]  # 倒计时遮罩 + 邮件
      message: "工作时间禁止启动娱乐应用"
    priority: 100
    
  - id: night-scroll-limit
    condition: |
      time.between("23:00", "02:00")
      AND app.category == "social"
    action:
      chain: ["OUT-04"]  # 只需输入理由
      message: "深夜刷社交应用，请确认必要性"
    priority: 80
```

---

## 九、部署拓扑与运行方式

### 9.1 单主机模式（MVP 阶段）

```
[Windows PC]
    ├── Hermes Agent (Python, localhost:8000)
    ├── Ollama (本地 LLM, localhost:11434)
    ├── Intervention MCP (Python, stdio)
    ├── Perception MCP (Rust, stdio)
    ├── Notification MCP (Python, stdio)
    └── Tauri 桌宠 (WebSocket → Hermes Gateway)
              │
              │ ADB over WiFi / 局域网 WebSocket
              ▼
[Android Phone]
    ├── Flutter 悬浮球
    ├── AndroidCtl MCP (Kotlin Service)
    └── LSPosed 模块（可选，MVP 先用 Accessibility）
```

### 9.2 启动顺序

1. **Windows 端**：`hermes start --agent aegis-core`（自动拉起所有 MCP Server）
2. **Android 端**：打开 Aegis App，自动通过 mDNS 发现 PC 的 Hermes Gateway
3. **用户操作**：签到 → 进入免疫期/开始工作 → 系统进入监控态

---

## 十、MVP 迭代路线（8 周产品化）

| 周次 | 目标 | Hermes 配置重点 | 自研重点 |
|------|------|----------------|----------|
| **W1** | **骨架通** | 安装 Hermes；创建 `aegis-core` Agent；配置本地 Ollama | Intervention MCP（Level 1~2 弹窗）；Win 全局热键唤醒 |
| **W2** | **能打断** | 写第一个 Skill：`focus_guardian`；配置 Cron 每 5 分钟触发 | Perception MCP（Win 进程检测）；Android 悬浮球（通信） |
| **W3** | **分级跑** | Skill 中加入状态机逻辑；记忆 Agent 记录逃避次数 | Intervention MCP（Level 3 理由输入窗）；Android 全屏遮罩 |
| **W4** | **有代价** | Notification MCP 注册为 Hermes 工具；Skill 中加入邮件触发条件 | 邮件模板 + Resend/SMTP 配置；外部惩罚测试 |
| **W5** | **AI 接管** | 开启 Hermes 自动技能生成；让 AI 根据历史数据优化干预策略 | 桌宠接入（Tauri 透明窗口 + Live2D）；情绪同步 |
| **W6** | **视觉感知** | Perception MCP 增加截屏工具；Skill 中可选调用 VLM 分析屏幕内容 | Win DXGI 截屏；Android MediaProjection 截屏 |
| **W7** | **Android 深度** | AndroidCtl MCP 全面接入 Hermes；LSPosed 替代 Accessibility | LSPosed 模块（Hook ActivityManager）；ForceStop/系统级遮罩 |
| **W8** | **自进化** | Hermes 自动生成 3+ 个个性化 Skill；记忆 Agent 形成用户画像 | 数据看板（今日专注度、历史服从率）；规则 DSL 可视化编辑 |

---

## 十一、与全自研方案的对比（预告）

| 维度 | Aegis-Hermes（本方案） | Aegis-Native（全自研，下一份方案） |
|------|----------------------|----------------------------------|
| **开发周期** | 8 周 MVP | 16-20 周 MVP |
| **核心代码量** | ~5k 行（工具+客户端） | ~30k 行（Agent+记忆+调度+工具） |
| **决策智能** | 依赖 Hermes ReAct + 自动技能 | 自研状态机 + 自研 Prompt 工程 |
| **记忆能力** | Hermes 自动语义检索 | 自研 SQLite + 向量库 + 索引 |
| **可扩展性** | MCP 热插拔，生态共享 | 自研协议，完全可控 |
| **离线能力** | 本地 Ollama 可完全离线 | 完全离线，无外部依赖 |
| **定制深度** | 受限于 Hermes 框架边界 | 无边界，可魔改到系统内核 |
| **维护成本** | 低（跟随 Hermes 升级） | 高（所有模块自己维护） |
| **适合人群** | 想快速落地、接受框架约束 | 追求极致可控、有长期维护精力 |

---

## 十二、立即启动清单（今晚）

1. **安装 Hermes**：`curl -fsSL https://hermes.io/install.sh | bash`
2. **创建 Agent**：`hermes create-agent --name aegis-core`
3. **配置本地模型**：`hermes config set llm.provider ollama`
4. **拉取 Ollama**：`ollama pull qwen2.5:14b`
5. **创建目录结构**：
   ```
   ~/aegis/
   ├── mcp-servers/
   │   ├── intervention/
   │   ├── perception/
   │   ├── notification/
   │   └── android-ctl/
   ├── clients/
   │   ├── win-desktop/   (Tauri)
   │   └── android-app/   (Flutter)
   └── hermes-skills/
       └── focus_guardian.yaml
   ```
6. **写第一个 MCP Tool**：`intervention.show_popup(title, message)`，验证 Hermes 能调用它
7. **写第一个 Skill**：当检测到 `chrome.exe` 且窗口标题含"B站"时，调用 `show_popup`

---

**这份方案的核心价值**：你不需要理解 ReAct 循环怎么写、不需要写向量检索、不需要写技能生成算法。你只需要写**工具函数**（弹窗、发邮件、读进程），然后告诉 Hermes "**你有这些工具，这是你的职责**"，它就会自己学会什么时候用、怎么用、怎么组合。

**下一份方案（Aegis-Native 全自研）**将覆盖：自研 Agent 内核、自研记忆系统、自研规则引擎、自研 MCP 替代协议。需要我现在输出吗？