# AgentCloud Misc 🛠️

**杂项任务收容所** — Agent Cloud 生态中那些不够格独立成项目的、一次性的、实验性的、临时性的活都放这儿。

> 一个项目目录满了，零碎的工作就不会散落在各处。

---

## 设计原则

| 原则 | 说明 |
|------|------|
| **低门槛** | 不需要完整项目脚手架，脚本即文件 |
| **可追溯** | 每个脚本/配置/文档都要标用途和日期 |
| **用完即走** | 实验性成果或沉淀成独立项目，或归档到 `archived/` |
| **能跑就够** | 不追求工程完美，能解决问题就行 |

## 目录结构

```
agentcloud-misc/
├── README.md           # 本文件
├── scripts/            # 一次性/临时脚本
│   ├── 2026-07-10_xxx.sh  # 带日期的命名惯例
│   └── ...
├── configs/            # 配置文件片段、template、env 示例
├── docs/               # 临时文档、笔记、研究记录
├── archived/           # 废弃 / 下沉的旧活，保留参考价值
└── .gitignore
```

### 命名惯例

- **脚本**: `YYYY-MM-DD_简短描述.后缀`
- **配置**: `用途.后缀`（如 `openrouter-templates.yaml`）
- **文档**: `YYYY-MM-DD_主题.md`

## 什么放这里

✅ **合适入住的租户：**

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

### 添加新活

```bash
# 1. 创建一个带日期的脚本
touch scripts/$(date +%Y-%m-%d)_简短描述.sh
chmod +x $_

# 2. 写完后提交
git add -A
git commit -m "add: 简短描述"
git push
```

### 存档旧活

定期（建议每季度）清理 `scripts/`，把不再有用的挪到 `archived/` 或删除：

```bash
mkdir -p archived/2026-Q2
mv scripts/2026-01-* archived/2026-Q2/
```

### 沉淀为独立项目

当一个脚本/工具开始被频繁使用、需要 issue 管理、或需要 CI：

1. 在本仓库记一笔迁移记录
2. 创建独立 repo
3. 从 `archived/` 引用链接

---

## 当前内容

<!-- 用 `tree --gitignore` 自动更新 -->
<!-- 手动维护的清单，每次提交后顺手更新 -->

暂无（新仓库）。

---

## 相关项目

| 项目 | 位置 | 用途 |
|------|------|------|
| [moon-bridge](../moon-bridge/) | `~/Projects/infra/moon-bridge/` | 协议转换与模型路由代理 |
| [video-extract](../video-extract/) | `~/Projects/infra/video-extract/` | 视频/音频提取工具 |
