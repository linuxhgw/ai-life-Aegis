---
name: git-auto-commit
description: 每次对话结束后自动判断是否存在未提交的 git 变更，若构成完整提交则自主提交
---

# Git 自动提交 Skill

## 触发时机

对话结束（Stop hook）时自动执行。

## 判断标准

**构成完整提交的条件（全部满足）：**
- 有 staged 或 unstaged 变更
- 变更属于同一功能/修复/改动
- 可以用一句 subject 描述清楚
- 是独立、可验证的单元

**不构成提交的情况：**
- 仅有格式、注释、空行调整
- 变更不完整、无法单独验证
- 涉及破坏性改动（如删除重要文件）而未经确认

## 提交流程

1. `git status` 查看变更范围
2. 判断是否满足完整提交标准
3. 如满足，按三段式格式生成 commit message：
   - type：feat / fix / docs / refactor 等
   - scope：影响的模块或目录
   - subject：不超过 50 字，祈使语气
   - body：简要说明变更内容（可选）
4. 执行 `git add` + `git commit`
5. 向用户汇报提交结果

## 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

示例：
```
docs(specs): 添加 Aegis 个人生活助手设计文档

- 新增 docs/superpowers/specs/2026-05-05-aegis-design.md
- 包含系统架构、核心模块、技术路线

Closes #1
```

## 注意事项

- 始终使用中文提交信息
- 每个提交只做一件事
- 不合并无关变更到同一提交
- 破坏性操作需先确认
