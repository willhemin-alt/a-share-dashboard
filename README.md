# A-share Dashboard

个人 A 股模拟账户与看板。第一阶段先把“连续账本 + 可验证分钟价格 + GitHub Actions + GitHub Pages”跑通。

## 当前实现

- 初始资金 ¥100,000，起始日 2026-08-17；账本不每日重置。
- 尾盘：读取 `config/candidates.json` 中**事先批准**的候选，使用 AKShare / 东方财富 1 分钟历史数据寻找 14:50 附近可验证价格；无价格则不成交。
- 次日早盘：对持仓使用 09:35 附近可验证分钟价模拟卖出；无可靠价格则继续持有。
- 100 股为一手；单股上限 35%，总仓位上限 70%。
- 默认费用假设：佣金 0.025%（最低 ¥5）、卖出印花税 0.05%、过户费 0.001%。全部可在 `config/settings.json` 修改。
- `docs/index.html` 为静态 Dashboard，可用 GitHub Pages 发布。

## 为什么 14:50 的 Action 设置为 14:55 北京时间

GitHub Actions 的 schedule 并不保证秒级准时。工作流在 06:55 UTC 触发，脚本不是拿“运行当下”的现价，而是读取当天 1 分钟历史数据并寻找 **14:50** 附近的真实分钟 K，因此即使 Action 晚几分钟启动，也不会把晚到的价格冒充 14:50。

AKShare 的 `stock_zh_a_hist_min_em` 1 分钟数据只保留近期数据，因此每天及时落盘很重要。

## 候选输入

`config/candidates.json` 示例：

```json
{
  "trade_date": "2026-08-31",
  "market_ok": true,
  "market_note": "市场赚钱效应达到隔夜超短交易标准",
  "candidates": [
    {
      "code": "000878",
      "name": "云南铜业",
      "approved": true,
      "reason": "涨停线索来自江西铜业；铜价与利润弹性逻辑映射，尚未涨停且量价确认"
    }
  ]
}
```

第一版**故意不把杨永兴的新闻/题材推理机械化**。这是为了避免把互联网总结的固定阈值冒充其本人方法。后续第二阶段再接入自动新闻研究/候选生成模块，并保留每次推理的审计记录。

## GitHub Pages

仓库 `Settings → Pages → Build and deployment → Source` 选择 **GitHub Actions**。随后运行 `Deploy Pages` workflow。

## 手动测试

```bash
pip install -r requirements.txt
python scripts/build_dashboard.py
python scripts/tail_buy.py
python scripts/morning_sell.py
```

> 仅为模拟研究，不构成投资建议。
