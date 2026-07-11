# A-share Research Lab

把「科学做法」落成可执行流程：**假设卡 → 防前视检查 → 成交模型 → 训练/验证/测试切分 → 门禁 → 报告**。

不是荐股系统。默认对测试集门禁失败就判 **REJECT**。

## 流程

```
hypotheses/*.yaml  声明可证伪主张
        │
        ▼
   lint（决策时点能否看到这些字段）
        │ fail → 直接 REJECT（可用 --force 强跑作对照）
        ▼
   train / val / test（中间留 purge gap）
        │
        ▼
   fill model + 费用
        │
        ▼
   gates（笔数 / 期望 / 盈亏比 / 回撤）
        │
        ▼
   results/<id>/report.md
```

## 快速开始

```bash
cd tasks/ashare-research-lab
pip install -r requirements.txt

# 需要日线 panel（复用隔壁任务缓存即可）
# ../ashare-xhs-strategy-backtest/data/panel_daily.parquet

python cli.py list
python cli.py lint hypotheses/H002_lookahead_bad.yaml   # 应失败
python cli.py run  hypotheses/H001_open_gap_hot.yaml
python cli.py run-all
```

## 目录

| 路径 | 作用 |
|------|------|
| `hypotheses/` | 假设卡（主张、决策时点、成交、参数） |
| `strategies/` | 策略实现；必须声明 `decision_columns` |
| `lab/` | 数据、切分、成交、指标、检查、引擎、报告 |
| `config/default.yaml` | 费用、切分、门禁 |
| `results/` | 每次运行的报告与成交明细 |

## 内置假设

| ID | 内容 | 预期/结果 |
|----|------|-----------|
| H001 | 开盘缺口+昨量比+热点（无前视） | REJECT |
| H002 | 故意用当日量比在开盘决策 | lint REJECT |
| H003 | 跌停抄底规则化 | REJECT |
| H004 | 涨停+成交额打板（保守成交） | REJECT（代理+压力测试） |
| H005 | 昨市偏强后开盘低开均值回归 | **CANDIDATE**（仍需模拟盘） |

## 如何加一个新假设

1. 在 `strategies/` 写类，声明 `decision_columns`（开盘决策不要碰 `volume/close/vol_ratio_eod`）
2. 在 `hypotheses/` 加 YAML，写清 `claim` / `decision_time` / `fill_model`
3. `python cli.py run hypotheses/H00X_....yaml`
4. 只有 **lint + test gates** 都过，才叫候选；然后才谈模拟盘

## 判定等级

| 等级 | 含义 |
|------|------|
| `REJECT` | lint / 假设 / 指标 / 成交压力测试未过 |
| `WEAK_CANDIDATE` | 数字勉强过，但代理指标或成交假设偏弱 |
| `CANDIDATE` | 假设相对诚实，且 val+test 过门禁 |

只看收益曲线不够：`amount` 冒充净流入、默认买到涨停，最多 `WEAK_CANDIDATE`，默认进不了 `CANDIDATE`。

## 门禁（默认）

- 测试集成交笔数 ≥ 30；验证集 ≥ 15
- **验证集与测试集**期望值都 > 0、盈亏比 ≥ 1.05、最大回撤优于 -35%
- 危险代理（如成交额当净流入）⇒ 不能当 CANDIDATE
- 涨停成交模型会强制跑 **次日开盘追价** 压力测试
- 前视 lint 失败直接 REJECT（除非 `--force`）
