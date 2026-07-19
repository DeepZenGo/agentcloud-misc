# 减脂作息看板

个人本机网页：展示 Hermes 减脂作息系统的**今日状态**、日程、本周合规，以及方案与研究摘要。

数据源与 CLI 相同：`~/.hermes/habit-track/daily-log.json`（只读，不在网页打卡）。

## 启动

```bash
cd tasks/fat-loss-board
npm install
npm run dev
```

- 页面：http://127.0.0.1:5173
- API：http://127.0.0.1:8787/api/status

可选环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `HABIT_LOG_FILE` | `~/.hermes/habit-track/daily-log.json` | 打卡 JSON 路径 |
| `PORT` | `8787` | API 端口 |

对照 CLI：

```bash
python3 ~/.hermes/scripts/habit-tracker.py report
python3 ~/.hermes/scripts/habit-tracker.py week
```

## 结构

- `server/` — Express `GET /api/status`
- `src/components/` — Today / Timeline / Week / Plan / Evidence
- `src/lib/` — 相位、streak、周汇总（与 habit-tracker 对齐）

## 说明

本任务为 agentcloud-misc 下的 POC，仅本机使用；提醒仍由 Hermes cron 负责。
