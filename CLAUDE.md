# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码仓库中工作时提供指导。

## 通用约定

- 所有回复使用中文
- 所有 git commit 使用中文

## 自动提交机制

每次对话结束时，Stop hook 检测 git 变更：
- 有变更 → 调用 `git-auto-commit` skill
- 无变更 → 结束

`git-auto-commit` skill 根据提交规范判断变更是否构成完整提交：
- **符合规范** → 自主提交
- **不符合规范** → 不提交，向用户说明原因

## 目录结构

```
ai-life-Aegis/
├── .claude/
│   ├── settings.json               # Stop hook 配置
│   └── skills/
│       └── git-auto-commit.md     # Git 提交规范与自动提交逻辑
├── docs/                            # 设计文档与方案
└── CLAUDE.md
```
