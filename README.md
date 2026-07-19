# AgentCloud Misc 🛠️

**杂项任务收容所** — Agent Cloud 生态中那些不够格独立成项目的、一次性的、实验性的、临时性的活都放这儿。

> 一个项目目录满了，零碎的工作就不会散落在各处。

**一任务一目录 · 随时可能转正** — 每个任务放在 `tasks/<task-name>/`；成熟后可随时迁出成独立项目。

---

## 设计原则

| 原则 | 说明 |
|------|------|
| **低门槛** | 不需要完整项目脚手架，脚本即文件 |
| **可追溯** | 每个脚本/配置/文档都要标用途和日期；任务在下方清单登记 |
| **一任务一目录** | 相关内容都放进该任务文件夹，不散落混放 |
| **用完即走** | 实验性成果或沉淀成独立项目，或归档到 `archived/` |
| **能跑就够** | 不追求工程完美，能解决问题就行 |

## 目录结构

```
agentcloud-misc/
├── README.md           # 本文件（说明 + 任务清单）
├── tasks/              # 每个任务一个独立子文件夹
│   └── <task-name>/
├── scripts/            # 一次性/临时脚本（非任务型零碎）
│   ├── 2026-07-10_xxx.sh  # 带日期的命名惯例
│   └── ...
├── configs/            # 配置文件片段、template、env 示例
├── docs/               # 临时文档、笔记、研究记录
├── archived/           # 废弃 / 下沉的旧活，保留参考价值
└── .gitignore
```

### 命名惯例

- **任务目录**: `tasks/<简短英文或拼音名>/`
- **脚本**: `YYYY-MM-DD_简短描述.后缀`
- **配置**: `用途.后缀`（如 `openrouter-templates.yaml`）
- **文档**: `YYYY-MM-DD_主题.md`

## 什么放这里

✅ **合适入住的租户：**

- 有明确边界、可能日后转正的小任务 → `tasks/<task-name>/`
- 一次性的数据清洗/迁移脚本
- 临时 API 集成测试
- Agent 编排的实验性 prompt/skill 草案
- 环境配置快照（.env 模板、config.yaml 片段）
- 跨项目共用的辅助脚本（如通知、日志轮转）
- 快速原型/概念验证（POC）
- 系统运维的临时工具（磁盘清理、进程管理）

❌ **不合适：**

- 有自己的 CI/CD、issue tracker、release 周期的成熟项目 → [独立项目]
- 持续运行的服务 → 应该有自己的 repo
- 敏感凭据 → 永远不要提交到 git

## 使用指南

### 添加新任务

```bash
# 1. 为任务建独立目录
mkdir -p tasks/<task-name>

# 2. 在目录内放脚本/配置/笔记，并在下方「当前任务」表登记

# 3. 提交
git add -A
git commit -m "add: <task-name> 简短描述"
git push
```

### 添加零碎脚本（非任务型）

```bash
touch scripts/$(date +%Y-%m-%d)_简短描述.sh
chmod +x $_
```

### 存档旧活

定期（建议每季度）清理，把不再有用的挪到 `archived/` 或删除：

```bash
mkdir -p archived/2026-Q2
mv tasks/<旧任务名> archived/2026-Q2/
# 或
mv scripts/2026-01-* archived/2026-Q2/
```

### 沉淀为独立项目（转正）

当一个任务开始被频繁使用、需要 issue 管理、或需要 CI：

1. 创建独立 repo，迁入内容
2. 下方清单将该行状态改为 `已转正`，并填上新项目链接
3. 原目录挪到 `archived/` 或删除（按需保留参考）

---

## 当前任务

| 任务 | 路径 | 状态 | 备注 |
|------|------|------|------|
| 减脂作息看板 | — | 已转正 | 迁至 `~/Projects/_misc/fat-loss-board` |

状态取值：`进行中` · `已归档` · `已转正`

---

## 相关项目

| 项目 | 位置 | 用途 |
|------|------|------|
| [moon-bridge](../moon-bridge/) | `~/Projects/infra/moon-bridge/` | 协议转换与模型路由代理 |
| [video-extract](../video-extract/) | `~/Projects/infra/video-extract/` | 视频/音频提取工具 |
| [fat-loss-board](../../_misc/fat-loss-board/) | `~/Projects/_misc/fat-loss-board/` | 减脂作息看板（已转正） |
