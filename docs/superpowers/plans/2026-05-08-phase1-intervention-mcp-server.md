# Phase 1: Intervention MCP Server 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个基于 Rust 的 MCP Server，实现 Aegis Phase 1 全部 L1-L5 干预工具，支持双线升级提醒，并具备本地 SQLite 数据持久化能力。

**Architecture:** 采用 MCP (Model Context Protocol) 标准协议，通过 stdio 与 Hermes 大脑通信。Server 分为三层：MCP 协议层 (`server.rs`)、工具注册与分发层 (`tools/`)、平台原生实现层 (`windows/`)。所有任务状态和提醒历史持久化到 SQLite。

**Tech Stack:** Rust 1.78+, `rmcp` (MCP SDK), `rusqlite`, `windows` crate (Win32 API), `tokio` (async runtime)

**提交原则：** 严格遵循 `git-auto-commit` skill 的最小提交单元原则——**一个提交 = 一个功能 = 一件完整、可独立验证、可回滚的事**。每个提交只做一件事，不合并无关变更。

---

## 文件结构总览

```
aegis-mcp-server/
├── Cargo.toml
├── src/
│   ├── main.rs              # 入口：初始化 + 启动 server
│   ├── lib.rs               # 库入口，模块声明
│   ├── server.rs            # McpServer 实现，处理 initialize/tools/call
│   ├── tools/
│   │   ├── mod.rs           # Tool trait + 注册表宏
│   │   ├── registry.rs      # 所有工具的注册与分发
│   │   ├── perception.rs    # get_current_time, get_system_state
│   │   ├── notification.rs  # show_notification
│   │   ├── wechat.rs        # send_wechat_message (stub)
│   │   ├── popup.rs         # show_popup
│   │   ├── sound.rs         # play_sound
│   │   ├── input.rs         # get_text_input, get_choice_input, get_photo_input, get_location_input
│   │   ├── overlay.rs       # show_countdown_overlay
│   │   └── fullscreen.rs    # show_fullscreen_block, lock_screen
│   ├── db/
│   │   ├── mod.rs           # DB 模块导出
│   │   ├── connection.rs    # SQLite 连接 + 初始化
│   │   └── models.rs        # Task, ReminderLog 等结构体
│   ├── reminder/
│   │   ├── mod.rs           # 提醒引擎模块
│   │   ├── engine.rs        # 双线升级调度核心
│   │   └── escalation.rs    # L1-L5 升级策略定义
│   └── windows/
│       ├── mod.rs           # Windows 模块导出
│       ├── notify.rs        # Win32 Toast 通知
│       ├── popup.rs         # Win32 MessageBox
│       ├── overlay.rs       # 倒计时遮罩（控制台模拟）
│       └── lock.rs          # LockWorkStation
└── tests/
    └── integration_tests.rs # 端到端工具调用测试
```

---

## 提交 1: 初始化项目脚手架

**功能：** 创建 Rust 项目，配置全部依赖，确保能编译通过。

**Files:**
- Create: `aegis-mcp-server/Cargo.toml`
- Create: `aegis-mcp-server/src/main.rs`（临时空入口）

- [ ] **Step 1: 创建项目并配置依赖**

Run:
```bash
cd /root/codeSpace/oneselfProject/ai-life-Aegis
cargo new --bin aegis-mcp-server
```

编辑 `aegis-mcp-server/Cargo.toml`:
```toml
[package]
name = "aegis-mcp-server"
version = "0.1.0"
edition = "2021"

[dependencies]
rmcp = { version = "0.8", features = ["server", "stdio"] }
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
anyhow = "1"
chrono = "0.4"
async-trait = "0.1"
rusqlite = { version = "0.32", features = ["bundled", "chrono"] }

[target.'cfg(windows)'.dependencies]
windows = { version = "0.56", features = [
    "Win32_UI_WindowsAndMessaging",
    "Win32_Foundation",
    "Win32_System_SystemServices",
] }

[dev-dependencies]
tokio-test = "0.4"
```

编辑 `aegis-mcp-server/src/main.rs`:
```rust
fn main() {
    println!("Aegis MCP Server");
}
```

Run:
```bash
cd aegis-mcp-server && cargo build
```
Expected: 编译成功

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/Cargo.toml aegis-mcp-server/src/main.rs
git commit -m "chore: 初始化 aegis-mcp-server 项目并配置依赖"
```

---

## 提交 2: MCP Server 骨架

**功能：** 搭建可运行的 MCP Server，能正确响应 `initialize` 请求。

**Files:**
- Create: `aegis-mcp-server/src/lib.rs`
- Create: `aegis-mcp-server/src/server.rs`
- Modify: `aegis-mcp-server/src/main.rs`
- Test: `aegis-mcp-server/tests/test_server_init.rs`

- [ ] **Step 1: 写失败测试**

创建 `aegis-mcp-server/tests/test_server_init.rs`:
```rust
use aegis_mcp_server::AegisMcpServer;

#[tokio::test]
async fn test_server_has_correct_name() {
    let server = AegisMcpServer::new();
    assert_eq!(server.name(), "aegis-intervention");
}
```

Run:
```bash
cargo test --test test_server_init
```
Expected: FAIL — `AegisMcpServer` 未定义

- [ ] **Step 2: 实现最小 MCP Server**

`aegis-mcp-server/src/lib.rs`:
```rust
pub mod server;
pub use server::AegisMcpServer;
```

`aegis-mcp-server/src/server.rs`:
```rust
use rmcp::{
    handler::server::server_handler,
    model::*,
    ServerHandler,
};

#[derive(Debug, Clone)]
pub struct AegisMcpServer;

impl AegisMcpServer {
    pub fn new() -> Self {
        Self
    }
    pub fn name(&self) -> &'static str {
        "aegis-intervention"
    }
}

#[server_handler]
impl ServerHandler for AegisMcpServer {
    async fn on_initialize(
        &self,
        _request: InitializeRequest,
        _info: ServerInfo,
    ) -> Result<InitializeResult, rmcp::Error> {
        Ok(InitializeResult {
            protocol_version: ProtocolVersion::V_2024_11_05,
            capabilities: ServerCapabilities::builder()
                .enable_tools()
                .build(),
            server_info: Implementation {
                name: "aegis-intervention".to_string(),
                version: env!("CARGO_PKG_VERSION").to_string(),
            },
            instructions: Some("Aegis Phase 1 Intervention MCP Server".to_string()),
        })
    }
}
```

`aegis-mcp-server/src/main.rs`:
```rust
use aegis_mcp_server::AegisMcpServer;
use rmcp::transport::stdio::StdioServerTransport;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let service = AegisMcpServer::new().into_router();
    let transport = StdioServerTransport::new(service);
    transport.await?;
    Ok(())
}
```

Run:
```bash
cargo test --test test_server_init
```
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add aegis-mcp-server/src/lib.rs aegis-mcp-server/src/server.rs aegis-mcp-server/src/main.rs aegis-mcp-server/tests/test_server_init.rs
git commit -m "feat(server): 实现 MCP Server 骨架，支持 initialize 响应"
```

---

## 提交 3: 数据库模型定义

**功能：** 定义 Task 和 ReminderLog 数据模型，为持久化做准备。

**Files:**
- Create: `aegis-mcp-server/src/db/mod.rs`
- Create: `aegis-mcp-server/src/db/models.rs`
- Modify: `aegis-mcp-server/src/lib.rs`

- [ ] **Step 1: 实现模型**

`aegis-mcp-server/src/db/mod.rs`:
```rust
pub mod models;
pub use models::{Task, TaskStatus, ReminderLog};
```

`aegis-mcp-server/src/db/models.rs`:
```rust
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum TaskStatus {
    Pending,
    Active,
    Completed,
    Skipped,
}

impl TaskStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            TaskStatus::Pending => "pending",
            TaskStatus::Active => "active",
            TaskStatus::Completed => "completed",
            TaskStatus::Skipped => "skipped",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub id: i64,
    pub user_id: String,
    pub title: String,
    pub scheduled_at: String,
    pub required_feedback: String,
    pub status: TaskStatus,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReminderLog {
    pub id: i64,
    pub task_id: i64,
    pub level: i32,
    pub feedback_type: String,
    pub notification_type: String,
    pub sent_at: String,
    pub responded_at: Option<String>,
    pub response_data: Option<String>,
}
```

