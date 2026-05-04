# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码仓库中工作时提供指导。

## 通用约定

- 所有回复使用中文
- 所有 git commit 使用中文

## Git 提交规范

### 核心原则

最小提交单元：一个提交 = 一个功能 = 一件完整、可独立验证、可回滚的事。

### 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

- **type**：feat / fix / docs / style / refactor / test / chore
- **scope**：影响范围（可选），如模块或目录名
- **subject**：简短描述，不超过 50 字，祈使语气
- **body**：详细说明（可选），解释 why 而非 what
- **footer**：BREAKING CHANGE / 关联 issue（可选）

### 示例

```
feat(docs): 添加 Hermes 方案设计文档

- 新增 docs/基于hermes的个人生活助手方案.md
- 包含架构选型、核心模块、技术路线

Closes #1
```

## 项目概述

个人 AI 生活助手系统设计文档仓库，处于早期规划阶段。`docs/` 目录下有两份设计方案：

- `全自主开发的个人生活助手方案.md` — 自主研发路线
- `基于hermes的个人生活助手方案.md` — 基于 Hermes 框架路线

## 目录结构

```
ai-life-Aegis/
├── docs/                          # 设计文档与方案
└── CLAUDE.md
```

## 常用操作

- 新增设计文档：`git add docs/<文件名>.md` → `git commit`
- 查看提交历史：`git log --oneline`
- 审查提案：阅读 `docs/` 目录下的文件
