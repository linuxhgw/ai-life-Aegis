---
name: git-auto-commit
version: 2.0.0
description: |
  检查 git 变更，按最小提交单元拆分，自主执行多次 git add + git commit。
  触发场景：用户说"检查 git 变更并提交"、"帮我提交"、"提交一下"。
  核心逻辑：有变更 → 按文件/逻辑单元拆分 → 逐次提交 / 不符合说明原因。
triggers:
  - 检查 git 变更并提交
  - 帮我提交
  - 有未提交的变更吗
  - 自动提交
  - git commit
  - 提交一下
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# /git-auto-commit — 检查 git 变更并自动提交

根据最小提交单元原则，将未提交变更拆分为多个独立提交，逐次执行。

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

1. `git status` + `git diff --stat` 查看所有未提交变更
2. **按最小单元拆分**：
   - 若多个文件属于同一功能/逻辑 → 合并为一个提交
   - 若文件彼此独立 → 每个（或每组）单独提交
   - 优先按文件粒度拆分，确保每个提交只做一件事
3. 为每个拆分单元生成独立的三段式中文 commit message
4. 逐个执行 `git add <文件>` + `git commit`
5. 若某单元不符合提交规范 → 跳过并说明原因
6. 向用户汇报所有提交结果

## 拆分示例

**场景**：未提交文件有 `src/auth.js`、`src/user.js`、`docs/api.md`

- `src/auth.js` 单独修改登录逻辑 → `git add src/auth.js && git commit -m "fix(auth): 修复登录态校验逻辑"`
- `src/user.js` 单独修改用户信息 → `git add src/user.js && git commit -m "feat(user): 新增用户等级字段"`
- `docs/api.md` 单独文档更新 → `git add docs/api.md && git commit -m "docs(api): 补充用户等级接口说明"`

**场景**：`src/auth.js` + `tests/auth.test.js` 同属登录修复

- 合并提交 → `git add src/auth.js tests/auth.test.js && git commit -m "fix(auth): 修复登录态校验并补充测试"`

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
- **拆分优先**：宁可多次小提交，不要一次大杂烩提交
- 始终使用中文提交信息
- 每个提交只做一件事
- 不合并无关变更到同一提交
- 破坏性操作需先确认，不擅自提交
