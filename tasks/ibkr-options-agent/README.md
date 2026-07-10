# IBKR Options Agent

用 **Interactive Brokers (IBKR)** 复制「AI Agent 自主交易美股期权」实验的可运行脚手架。

参考形态：Agent 盯盘 → 结合 QQQ/SMH 等确认 → 下期权限价单 → 自己管仓 → 日记记账。默认 **纸交易 + DRY_RUN**，风控比原文 Day-6（单笔约 41% 仓位）紧得多。

> 这不是投资建议。期权可归零；自动化下单有真实资金风险。先 Paper，再考虑实盘。

---

## 能不能用 IBKR 复制？

**可以。** IBKR 提供 TWS / IB Gateway API，足够覆盖该实验需要的能力：

| 能力 | IBKR 怎么做 |
|------|-------------|
| 盯盘 / 行情 | `reqMktData` / `reqTickers`（股票 + 期权链） |
| 下单买卖 | `placeOrder` 限价单（本项目只用 Limit） |
| 持仓管理 | `positions` + 平仓单 |
| 账户权益 | `accountSummary`（NetLiquidation 等） |
| 纸交易 | Paper 账户端口 `7497`（TWS）/ `4002`（Gateway） |

你需要：

1. IBKR 账户，并开通 **美股期权** 交易权限  
2. 本机运行 **TWS** 或 **IB Gateway**，开启 API（Enable ActiveX and Socket Clients）  
3. 期权相关 **行情订阅**（美股期权通常要额外 market data）  
4. 一个 OpenAI 兼容的 LLM Key（OpenAI / OpenRouter / 自建 moon-bridge 等）

---

## 快速开始

```bash
cd tasks/ibkr-options-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env：填 LLM_API_KEY；确认 IBKR_PORT=7497（Paper）

# 先跑不连券商的单测
pytest -q

# TWS/Gateway 已登录 Paper 后：
python src/main.py --once          # 单轮决策（默认 DRY_RUN，不会真下单）
python src/main.py                 # 盘中循环
python src/main.py --summary       # 写当日权益快照
```

### 端口速查

| 模式 | TWS | Gateway |
|------|-----|---------|
| Paper | 7497 | 4002 |
| Live | 7496 | 4001 |

实盘需要同时满足：`.env` 里 `DRY_RUN=false` **且** `config.yaml` 里 `risk.allow_live: true`。

---

## 目录

```
ibkr-options-agent/
├── README.md
├── requirements.txt
├── .env.example
├── config.yaml              # 标的、确认品种、风控、交易时段
├── prompts/system.md        # Agent 系统提示词
├── src/
│   ├── main.py              # 主循环
│   ├── ibkr_client.py       # 行情 / 期权链 / 下单
│   ├── agent.py             # LLM 结构化决策
│   ├── risk.py              # 硬风控门闩
│   ├── journal.py           # JSONL 日记 + 日结
│   ├── session.py           # 美东 RTH 窗口
│   └── settings.py
└── tests/test_risk.py
```

---

## 和原文 Day-6 的对应关系

原文示例：`RIVN 2024-07-19 17.5C`，买 3 @ 0.73 / 卖 3 @ 0.63，约占账户 41%。

本脚手架默认：

- 标的池含 `RIVN`，确认品种 `QQQ` + `SMH`（可在 `config.yaml` 改）
- `max_position_pct: 0.15` —— **会挡住** 那种 41% 单笔（单测覆盖）
- 决策要求模型写出 `market_view` + `confirmation`，贴近「价位收回 + ETF 确认」叙事
- `logs/journal.jsonl` / `logs/daily_*.md` 对应「只记录、少干预」的日记习惯

---

## 风控（务必读）

- 默认 `DRY_RUN=true`：只记日志，不向 IBKR 提交订单  
- `risk.allow_live=false`：即使关掉 DRY_RUN 也会拒单  
- 单笔 / 总期权权利金占比、单日下单次数、最低权益均有硬顶  
- 只下限价单，不用市价单  

把 `universe.underlyings` 收窄、把 `max_position_pct` 再降，是上线前最有效的两步。

---

## 常见坑

1. **连不上** — TWS 未开 API、端口错、clientId 冲突  
2. **期权链为空** — 无期权行情权限，或标的当日无足够到期日  
3. **LLM 乱下单** — 靠 `risk.py` 硬拦；不要先关风控  
4. **时区** — 默认按 `America/New_York` 的 09:35–15:50 交易  

---

## 状态

| 项 | 值 |
|----|----|
| 创建 | 2026-07-10 |
| 用途 | IBKR 自主期权 Agent POC |
| 依赖本机 | TWS/Gateway + LLM API |