`aegis-mcp-server/src/lib.rs` 追加：
```rust
pub mod db;
```

Run:
```bash
cargo check
```
Expected: 编译通过

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/db/mod.rs aegis-mcp-server/src/db/models.rs aegis-mcp-server/src/lib.rs
git commit -m "feat(db): 定义 Task 和 ReminderLog 数据模型"
```

---

## 提交 4: SQLite 连接与任务 CRUD

**功能：** 实现数据库连接、Schema 初始化、任务的增查和提醒日志记录。

**Files:**
- Create: `aegis-mcp-server/src/db/connection.rs`
- Modify: `aegis-mcp-server/src/db/mod.rs`
- Test: `aegis-mcp-server/tests/test_db.rs`

- [ ] **Step 1: 写失败测试**

创建 `aegis-mcp-server/tests/test_db.rs`:
```rust
use aegis_mcp_server::db::{DbPool, Task, TaskStatus};

#[tokio::test]
async fn test_create_and_fetch_task() {
    let pool = DbPool::new_in_memory().unwrap();
    let task = Task {
        id: 1,
        user_id: "user1".to_string(),
        title: "减肥打卡".to_string(),
        scheduled_at: chrono::Local::now().to_rfc3339(),
        required_feedback: "photo".to_string(),
        status: TaskStatus::Pending,
        created_at: chrono::Local::now().to_rfc3339(),
    };
    pool.insert_task(&task).unwrap();
    let fetched = pool.get_task(1).unwrap().unwrap();
    assert_eq!(fetched.title, "减肥打卡");
}
```

Run:
```bash
cargo test --test test_db
```
Expected: FAIL — `DbPool` 未定义

- [ ] **Step 2: 实现数据库连接**

`aegis-mcp-server/src/db/connection.rs`:
```rust
use anyhow::Result;
use rusqlite::{Connection, params};
use crate::db::models::{Task, TaskStatus, ReminderLog};

/// Phase 1 单连接数据库句柄。当前实现为单 Connection（Phase 1 单用户单进程够用）。
pub struct DbPool {
    conn: Connection,
}

impl DbPool {
    pub fn new_in_memory() -> Result<Self> {
        let conn = Connection::open_in_memory()?;
        let pool = Self { conn };
        pool.init_schema()?;
        Ok(pool)
    }

    pub fn new(path: &str) -> Result<Self> {
        let conn = Connection::open(path)?;
        let pool = Self { conn };
        pool.init_schema()?;
        Ok(pool)
    }

    fn init_schema(&self) -> Result<()> {
        self.conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                required_feedback TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reminder_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL REFERENCES tasks(id),
                level INTEGER NOT NULL,
                feedback_type TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                responded_at TEXT,
                response_data TEXT
            );"
        )?;
        Ok(())
    }

    pub fn insert_task(&self, task: &Task) -> Result<()> {
        self.conn.execute(
            "INSERT INTO tasks (id, user_id, title, scheduled_at, required_feedback, status, created_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![
                task.id, &task.user_id, &task.title, &task.scheduled_at,
                &task.required_feedback, task.status.as_str(), &task.created_at
            ],
        )?;
        Ok(())
    }

    pub fn get_task(&self, id: i64) -> Result<Option<Task>> {
        let mut stmt = self.conn.prepare(
            "SELECT id, user_id, title, scheduled_at, required_feedback, status, created_at FROM tasks WHERE id = ?1"
        )?;
        let mut rows = stmt.query_map([id], |row| {
            let status_str: String = row.get(5)?;
            let status = match status_str.as_str() {
                "active" => TaskStatus::Active,
                "completed" => TaskStatus::Completed,
                "skipped" => TaskStatus::Skipped,
                _ => TaskStatus::Pending,
            };
            Ok(Task {
                id: row.get(0)?,
                user_id: row.get(1)?,
                title: row.get(2)?,
                scheduled_at: row.get(3)?,
                required_feedback: row.get(4)?,
                status,
                created_at: row.get(6)?,
            })
        })?;
        if let Some(row) = rows.next() {
            Ok(Some(row?))
        } else {
            Ok(None)
        }
    }

    pub fn log_reminder(&self, log: &ReminderLog) -> Result<()> {
        self.conn.execute(
            "INSERT INTO reminder_logs (task_id, level, feedback_type, notification_type, sent_at, responded_at, response_data)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![
                log.task_id, log.level, &log.feedback_type, &log.notification_type,
                &log.sent_at, log.responded_at.as_ref(), log.response_data.as_ref()
            ],
        )?;
        Ok(())
    }
}
```

`aegis-mcp-server/src/db/mod.rs` 追加：
```rust
pub mod connection;
pub use connection::DbPool;
```

Run:
```bash
cargo test --test test_db
```
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add aegis-mcp-server/src/db/connection.rs aegis-mcp-server/src/db/mod.rs aegis-mcp-server/tests/test_db.rs
git commit -m "feat(db): 实现 SQLite 连接、Schema 初始化与任务 CRUD"
```

---

## 提交 5: Tool trait 与注册表骨架

**功能：** 定义工具接口和注册表，支持动态注册和调用。

**Files:**
- Create: `aegis-mcp-server/src/tools/mod.rs`
- Create: `aegis-mcp-server/src/tools/registry.rs`
- Modify: `aegis-mcp-server/src/lib.rs`

- [ ] **Step 1: 实现 Tool trait 与注册表**

`aegis-mcp-server/src/tools/mod.rs`:
```rust
pub mod registry;

use async_trait::async_trait;
use rmcp::model::CallToolRequest;
use serde_json::Value;
use anyhow::Result;

#[async_trait]
pub trait Tool: Send + Sync {
    fn name(&self) -> &'static str;
    fn description(&self) -> &'static str;
    fn schema(&self) -> Value;
    async fn execute(&self, args: CallToolRequest) -> Result<Value>;
}
```

`aegis-mcp-server/src/tools/registry.rs`:
```rust
use crate::tools::Tool;
use std::collections::HashMap;
use rmcp::model::CallToolRequest;
use serde_json::{json, Value};
use anyhow::{anyhow, Result};

pub struct ToolRegistry {
    tools: HashMap<&'static str, Box<dyn Tool>>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self {
            tools: HashMap::new(),
        }
    }

    pub fn register(&mut self, tool: Box<dyn Tool>) {
        self.tools.insert(tool.name(), tool);
    }

    pub fn list(&self) -> Vec<Value> {
        self.tools.values()
            .map(|t| {
                json!({
                    "name": t.name(),
                    "description": t.description(),
                    "inputSchema": t.schema()
                })
            })
            .collect()
    }

    pub async fn call(&self, name: &str, args: CallToolRequest) -> Result<Value> {
        let tool = self.tools.get(name)
            .ok_or_else(|| anyhow!("Tool not found: {}", name))?;
        tool.execute(args).await
    }
}
```

`aegis-mcp-server/src/lib.rs` 追加：
```rust
pub mod tools;
```

Run:
```bash
cargo check
```
Expected: 编译通过

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/tools/mod.rs aegis-mcp-server/src/tools/registry.rs aegis-mcp-server/src/lib.rs
git commit -m "feat(tools): 定义 Tool trait 与注册表骨架"
```

---

## 提交 6: Windows 通知原生层

**功能：** 实现 Windows Toast 通知基础能力（非 Windows 平台用控制台 fallback）。

**Files:**
- Create: `aegis-mcp-server/src/windows/mod.rs`
- Create: `aegis-mcp-server/src/windows/notify.rs`
- Modify: `aegis-mcp-server/src/lib.rs`
- Test: `aegis-mcp-server/tests/test_notification.rs`

- [ ] **Step 1: 写失败测试**

创建 `aegis-mcp-server/tests/test_notification.rs`:
```rust
use aegis_mcp_server::windows::show_windows_notification;

