---
name: git-auto-commit
version: 1.0.0
description: |
  检查 git 变更，判断是否符合提交规范，符合则自主执行 git add + git commit。
  触发场景：用户说"检查 git 变更"、"帮我提交"、对话结束前主动调用。
  核心逻辑：有变更 → 判断是否完整 → 符合规范提交 / 不符合说明原因。
triggers:
  - 检查 git 变更并提交
  - 帮我提交
  - 有未提交的变更吗
  - 自动提交
  - git commit
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# /git-auto-commit — 检查 git 变更并自动提交

根据最小提交单元原则，判断当前变更是否构成完整提交，符合规范则自主提交。

## 判断标准

### 构成完整提交（需全部满足）

- 有 staged 或 unstaged 变更
- 变更属于同一功能/修复/改动
- 可以用一句 subject 描述清楚
- 是独立、可验证的单元

### 不构成提交

- 仅有格式、注释、空行调整
- 变更不完整、无法单独验证
- 涉及破坏性改动而未经确认

## 执行流程

1. `git status` + `git diff --stat` 查看变更范围
2. 判断是否满足完整提交标准
3. 符合规范 → 生成三段式中文 commit message → `git add` + `git commit`
4. 不符合规范 → 不提交，向用户说明原因
5. 向用户汇报结果

## 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

| 字段 | 说明 |
|------|------|
| type | feat / fix / docs / style / refactor / test / chore |
| scope | 影响范围，如模块或目录名 |
| subject | 不超过 50 字，祈使语气，陈述句 |
| body | 详细说明（可选），解释 why 而非 what |
| footer | BREAKING CHANGE / Closes #issue（可选） |

## 示例

```
docs(specs): 添加 Aegis 个人生活助手设计文档

- 新增 docs/superpowers/specs/2026-05-05-aegis-design.md
- 包含系统架构、核心模块、技术路线
```

## 核心原则

- **最小提交单元**：一个提交 = 一个功能 = 一件完整、可独立验证、可回滚的事
- 始终使用中文提交信息
- 每个提交只做一件事
- 不合并无关变更到同一提交
- 破坏性操作需先确认，不擅自提交
