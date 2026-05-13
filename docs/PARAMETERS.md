# 参数说明

本文档详细说明 聪明钱交易者 的所有配置参数。

---

## 参数总览

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `risk_per_trade` | number | ❌ | 5.0 | 单笔风险占账户净值百分比 |
| `max_daily_trades` | integer | ❌ | 10 | 每日最大交易笔数 |
| `max_concurrent_positions` | integer | ❌ | 5 | 最大并发持仓数 |
| `daily_drawdown_limit` | number | ❌ | 10 | 日回撤熔断阈值（%） |
| `min_smart_money_wallets` | integer | ❌ | 3 | 最小聪明钱钱包数 |
| `signal_window_minutes` | integer | ❌ | 60 | 信号时间窗口（分钟） |
| `take_profit_tiers` | number[] | ❌ | [2.0, 5.0, 10.0] | 分层止盈倍数 |
| `sell_ratio_tiers` | number[] | ❌ | [0.33, 0.33, 0.34] | 对应卖出比例 |
| `stop_loss_pct` | number | ❌ | 20 | 止损百分比（%） |
| `trailing_stop_activate` | number | ❌ | 50 | 移动止损激活盈利（%） |
| `chain` | string | ❌ | solana | 链（当前仅支持 solana） |
| `profile` | string | ❌ | demo | 实盘 live / 模拟盘 demo |

---

## 详细说明

### 1. risk_per_trade（单笔风险）

**类型**：number
**默认值**：5.0
**范围**：1.0 - 20.0
**说明**：单笔交易风险占账户净值的百分比

**示例**：
```
账户净值 = $10,000
risk_per_trade = 5%
风险金额 = $500
```

**调整建议**：
- 保守型：1-3%
- 平衡型：5%
- 激进型：10-20%

### 2. max_daily_trades（每日最大交易）

**类型**：integer
**默认值**：10
**范围**：1 - 50
**说明**：每天最多执行的交易笔数

### 3. max_concurrent_positions（最大并发持仓）

**类型**：integer
**默认值**：5
**范围**：1 - 10
**说明**：同时持有的最大仓位数量

### 4. daily_drawdown_limit（日回撤熔断）

**类型**：number
**默认值**：10
**范围**：5 - 30
**说明**：日回撤达到此百分比时，停止所有开仓直至次日

### 5. min_smart_money_wallets（最小聪明钱钱包数）

**类型**：integer
**默认值**：3
**范围**：1 - 10
**说明**：触发入场所需的最小聪明钱钱包数量

**调整建议**：
- 宽松：1-2 个钱包
- 标准：3-5 个钱包
- 严格：≥ 5 个钱包

### 6. signal_window_minutes（信号时间窗口）

**类型**：integer
**默认值**：60
**范围**：15 - 180
**说明**：只保留最近多少分钟内的聪明钱信号

### 7. take_profit_tiers（分层止盈倍数）

**类型**：number[]
**默认值**：[2.0, 5.0, 10.0]
**说明**：各层止盈的目标倍数

**示例**：
```
take_profit_tiers = [2.0, 5.0, 10.0]
入场价 = $100
TP1 = $200（2倍）
TP2 = $500（5倍）
TP3 = $1000（10倍）
```

### 8. sell_ratio_tiers（对应卖出比例）

**类型**：number[]
**默认值**：[0.33, 0.33, 0.34]
**说明**：各层止盈时卖出的比例，总和应为 1.0

**示例**：
```
sell_ratio_tiers = [0.33, 0.33, 0.34]
TP1 触发：卖出 33% 持仓
TP2 触发：卖出 33% 持仓
TP3 触发：卖出 34% 持仓
```

### 9. stop_loss_pct（止损百分比）

**类型**：number
**默认值**：20
**范围**：5 - 50
**说明**：止损线距离入场价的百分比

**示例**：
```
入场价 = $100
stop_loss_pct = 20%
止损价 = $80（价格下跌 20% 触发）
```

### 10. trailing_stop_activate（移动止损激活盈利）

**类型**：number
**默认值**：50
**范围**：20 - 100
**说明**：盈利达到此百分比后激活移动止损

**示例**：
```
入场价 = $100
trailing_stop_activate = 50%
激活条件：当前价格 ≥ $150（盈利 50%）
激活后：回撤 10% 止损（$135）
```

### 11. chain（链）

**类型**：string
**默认值**：solana
**可选值**：solana
**说明**：交易所在的区块链网络

**注意**：当前仅支持 Solana 链

### 12. profile（配置文件）

**类型**：string
**默认值**：demo
**可选值**：demo, live
**说明**：运行环境配置

| 值 | 说明 |
|----|------|
| `demo` | 模拟盘，不真实交易 |
| `live` | 实盘，真实交易 |

---

## 参数组合示例

### 保守型配置

```yaml
risk_per_trade: 2.0
max_daily_trades: 5
max_concurrent_positions: 2
daily_drawdown_limit: 5
min_smart_money_wallets: 5
stop_loss_pct: 15
trailing_stop_activate: 30
```

### 平衡型配置

```yaml
risk_per_trade: 5.0
max_daily_trades: 10
max_concurrent_positions: 5
daily_drawdown_limit: 10
min_smart_money_wallets: 3
stop_loss_pct: 20
trailing_stop_activate: 50
```

### 激进型配置

```yaml
risk_per_trade: 10.0
max_daily_trades: 20
max_concurrent_positions: 10
daily_drawdown_limit: 20
min_smart_money_wallets: 2
stop_loss_pct: 30
trailing_stop_activate: 100
```

---

## 参数调整建议

### 根据市场环境调整

| 市场环境 | 建议调整 |
|----------|----------|
| 牛市 | 放宽 `min_smart_money_wallets`，增加 `max_daily_trades` |
| 熊市 | 收紧 `min_smart_money_wallets`，减少 `risk_per_trade` |
| 震荡 | 保持默认参数，专注信号质量 |
| 高波动 | 增加 `stop_loss_pct`，减少 `max_concurrent_positions` |

### 根据个人风险承受能力调整

| 风险偏好 | 建议调整 |
|----------|----------|
| 保守 | `risk_per_trade: 1-3%`, `stop_loss_pct: 10-15%` |
| 平衡 | `risk_per_trade: 5%`, `stop_loss_pct: 20%` |
| 激进 | `risk_per_trade: 10-20%`, `stop_loss_pct: 30%+` |

---

*最后更新：2026-05-13*