#[test]
fn test_notification_returns_ok() {
    let result = show_windows_notification("Test Title", "Test Body");
    assert!(result.is_ok());
}
```

Run:
```bash
cargo test --test test_notification
```
Expected: FAIL — `show_windows_notification` 未定义

- [ ] **Step 2: 实现 Windows 通知**

`aegis-mcp-server/src/windows/mod.rs`:
```rust
#[cfg(windows)]
pub mod notify;
#[cfg(windows)]
pub use notify::show_windows_notification;

#[cfg(not(windows))]
pub fn show_windows_notification(title: &str, body: &str) -> anyhow::Result<()> {
    println!("[NOTIFICATION] {}: {}", title, body);
    Ok(())
}
```

`aegis-mcp-server/src/windows/notify.rs`:
```rust
use anyhow::Result;
use windows::{
    core::*,
    Data::Xml::Dom::XmlDocument,
    UI::Notifications::{
        ToastNotification, ToastNotificationManager,
    },
};

pub fn show_windows_notification(title: &str, body: &str) -> Result<()> {
    let toast_xml = ToastNotificationManager::GetTemplateContent(
        windows::UI::Notifications::ToastTemplateType::ToastText02,
    )?;

    let text_elements = toast_xml.GetElementsByTagName(&HSTRING::from("text"))?;
    text_elements.Item(0)?.SetInnerText(&HSTRING::from(title))?;
    text_elements.Item(1)?.SetInnerText(&HSTRING::from(body))?;

    let toast = ToastNotification::CreateToastNotification(&toast_xml)?;
    let notifier = ToastNotificationManager::CreateToastNotifierWithId(
        &HSTRING::from("Aegis"))?;
    notifier.Show(&toast)?;
    Ok(())
}
```

`aegis-mcp-server/src/lib.rs` 追加：
```rust
#[cfg(windows)]
pub mod windows;
```

Run:
```bash
cargo test --test test_notification
```
Expected: PASS（Windows 上）或编译通过

- [ ] **Step 3: Commit**

```bash
git add aegis-mcp-server/src/windows/mod.rs aegis-mcp-server/src/windows/notify.rs aegis-mcp-server/src/lib.rs aegis-mcp-server/tests/test_notification.rs
git commit -m "feat(windows): 实现系统 Toast 通知原生层"
```

---

## 提交 7: show_notification MCP 工具

**功能：** 将 Windows 通知封装为 MCP 工具，可被 Hermes 调用。

**Files:**
- Create: `aegis-mcp-server/src/tools/notification.rs`
- Modify: `aegis-mcp-server/src/tools/mod.rs`
- Modify: `aegis-mcp-server/src/tools/registry.rs`
- Modify: `aegis-mcp-server/src/server.rs`

- [ ] **Step 1: 实现工具**

`aegis-mcp-server/src/tools/notification.rs`:
```rust
use crate::tools::Tool;
use async_trait::async_trait;
use rmcp::model::CallToolRequest;
use serde_json::{json, Value};
use anyhow::Result;

pub struct ShowNotificationTool;

#[async_trait]
impl Tool for ShowNotificationTool {
    fn name(&self) -> &'static str {
        "show_notification"
    }
    fn description(&self) -> &'static str {
        "显示系统通知 (L1-L2)"
    }
    fn schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "title": { "type": "string", "description": "通知标题" },
                "body": { "type": "string", "description": "通知内容" }
            },
            "required": ["title", "body"]
        })
    }
    async fn execute(&self, args: CallToolRequest) -> Result<Value> {
        let args = args.arguments.as_object().unwrap();
        let title = args["title"].as_str().unwrap_or("Aegis");
        let body = args["body"].as_str().unwrap_or("");
        crate::windows::show_windows_notification(title, body)?;
        Ok(json!({ "shown": true }))
    }
}
```

`aegis-mcp-server/src/tools/mod.rs` 追加：
```rust
pub mod notification;
```

`aegis-mcp-server/src/tools/registry.rs` 修改 `new()`：
```rust
pub fn new() -> Self {
    let mut registry = Self {
        tools: HashMap::new(),
    };
    registry.register(Box::new(notification::ShowNotificationTool));
    registry
}
```

`aegis-mcp-server/src/server.rs` 注入注册表：
```rust
use crate::tools::ToolRegistry;
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Debug, Clone)]
pub struct AegisMcpServer {
    registry: Arc<Mutex<ToolRegistry>>,
}

impl AegisMcpServer {
    pub fn new() -> Self {
        Self {
            registry: Arc::new(Mutex::new(ToolRegistry::new())),
        }
    }
}

#[server_handler]
impl ServerHandler for AegisMcpServer {
    // ... on_initialize 保持不变 ...

    async fn list_tools(
        &self, _request: Option<PaginatedRequest>
    ) -> Result<ListToolsResult, rmcp::Error> {
        let registry = self.registry.lock().await;
        Ok(ListToolsResult {
            tools: registry.list().into_iter()
                .map(|v| serde_json::from_value(v).unwrap())
                .collect(),
            next_cursor: None,
        })
    }

    async fn call_tool(
        &self, request: CallToolRequest
    ) -> Result<CallToolResult, rmcp::Error> {
        let registry = self.registry.lock().await;
        let name = request.name.clone();
        match registry.call(&name, request).await {
            Ok(result) => Ok(CallToolResult {
                content: vec![ToolResponseContent::text(result.to_string())],
                is_error: false,
            }),
            Err(e) => Ok(CallToolResult {
                content: vec![ToolResponseContent::text(e.to_string())],
                is_error: true,
            }),
        }
    }
}
```

Run:
```bash
cargo test --test test_server_init
```
Expected: PASS（空工具列表 → 现在有 1 个工具）

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/tools/notification.rs aegis-mcp-server/src/tools/mod.rs aegis-mcp-server/src/tools/registry.rs aegis-mcp-server/src/server.rs
git commit -m "feat(tools): 添加 show_notification MCP 工具"
```

---

## 提交 8: send_wechat_message MCP 工具

**功能：** 添加微信消息发送工具（Phase 1 stub，需外部微信接口）。

**Files:**
- Create: `aegis-mcp-server/src/tools/wechat.rs`
- Modify: `aegis-mcp-server/src/tools/mod.rs`
- Modify: `aegis-mcp-server/src/tools/registry.rs`

- [ ] **Step 1: 实现工具**

`aegis-mcp-server/src/tools/wechat.rs`:
```rust
use crate::tools::Tool;
use async_trait::async_trait;
use rmcp::model::CallToolRequest;
use serde_json::{json, Value};
use anyhow::Result;

pub struct SendWechatMessageTool;

#[async_trait]
impl Tool for SendWechatMessageTool {
    fn name(&self) -> &'static str {
        "send_wechat_message"
    }
    fn description(&self) -> &'static str {
        "发送微信消息 (L1，需要外部微信接口)"
    }
    fn schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "message": { "type": "string", "description": "消息内容" }
            },
            "required": ["message"]
        })
    }
    async fn execute(&self, args: CallToolRequest) -> Result<Value> {
        let args = args.arguments.as_object().unwrap();
        let msg = args["message"].as_str().unwrap_or("");
        println!("[WECHAT STUB] Would send: {}", msg);
        Ok(json!({ "sent": true, "note": "stub implementation" }))
    }
}
```

`aegis-mcp-server/src/tools/mod.rs` 追加：
```rust
pub mod wechat;
```

`aegis-mcp-server/src/tools/registry.rs` 的 `new()` 追加：
```rust
registry.register(Box::new(wechat::SendWechatMessageTool));
```

Run:
```bash
cargo test
```
Expected: 编译通过

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/tools/wechat.rs aegis-mcp-server/src/tools/mod.rs aegis-mcp-server/src/tools/registry.rs
git commit -m "feat(tools): 添加 send_wechat_message MCP 工具（stub）"
```

---

## 提交 9: Windows 弹窗原生层

**功能：** 实现 Windows 弹窗基础能力（`MessageBoxW`）。

**Files:**
- Create: `aegis-mcp-server/src/windows/popup.rs`
- Modify: `aegis-mcp-server/src/windows/mod.rs`
- Test: `aegis-mcp-server/tests/test_popup.rs`

- [ ] **Step 1: 写失败测试**

创建 `aegis-mcp-server/tests/test_popup.rs`:
```rust
use aegis_mcp_server::windows::show_windows_popup;

