# 减脂作息看板

个人本机网页：展示 Hermes 减脂作息系统的**今日状态**、日程、本周合规，以及方案与研究摘要。

数据源与 CLI 相同：`~/.hermes/habit-track/daily-log.json`（只读，不在网页打卡）。

## 手机 / Tailscale 访问（推荐）

先构建并单进程托管（API + 静态页，监听 `0.0.0.0:5173`）：

```bash
cd tasks/fat-loss-board
npm install
npm start
```

然后用手机浏览器打开（必须是 **http**，不要写成 https）：

- `http://100.103.178.110:5173`
- 或 MagicDNS：`http://amacbook-pro:5173`（需开启 MagicDNS）

前提：手机 Tailscale 已登录同一账号并在线。本机终端里应能看到类似：

```text
[fat-loss-board] tailscale http://100.103.178.110:5173
```

若仍打不开：在 Mac 上执行 `curl -I http://100.103.178.110:5173`，应返回 `200`。

## 本机开发

```bash
npm run dev
```

- 本机：http://127.0.0.1:5173
- API（开发）：http://127.0.0.1:8787/api/status（页面经 Vite 代理 `/api`）

可选环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `HABIT_LOG_FILE` | `~/.hermes/habit-track/daily-log.json` | 打卡 JSON 路径 |
| `PORT` | `8787`（dev api）/ `5173`（`npm start`） | 监听端口 |
| `HOST` | `0.0.0.0` | 绑定地址 |
| `SERVE_STATIC` | `1`（`npm start`） | 同时托管 `dist/` |

对照 CLI：

```bash
python3 ~/.hermes/scripts/habit-tracker.py report
python3 ~/.hermes/scripts/habit-tracker.py week
```

## 结构

- `server/` — Express `/api/*`，可选托管 `dist/`
- `src/components/` — Today / Timeline / Week / Plan / Evidence
- `src/lib/` — 相位、streak、周汇总（与 habit-tracker 对齐）

## 说明

本任务为 agentcloud-misc 下的 POC，仅本机 / Tailscale 使用；提醒仍由 Hermes cron 负责。