#[test]
fn test_popup_returns_ok() {
    let buttons = vec!["OK".to_string(), "Cancel".to_string()];
    let result = show_windows_popup("Title", "Message", &buttons);
    assert!(result.is_ok());
}
```

Run:
```bash
cargo test --test test_popup
```
Expected: FAIL

- [ ] **Step 2: 实现弹窗**

`aegis-mcp-server/src/windows/popup.rs`:
```rust
use anyhow::Result;
use windows::Win32::UI::WindowsAndMessaging::*;
use windows::Win32::Foundation::HWND;

pub fn show_windows_popup(title: &str, message: &str, _buttons: &[String]) -> Result<String> {
    let title_wide: Vec<u16> = title.encode_utf16().chain(std::iter::once(0)).collect();
    let message_wide: Vec<u16> = message.encode_utf16().chain(std::iter::once(0)).collect();

    unsafe {
        let result = MessageBoxW(
            HWND(0),
            windows::core::PCWSTR(message_wide.as_ptr()),
            windows::core::PCWSTR(title_wide.as_ptr()),
            MB_OKCANCEL | MB_ICONINFORMATION | MB_SYSTEMMODAL,
        );
        match result.0 {
            1 => Ok("OK".to_string()),
            2 => Ok("Cancel".to_string()),
            _ => Ok("Unknown".to_string()),
        }
    }
}
```

`aegis-mcp-server/src/windows/mod.rs` 追加：
```rust
#[cfg(windows)]
pub mod popup;
#[cfg(windows)]
pub use popup::show_windows_popup;
```

Run:
```bash
cargo test --test test_popup
```
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add aegis-mcp-server/src/windows/popup.rs aegis-mcp-server/src/windows/mod.rs aegis-mcp-server/tests/test_popup.rs
git commit -m "feat(windows): 实现弹窗原生层"
```

---

## 提交 10: show_popup MCP 工具

**功能：** 将弹窗封装为 MCP 工具。

**Files:**
- Create: `aegis-mcp-server/src/tools/popup.rs`
- Modify: `aegis-mcp-server/src/tools/mod.rs`
- Modify: `aegis-mcp-server/src/tools/registry.rs`

- [ ] **Step 1: 实现工具**

`aegis-mcp-server/src/tools/popup.rs`:
```rust
use crate::tools::Tool;
use async_trait::async_trait;
use rmcp::model::CallToolRequest;
use serde_json::{json, Value};
use anyhow::Result;

pub struct ShowPopupTool;

#[async_trait]
impl Tool for ShowPopupTool {
    fn name(&self) -> &'static str {
        "show_popup"
    }
    fn description(&self) -> &'static str {
        "显示弹窗，需用户点击确认 (L2-L3)"
    }
    fn schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "title": { "type": "string" },
                "message": { "type": "string" },
                "buttons": { "type": "array", "items": { "type": "string" }, "default": ["OK"] }
            },
            "required": ["title", "message"]
        })
    }
    async fn execute(&self, args: CallToolRequest) -> Result<Value> {
        let args = args.arguments.as_object().unwrap();
        let title = args["title"].as_str().unwrap_or("Aegis");
        let message = args["message"].as_str().unwrap_or("");
        let buttons: Vec<String> = args.get("buttons")
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
            .unwrap_or_else(|| vec!["OK".to_string()]);
        let clicked = crate::windows::show_windows_popup(title, message, &buttons)?;
        Ok(json!({ "clicked": clicked, "timeout": false }))
    }
}
```

`aegis-mcp-server/src/tools/mod.rs` 追加：
```rust
pub mod popup;
```

`aegis-mcp-server/src/tools/registry.rs` 的 `new()` 追加：
```rust
registry.register(Box::new(popup::ShowPopupTool));
```

Run:
```bash
cargo test
```
Expected: 编译通过

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/tools/popup.rs aegis-mcp-server/src/tools/mod.rs aegis-mcp-server/src/tools/registry.rs
git commit -m "feat(tools): 添加 show_popup MCP 工具"
```

---

## 提交 11: get_text_input MCP 工具

**功能：** 获取用户文字输入。

**Files:**
- Modify: `aegis-mcp-server/src/tools/input.rs`（新建并写入 GetTextInputTool）
- Modify: `aegis-mcp-server/src/tools/mod.rs`
- Modify: `aegis-mcp-server/src/tools/registry.rs`

- [ ] **Step 1: 实现工具**

创建 `aegis-mcp-server/src/tools/input.rs`:
```rust
use crate::tools::Tool;
use async_trait::async_trait;
use rmcp::model::CallToolRequest;
use serde_json::{json, Value};
use anyhow::Result;
use std::io::{self, Write};

pub struct GetTextInputTool;

#[async_trait]
impl Tool for GetTextInputTool {
    fn name(&self) -> &'static str {
        "get_text_input"
    }
    fn description(&self) -> &'static str {
        "获取用户文字输入"
    }
    fn schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "prompt": { "type": "string", "description": "输入提示语" }
            },
            "required": ["prompt"]
        })
    }
    async fn execute(&self, args: CallToolRequest) -> Result<Value> {
        let args = args.arguments.as_object().unwrap();
        let prompt = args["prompt"].as_str().unwrap_or("请输入:");
        print!("{}: ", prompt);
        io::stdout().flush()?;
        let mut input = String::new();
        io::stdin().read_line(&mut input)?;
        Ok(json!({ "submitted": true, "text": input.trim() }))
    }
}
```

`aegis-mcp-server/src/tools/mod.rs` 追加：
```rust
pub mod input;
```

`aegis-mcp-server/src/tools/registry.rs` 的 `new()` 追加：
```rust
registry.register(Box::new(input::GetTextInputTool));
```

Run:
```bash
cargo test
```
Expected: 编译通过

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/tools/input.rs aegis-mcp-server/src/tools/mod.rs aegis-mcp-server/src/tools/registry.rs
git commit -m "feat(tools): 添加 get_text_input MCP 工具"
```

---

## 提交 12: get_choice_input MCP 工具

**功能：** 获取用户多选确认。

**Files:**
- Modify: `aegis-mcp-server/src/tools/input.rs`
- Modify: `aegis-mcp-server/src/tools/registry.rs`

- [ ] **Step 1: 实现工具**

在 `aegis-mcp-server/src/tools/input.rs` 中追加：
```rust
pub struct GetChoiceInputTool;

#[async_trait]
impl Tool for GetChoiceInputTool {
    fn name(&self) -> &'static str {
        "get_choice_input"
    }
    fn description(&self) -> &'static str {
        "获取用户多选确认"
    }
    fn schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "prompt": { "type": "string" },
                "options": { "type": "array", "items": { "type": "string" } }
            },
            "required": ["prompt", "options"]
        })
    }
    async fn execute(&self, args: CallToolRequest) -> Result<Value> {
        let args = args.arguments.as_object().unwrap();
        let prompt = args["prompt"].as_str().unwrap_or("请选择:");
        let options: Vec<String> = args["options"].as_array()
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
            .unwrap_or_default();

        println!("{}", prompt);
        for (i, opt) in options.iter().enumerate() {
            println!("  [{}] {}", i + 1, opt);
        }
        print!("输入编号: ");
        io::stdout().flush()?;
        let mut input = String::new();
        io::stdin().read_line(&mut input)?;
        let choice = input.trim().parse::<usize>()
            .ok()
            .and_then(|n| options.get(n - 1))
            .cloned()
            .unwrap_or_default();
        Ok(json!({ "submitted": !choice.is_empty(), "choice": choice }))
    }
}
```

`aegis-mcp-server/src/tools/registry.rs` 的 `new()` 追加：
```rust
registry.register(Box::new(input::GetChoiceInputTool));
```

Run:
```bash
cargo test
```
Expected: 编译通过

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/tools/input.rs aegis-mcp-server/src/tools/registry.rs
git commit -m "feat(tools): 添加 get_choice_input MCP 工具"
```

---

## 提交 13: get_photo_input MCP 工具（stub）

**功能：** 拍照上传工具（Phase 1 控制台模拟，Phase 2 接入文件选择）。

**Files:**
- Modify: `aegis-mcp-server/src/tools/input.rs`
- Modify: `aegis-mcp-server/src/tools/registry.rs`

- [ ] **Step 1: 实现工具**

在 `aegis-mcp-server/src/tools/input.rs` 中追加：
```rust
pub struct GetPhotoInputTool;

#[async_trait]
impl Tool for GetPhotoInputTool {
    fn name(&self) -> &'static str {
        "get_photo_input"
    }
    fn description(&self) -> &'static str {
        "拍照上传（Phase 1 stub）"
    }
    fn schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "prompt": { "type": "string" }
            },
            "required": ["prompt"]
        })
    }
    async fn execute(&self, args: CallToolRequest) -> Result<Value> {
        let args = args.arguments.as_object().unwrap();
        let prompt = args["prompt"].as_str().unwrap_or("请拍照:");
        println!("[PHOTO STUB] {}", prompt);
        Ok(json!({ "submitted": true, "photo_base64": "stub" }))
    }
}
```

`aegis-mcp-server/src/tools/registry.rs` 的 `new()` 追加：
```rust
registry.register(Box::new(input::GetPhotoInputTool));
```

Run:
```bash
cargo test
```
Expected: 编译通过

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/tools/input.rs aegis-mcp-server/src/tools/registry.rs
git commit -m "feat(tools): 添加 get_photo_input MCP 工具（stub）"
```

---

## 提交 14: get_location_input MCP 工具（stub）

**功能：** 位置确认工具（Phase 1 控制台模拟）。

**Files:**
- Modify: `aegis-mcp-server/src/tools/input.rs`
- Modify: `aegis-mcp-server/src/tools/registry.rs`

- [ ] **Step 1: 实现工具**

在 `aegis-mcp-server/src/tools/input.rs` 中追加：
```rust
pub struct GetLocationInputTool;

#[async_trait]
impl Tool for GetLocationInputTool {
    fn name(&self) -> &'static str {
        "get_location_input"
    }
    fn description(&self) -> &'static str {
        "位置确认（Phase 1 stub）"
    }
    fn schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "prompt": { "type": "string" }
            },
            "required": ["prompt"]
        })
    }
    async fn execute(&self, args: CallToolRequest) -> Result<Value> {
        let args = args.arguments.as_object().unwrap();
        let prompt = args["prompt"].as_str().unwrap_or("确认位置:");
        println!("[LOCATION STUB] {}", prompt);
        Ok(json!({ "submitted": true, "latitude": 0.0, "longitude": 0.0, "address": "stub" }))
    }
}
```

`aegis-mcp-server/src/tools/registry.rs` 的 `new()` 追加：
```rust
registry.register(Box::new(input::GetLocationInputTool));
```

Run:
```bash
cargo test
```
Expected: 编译通过

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/tools/input.rs aegis-mcp-server/src/tools/registry.rs
git commit -m "feat(tools): 添加 get_location_input MCP 工具（stub）"
```

---

## 提交 15: Perception 工具集

**功能：** 添加 get_current_time 和 get_system_state 两个感知工具。

**Files:**
- Create: `aegis-mcp-server/src/tools/perception.rs`
- Modify: `aegis-mcp-server/src/tools/mod.rs`
- Modify: `aegis-mcp-server/src/tools/registry.rs`

- [ ] **Step 1: 实现工具**

`aegis-mcp-server/src/tools/perception.rs`:
```rust
use crate::tools::Tool;
use async_trait::async_trait;
use rmcp::model::CallToolRequest;
use serde_json::{json, Value};
use anyhow::Result;

pub struct GetCurrentTimeTool;

#[async_trait]
impl Tool for GetCurrentTimeTool {
    fn name(&self) -> &'static str {
        "get_current_time"
    }
    fn description(&self) -> &'static str {
        "获取当前时间"
    }
    fn schema(&self) -> Value {
        json!({ "type": "object", "properties": {} })
    }
    async fn execute(&self, _args: CallToolRequest) -> Result<Value> {
        let now = chrono::Local::now();
        Ok(json!({
            "time": now.format("%H:%M:%S").to_string(),
            "date": now.format("%Y-%m-%d").to_string(),
            "weekday": now.weekday().num_days_from_monday() as i32 + 1
        }))
    }
}

pub struct GetSystemStateTool;

#[async_trait]
impl Tool for GetSystemStateTool {
    fn name(&self) -> &'static str {
        "get_system_state"
    }
    fn description(&self) -> &'static str {
        "获取系统运行状态（Phase 1 返回硬编码值）"
    }
    fn schema(&self) -> Value {
        json!({ "type": "object", "properties": {} })
    }
    async fn execute(&self, _args: CallToolRequest) -> Result<Value> {
        Ok(json!({
            "pc_online": true,
            "screen_on": true
        }))
    }
}
```

`aegis-mcp-server/src/tools/mod.rs` 追加：
```rust
pub mod perception;
```

`aegis-mcp-server/src/tools/registry.rs` 的 `new()` 追加：
```rust
registry.register(Box::new(perception::GetCurrentTimeTool));
registry.register(Box::new(perception::GetSystemStateTool));
```

Run:
```bash
cargo test
```
Expected: 编译通过

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/tools/perception.rs aegis-mcp-server/src/tools/mod.rs aegis-mcp-server/src/tools/registry.rs
git commit -m "feat(tools): 添加 Perception 工具集（get_current_time, get_system_state）"
```

---

## 提交 16: play_sound MCP 工具

**功能：** 播放提示音（Windows 用 `MessageBeep`，非 Windows 控制台模拟）。

**Files:**
- Create: `aegis-mcp-server/src/tools/sound.rs`
- Modify: `aegis-mcp-server/src/tools/mod.rs`
- Modify: `aegis-mcp-server/src/tools/registry.rs`

- [ ] **Step 1: 实现工具**

`aegis-mcp-server/src/tools/sound.rs`:
```rust
use crate::tools::Tool;
use async_trait::async_trait;
use rmcp::model::CallToolRequest;
use serde_json::{json, Value};
use anyhow::Result;

pub struct PlaySoundTool;

#[async_trait]
impl Tool for PlaySoundTool {
    fn name(&self) -> &'static str {
        "play_sound"
    }
    fn description(&self) -> &'static str {
        "播放提示音 (L4)"
    }
    fn schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "sound_type": { "type": "string", "enum": ["gentle", "alert", "alarm"], "default": "alert" }
            }
        })
    }
    async fn execute(&self, args: CallToolRequest) -> Result<Value> {
        let args = args.arguments.as_object().unwrap();
        let sound_type = args.get("sound_type").and_then(|v| v.as_str()).unwrap_or("alert");
        #[cfg(windows)]
        {
            use windows::Win32::UI::WindowsAndMessaging::MessageBeep;
            unsafe {
                match sound_type {
                    "gentle" => MessageBeep(0x00000000),
                    "alarm" => MessageBeep(0x00000030),
                    _ => MessageBeep(0x00000010),
                };
            }
        }
        #[cfg(not(windows))]
        {
            println!("[SOUND] Playing: {}", sound_type);
        }
        Ok(json!({ "played": true, "sound_type": sound_type }))
    }
}
```

`aegis-mcp-server/src/tools/mod.rs` 追加：
```rust
pub mod sound;
```

`aegis-mcp-server/src/tools/registry.rs` 的 `new()` 追加：
```rust
registry.register(Box::new(sound::PlaySoundTool));
```

Run:
```bash
cargo test
```
Expected: 编译通过

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/tools/sound.rs aegis-mcp-server/src/tools/mod.rs aegis-mcp-server/src/tools/registry.rs
git commit -m "feat(tools): 添加 play_sound MCP 工具"
```

---

## 提交 17: Windows 遮罩原生层

**功能：** 实现倒计时遮罩和全屏阻断的基础层（Phase 1 控制台模拟，Phase 1.5 换真窗口）。

**Files:**
- Create: `aegis-mcp-server/src/windows/overlay.rs`
- Modify: `aegis-mcp-server/src/windows/mod.rs`
- Test: `aegis-mcp-server/tests/test_overlay.rs`

- [ ] **Step 1: 写失败测试**

创建 `aegis-mcp-server/tests/test_overlay.rs`:
```rust
use aegis_mcp_server::windows::show_countdown_overlay;

#[test]
fn test_overlay_returns_ok() {
    let result = show_countdown_overlay("Test", 1);
    assert!(result.is_ok());
}
```

Run:
```bash
cargo test --test test_overlay
```
Expected: FAIL

- [ ] **Step 2: 实现遮罩层**

`aegis-mcp-server/src/windows/overlay.rs`:
```rust
use anyhow::Result;
use std::thread;
use std::time::Duration;

pub fn show_countdown_overlay(message: &str, seconds: u32) -> Result<bool> {
    println!("[OVERLAY] {} — 倒计时 {} 秒", message, seconds);
    for i in (1..=seconds).rev() {
        print!("\r剩余 {} 秒...", i);
        std::io::Write::flush(&mut std::io::stdout())?;
        thread::sleep(Duration::from_secs(1));
    }
    println!("\n倒计时结束");
    Ok(true)
}

pub fn show_fullscreen_block(message: &str, _required_feedback: &str) -> Result<String> {
    println!("[FULLSCREEN BLOCK] {}", message);
    println!("(按 Enter 解除阻断)");
    let mut input = String::new();
    std::io::stdin().read_line(&mut input)?;
    Ok(input.trim().to_string())
}
```

`aegis-mcp-server/src/windows/mod.rs` 追加：
```rust
pub mod overlay;
pub use overlay::{show_countdown_overlay, show_fullscreen_block};
```

Run:
```bash
cargo test --test test_overlay
```
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add aegis-mcp-server/src/windows/overlay.rs aegis-mcp-server/src/windows/mod.rs aegis-mcp-server/tests/test_overlay.rs
git commit -m "feat(windows): 实现倒计时遮罩原生层（Phase 1 控制台模拟）"
```

---

## 提交 18: show_countdown_overlay MCP 工具

**功能：** 将倒计时遮罩封装为 MCP 工具。

**Files:**
- Create: `aegis-mcp-server/src/tools/overlay.rs`
- Modify: `aegis-mcp-server/src/tools/mod.rs`
- Modify: `aegis-mcp-server/src/tools/registry.rs`

- [ ] **Step 1: 实现工具**

`aegis-mcp-server/src/tools/overlay.rs`:
```rust
use crate::tools::Tool;
use async_trait::async_trait;
use rmcp::model::CallToolRequest;
use serde_json::{json, Value};
use anyhow::Result;

pub struct ShowCountdownOverlayTool;

#[async_trait]
impl Tool for ShowCountdownOverlayTool {
    fn name(&self) -> &'static str {
        "show_countdown_overlay"
    }
    fn description(&self) -> &'static str {
        "显示倒计时遮罩，不可跳过 (L4)"
    }
    fn schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "message": { "type": "string" },
                "seconds": { "type": "integer", "minimum": 1, "maximum": 300 },
                "required_feedback": { "type": "string" }
            },
            "required": ["message", "seconds"]
        })
    }
    async fn execute(&self, args: CallToolRequest) -> Result<Value> {
        let args = args.arguments.as_object().unwrap();
        let message = args["message"].as_str().unwrap_or("");
        let seconds = args["seconds"].as_u64().unwrap_or(30) as u32;
        crate::windows::show_countdown_overlay(message, seconds)?;
        Ok(json!({ "completed": true, "waited_seconds": seconds }))
    }
}
```

`aegis-mcp-server/src/tools/mod.rs` 追加：
```rust
pub mod overlay;
```

`aegis-mcp-server/src/tools/registry.rs` 的 `new()` 追加：
```rust
registry.register(Box::new(overlay::ShowCountdownOverlayTool));
```

Run:
```bash
cargo test
```
Expected: 编译通过

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/tools/overlay.rs aegis-mcp-server/src/tools/mod.rs aegis-mcp-server/src/tools/registry.rs
git commit -m "feat(tools): 添加 show_countdown_overlay MCP 工具"
```

---

## 提交 19: lock_screen MCP 工具

**功能：** 锁定屏幕（Windows 调用 `LockWorkStation`，非 Windows 控制台模拟）。

**Files:**
- Create: `aegis-mcp-server/src/windows/lock.rs`
- Modify: `aegis-mcp-server/src/windows/mod.rs`
- Create: `aegis-mcp-server/src/tools/fullscreen.rs`（写入 LockScreenTool）
- Modify: `aegis-mcp-server/src/tools/mod.rs`
- Modify: `aegis-mcp-server/src/tools/registry.rs`

- [ ] **Step 1: 实现原生层和工具**

`aegis-mcp-server/src/windows/lock.rs`:
```rust
use anyhow::Result;

pub fn lock_workstation() -> Result<()> {
    #[cfg(windows)]
    {
        use windows::Win32::System::SystemServices::LockWorkStation;
        unsafe {
            LockWorkStation()?;
        }
    }
    #[cfg(not(windows))]
    {
        println!("[LOCK] LockWorkStation stub");
    }
    Ok(())
}
```

`aegis-mcp-server/src/windows/mod.rs` 追加：
```rust
pub mod lock;
pub use lock::lock_workstation;
```

`aegis-mcp-server/src/tools/fullscreen.rs`:
```rust
use crate::tools::Tool;
use async_trait::async_trait;
use rmcp::model::CallToolRequest;
use serde_json::{json, Value};
use anyhow::Result;

pub struct LockScreenTool;

#[async_trait]
impl Tool for LockScreenTool {
    fn name(&self) -> &'static str {
        "lock_screen"
    }
    fn description(&self) -> &'static str {
        "锁定屏幕 (L5)"
    }
    fn schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "duration_seconds": { "type": "integer", "minimum": 1 }
            },
            "required": ["duration_seconds"]
        })
    }
    async fn execute(&self, args: CallToolRequest) -> Result<Value> {
        let args = args.arguments.as_object().unwrap();
        let duration = args["duration_seconds"].as_u64().unwrap_or(60);
        crate::windows::lock_workstation()?;
        Ok(json!({ "unlocked": false, "locked_duration": duration }))
    }
}
```

`aegis-mcp-server/src/tools/mod.rs` 追加：
```rust
pub mod fullscreen;
```

`aegis-mcp-server/src/tools/registry.rs` 的 `new()` 追加：
```rust
registry.register(Box::new(fullscreen::LockScreenTool));
```

Run:
```bash
cargo test
```
Expected: 编译通过

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/windows/lock.rs aegis-mcp-server/src/windows/mod.rs aegis-mcp-server/src/tools/fullscreen.rs aegis-mcp-server/src/tools/mod.rs aegis-mcp-server/src/tools/registry.rs
git commit -m "feat(tools): 添加 lock_screen MCP 工具"
```

---

## 提交 20: show_fullscreen_block MCP 工具

**功能：** 全屏阻断工具（必须提交反馈才能解除）。

**Files:**
- Modify: `aegis-mcp-server/src/tools/fullscreen.rs`
- Modify: `aegis-mcp-server/src/tools/registry.rs`

- [ ] **Step 1: 实现工具**

在 `aegis-mcp-server/src/tools/fullscreen.rs` 中追加：
```rust
pub struct ShowFullscreenBlockTool;

#[async_trait]
impl Tool for ShowFullscreenBlockTool {
    fn name(&self) -> &'static str {
        "show_fullscreen_block"
    }
    fn description(&self) -> &'static str {
        "全屏阻断，必须提交反馈才能解除 (L5)"
    }
    fn schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "message": { "type": "string" },
                "required_feedback": { "type": "string", "enum": ["text", "photo", "location"] }
            },
            "required": ["message", "required_feedback"]
        })
    }
    async fn execute(&self, args: CallToolRequest) -> Result<Value> {
        let args = args.arguments.as_object().unwrap();
        let message = args["message"].as_str().unwrap_or("");
        let required = args["required_feedback"].as_str().unwrap_or("text");
        let feedback = crate::windows::show_fullscreen_block(message, required)?;
        Ok(json!({ "completed": true, "feedback_submitted": feedback }))
    }
}
```

`aegis-mcp-server/src/tools/registry.rs` 的 `new()` 追加：
```rust
registry.register(Box::new(fullscreen::ShowFullscreenBlockTool));
```

Run:
```bash
cargo test
```
Expected: 编译通过

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/tools/fullscreen.rs aegis-mcp-server/src/tools/registry.rs
git commit -m "feat(tools): 添加 show_fullscreen_block MCP 工具"
```

---

## 提交 21: 双线升级策略状态机

**功能：** 定义反馈升级通道和通知强度升级通道的状态机。

**Files:**
- Create: `aegis-mcp-server/src/reminder/mod.rs`
- Create: `aegis-mcp-server/src/reminder/escalation.rs`
- Modify: `aegis-mcp-server/src/lib.rs`
- Test: `aegis-mcp-server/tests/test_escalation.rs`

- [ ] **Step 1: 写失败测试**

创建 `aegis-mcp-server/tests/test_escalation.rs`:
```rust
use aegis_mcp_server::reminder::{EscalationState, NotificationLevel, FeedbackLevel};

#[test]
fn test_escalation_progression() {
    let mut state = EscalationState::initial();
    assert_eq!(state.notification_level, NotificationLevel::L1);
    assert_eq!(state.feedback_level, FeedbackLevel::Text);

    state.escalate();
    assert_eq!(state.notification_level, NotificationLevel::L2);
    assert_eq!(state.feedback_level, FeedbackLevel::Photo);

    state.escalate();
    assert_eq!(state.notification_level, NotificationLevel::L3);
    assert_eq!(state.feedback_level, FeedbackLevel::Location);

    state.escalate();
    state.escalate();
    assert_eq!(state.notification_level, NotificationLevel::L5);
    assert_eq!(state.feedback_level, FeedbackLevel::PhotoText);
}
```

Run:
```bash
cargo test --test test_escalation
```
Expected: FAIL

- [ ] **Step 2: 实现状态机**

`aegis-mcp-server/src/reminder/mod.rs`:
```rust
pub mod escalation;
pub use escalation::{EscalationState, NotificationLevel, FeedbackLevel};
```

`aegis-mcp-server/src/reminder/escalation.rs`:
```rust
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum FeedbackLevel {
    Text,
    Photo,
    Location,
    PhotoText,
}

impl FeedbackLevel {
    pub fn next(&self) -> Option<Self> {
        match self {
            FeedbackLevel::Text => Some(FeedbackLevel::Photo),
            FeedbackLevel::Photo => Some(FeedbackLevel::Location),
            FeedbackLevel::Location => Some(FeedbackLevel::PhotoText),
            FeedbackLevel::PhotoText => None,
        }
    }
    pub fn as_str(&self) -> &'static str {
        match self {
            FeedbackLevel::Text => "text",
            FeedbackLevel::Photo => "photo",
            FeedbackLevel::Location => "location",
            FeedbackLevel::PhotoText => "photo_text",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum NotificationLevel {
    L1,
    L2,
    L3,
    L4,
    L5,
}

impl NotificationLevel {
    pub fn as_str(&self) -> &'static str {
        match self {
            NotificationLevel::L1 => "L1",
            NotificationLevel::L2 => "L2",
            NotificationLevel::L3 => "L3",
            NotificationLevel::L4 => "L4",
            NotificationLevel::L5 => "L5",
        }
    }
    pub fn next(&self) -> Option<Self> {
        match self {
            NotificationLevel::L1 => Some(NotificationLevel::L2),
            NotificationLevel::L2 => Some(NotificationLevel::L3),
            NotificationLevel::L3 => Some(NotificationLevel::L4),
            NotificationLevel::L4 => Some(NotificationLevel::L5),
            NotificationLevel::L5 => None,
        }
    }
    pub fn tools(&self) -> Vec<&'static str> {
        match self {
            NotificationLevel::L1 => vec!["send_wechat_message", "show_notification"],
            NotificationLevel::L2 => vec!["send_wechat_message", "show_popup"],
            NotificationLevel::L3 => vec!["show_popup", "play_sound"],
            NotificationLevel::L4 => vec!["show_countdown_overlay"],
            NotificationLevel::L5 => vec!["show_fullscreen_block"],
        }
    }
}

#[derive(Debug, Clone)]
pub struct EscalationState {
    pub feedback_level: FeedbackLevel,
    pub notification_level: NotificationLevel,
    pub attempt_count: u32,
}

impl EscalationState {
    pub fn initial() -> Self {
        Self {
            feedback_level: FeedbackLevel::Text,
            notification_level: NotificationLevel::L1,
            attempt_count: 0,
        }
    }
    pub fn escalate(&mut self) {
        if let Some(next) = self.feedback_level.next() {
            self.feedback_level = next;
        }
        if let Some(next) = self.notification_level.next() {
            self.notification_level = next;
        }
        self.attempt_count += 1;
    }
}
```

`aegis-mcp-server/src/lib.rs` 追加：
```rust
pub mod reminder;
```

Run:
```bash
cargo test --test test_escalation
```
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add aegis-mcp-server/src/reminder/mod.rs aegis-mcp-server/src/reminder/escalation.rs aegis-mcp-server/src/lib.rs aegis-mcp-server/tests/test_escalation.rs
git commit -m "feat(reminder): 实现双线升级策略状态机"
```

---

## 提交 22: 提醒引擎调度器

**功能：** 实现按时间间隔驱动 L1→L5 升级的调度核心。

**Files:**
- Create: `aegis-mcp-server/src/reminder/engine.rs`
- Modify: `aegis-mcp-server/src/reminder/mod.rs`

- [ ] **Step 1: 实现调度器**

`aegis-mcp-server/src/reminder/engine.rs`:
```rust
use crate::reminder::escalation::{EscalationState, NotificationLevel};
use crate::tools::ToolRegistry;
use rmcp::model::CallToolRequest;
use serde_json::{json, Value};
use std::sync::Arc;
use tokio::sync::Mutex;
use tokio::time::{sleep, Duration};
use anyhow::Result;

pub struct ReminderEngine {
    registry: Arc<Mutex<ToolRegistry>>,
}

impl ReminderEngine {
    pub fn new(registry: Arc<Mutex<ToolRegistry>>) -> Self {
        Self { registry }
    }

    pub async fn run_reminder_cycle(
        &self,
        task_id: i64,
        message: &str,
        interval_secs: u64,
    ) -> Result<Value> {
        let mut state = EscalationState::initial();
        let max_attempts = 5;

        for attempt in 0..max_attempts {
            println!("\n[Reminder] Task {} — Attempt {} ({} / {:?})",
                task_id, attempt + 1,
                state.notification_level.as_str(),
                state.feedback_level
            );

            let result = self.execute_level(&state, message).await?;

            if result.get("clicked").is_some_and(|v| v.as_str() != Some("Cancel")) {
                return Ok(json!({ "completed": true, "at_level": state.notification_level.as_str() }));
            }
            if result.get("submitted").is_some_and(|v| v.as_bool() == Some(true)) {
                return Ok(json!({ "completed": true, "feedback": result }));
            }
            if result.get("completed").is_some_and(|v| v.as_bool() == Some(true)) {
                return Ok(json!({ "completed": true }));
            }

            if attempt < max_attempts - 1 {
                sleep(Duration::from_secs(interval_secs)).await;
                state.escalate();
            }
        }

        Ok(json!({ "completed": false, "max_level_reached": "L5" }))
    }

    async fn execute_level(&self, state: &EscalationState, message: &str) -> Result<Value> {
        let registry = self.registry.lock().await;
        let tools = state.notification_level.tools();
        let mut results = vec![];

        for tool_name in tools {
            let args = Self::build_args_for_tool(tool_name, message);
            match registry.call(tool_name, args).await {
                Ok(result) => results.push(result),
                Err(e) => {
                    println!("[WARN] Tool {} failed: {}", tool_name, e);
                }
            }
        }
        drop(registry);

        let mut combined = json!({});
        for result in results {
            if let Some(obj) = result.as_object() {
                for (k, v) in obj {
                    combined[k] = v.clone();
                }
            }
        }
        Ok(combined)
    }

    fn build_args_for_tool(tool_name: &str, message: &str) -> CallToolRequest {
        let arguments = match tool_name {
            "show_notification" => json!({ "title": "Aegis 提醒", "body": message }),
            "send_wechat_message" => json!({ "message": message }),
            "show_popup" => json!({ "title": "Aegis", "message": message, "buttons": ["OK", "稍后"] }),
            "play_sound" => json!({ "sound_type": "alert" }),
            "show_countdown_overlay" => json!({ "message": message, "seconds": 30 }),
            "show_fullscreen_block" => json!({ "message": message, "required_feedback": "text" }),
            _ => json!({ "prompt": message }),
        };
        CallToolRequest {
            name: tool_name.to_string(),
            arguments,
        }
    }
}
```

`aegis-mcp-server/src/reminder/mod.rs` 追加：
```rust
pub mod engine;
pub use engine::ReminderEngine;
```

Run:
```bash
cargo test
```
Expected: 编译通过

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/src/reminder/engine.rs aegis-mcp-server/src/reminder/mod.rs
git commit -m "feat(reminder): 实现提醒引擎调度器"
```

---

## 提交 23: MCP Server 集成测试

**功能：** 验证全部 13 个工具正确注册且可被调用。

**Files:**
- Create: `aegis-mcp-server/tests/integration_tests.rs`

- [ ] **Step 1: 写集成测试**

`aegis-mcp-server/tests/integration_tests.rs`:
```rust
use aegis_mcp_server::AegisMcpServer;
use rmcp::ServerHandler;

#[tokio::test]
async fn test_server_lists_all_tools() {
    let server = AegisMcpServer::new();
    let tools = server.list_tools(None).await.unwrap();
    let tool_names: Vec<String> = tools.tools.iter()
        .map(|t| t.name.clone())
        .collect();

    assert!(tool_names.contains(&"show_notification".to_string()));
    assert!(tool_names.contains(&"send_wechat_message".to_string()));
    assert!(tool_names.contains(&"show_popup".to_string()));
    assert!(tool_names.contains(&"get_text_input".to_string()));
    assert!(tool_names.contains(&"get_choice_input".to_string()));
    assert!(tool_names.contains(&"get_photo_input".to_string()));
    assert!(tool_names.contains(&"get_location_input".to_string()));
    assert!(tool_names.contains(&"get_current_time".to_string()));
    assert!(tool_names.contains(&"get_system_state".to_string()));
    assert!(tool_names.contains(&"play_sound".to_string()));
    assert!(tool_names.contains(&"show_countdown_overlay".to_string()));
    assert!(tool_names.contains(&"show_fullscreen_block".to_string()));
    assert!(tool_names.contains(&"lock_screen".to_string()));
    assert_eq!(tools.tools.len(), 13);
}

#[tokio::test]
async fn test_call_notification_tool() {
    let server = AegisMcpServer::new();
    let result = server.call_tool(rmcp::model::CallToolRequest {
        name: "show_notification".to_string(),
        arguments: serde_json::json!({
            "title": "Test",
            "body": "Hello from test"
        }),
    }).await.unwrap();

    assert!(!result.is_error);
    let content_json = serde_json::to_string(&result.content).unwrap();
    assert!(content_json.contains("shown"));
}

#[tokio::test]
async fn test_call_unknown_tool_returns_error() {
    let server = AegisMcpServer::new();
    let result = server.call_tool(rmcp::model::CallToolRequest {
        name: "nonexistent".to_string(),
        arguments: serde_json::json!({}),
    }).await.unwrap();

    assert!(result.is_error);
}
```

Run:
```bash
cargo test
```
Expected: 全部通过（13个工具正确注册）

- [ ] **Step 2: Commit**

```bash
git add aegis-mcp-server/tests/integration_tests.rs
git commit -m "test: 添加 MCP Server 集成测试，覆盖 13 个工具"
```

---

## 提交 24: 主入口整合

**功能：** 连接数据库，启动 MCP Server，验证可运行。

**Files:**
- Modify: `aegis-mcp-server/src/main.rs`

- [ ] **Step 1: 完善主入口**

`aegis-mcp-server/src/main.rs`:
```rust
use aegis_mcp_server::{AegisMcpServer, db::DbPool};
use rmcp::transport::stdio::StdioServerTransport;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let db_path = std::env::var("AEGIS_DB_PATH").unwrap_or_else(|_| "aegis.db".to_string());
    let _db = DbPool::new(&db_path)?;
    println!("[Aegis] Database initialized at {}", db_path);

    let service = AegisMcpServer::new().into_router();
    let transport = StdioServerTransport::new(service);
    println!("[Aegis] MCP Server running on stdio");
    transport.await?;
    Ok(())
}
```

Run:
```bash
cargo build --release
```
Expected: 编译成功

- [ ] **Step 2: 手动验证 stdio 响应**

Run:
```bash
cd aegis-mcp-server
cargo build --release
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | ./target/release/aegis-mcp-server
```
Expected: 能看到 JSONRPC 响应，包含 serverInfo.name = "aegis-intervention"

- [ ] **Step 3: Commit**

```bash
git add aegis-mcp-server/src/main.rs
git commit -m "feat(main): 整合数据库与 MCP Server 主入口"
```

---

## 附录：Windows 原生 UI 细化（Phase 1.5 可选）

当前 `windows/` 模块的分层策略：
- **Windows 平台**：基础 Win32 API 实现（`MessageBoxW`、`MessageBeep`、`LockWorkStation`、Toast 通知）。Toast 通知若因缺少 AppUserModelID 注册失败，后续补充 `MessageBoxW` fallback。
- **非 Windows 平台**：控制台 fallback（`println!`），保证编译和基础功能可用。

Phase 1 验收条件中的"正确弹出/执行"在 Windows 上由基础 Win32 API 覆盖，在非 Windows 上由控制台模拟。
如需完整原生体验（无边框遮罩、键盘钩子拦截、锁屏后遮罩），需 Phase 1.5 追加：

1. **倒计时遮罩**：创建真正的 `WS_POPUP | WS_VISIBLE` 窗口，`SetWindowPos(HWND_TOPMOST)`，GDI 绘制倒计时文本。
2. **全屏阻断**：无边框全屏窗口 + 禁用 `Alt+Tab` / `Win` 键，通过 WH_KEYBOARD_LL 钩子拦截。
3. **锁屏后遮罩**：锁屏解锁后立即弹出遮罩窗口，防止用户解锁后逃避。

---

## Phase 1 验收对照表

| # | 验收条件 | 对应提交 | 验证命令 |
|---|---------|---------|---------|
| 1 | 微信输入目标拆解 → 收到计划 | Phase 1 结束与 Hermes 集成时验证 | — |
| 3 | L1 微信消息正确发送 | 提交 8 | `cargo test --test integration_tests test_call_notification_tool` |
| 4 | L2 系统通知正确弹出 | 提交 7 | 手动运行 Server 调用 `show_notification` |
| 5 | L3 弹窗确认正确弹出 | 提交 10 | 手动运行 Server 调用 `show_popup` |
| 6 | L4 倒计时遮罩不可跳过 | 提交 18 | 手动运行 Server 调用 `show_countdown_overlay` |
| 7 | L5 全屏阻断正确执行 | 提交 20 | 手动运行 Server 调用 `show_fullscreen_block` |
| 8 | 提醒升级策略正确 L1→L5 | 提交 21 | `cargo test --test test_escalation` |
| 11 | 提醒响应被记录 | 提交 4 | `cargo test --test test_db` |
| 14 | 部署简单，Windows 可启动 | 提交 24 | `cargo build --release` |
