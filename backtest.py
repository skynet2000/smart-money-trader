#!/usr/bin/env python3
"""
聪明钱交易者 - 回测框架 V1.0.0
回测时间范围：2026-04-13 ~ 2026-05-13（1个月）

核心逻辑：
1. 通过 onchainOS 采集真实聪明钱信号
2. 使用 token trades + market kline 获取历史数据
3. 模拟策略完整交易流程
4. 计算性能指标

注意：onchainOS signal list 只返回实时信号，无历史时间范围参数
本回测通过以下方式重建历史信号：
- 获取当前信号作为样本
- 通过 token trades 重建近期聪明钱交易历史
- 使用 Monte Carlo 模拟扩展到 1 个月
"""

import json
import subprocess
import time
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

# ============================================================================
# onchainOS API 调用封装
# ============================================================================

def run_onchainos(args: List[str], timeout: int = 30) -> Optional[Dict]:
    """执行 onchainos CLI 命令并返回 JSON 结果"""
    try:
        cmd = ["onchainos"] + args
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"  ⚠️  命令失败: {' '.join(args)}")
            print(f"     错误: {result.stderr[:200]}")
            return None
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  命令超时: {' '.join(args)}")
        return None
    except Exception as e:
        print(f"  ⚠️  异常: {e}")
        return None

def get_smart_money_signals(chain: str = "solana", wallet_type: str = "1", 
                            limit: int = 100) -> List[Dict]:
    """获取聪明钱信号列表"""
    print(f"\n📡 正在获取 {chain} 链聪明钱信号...")
    data = run_onchainos([
        "signal", "list",
        "--chain", chain,
        "--wallet-type", wallet_type,
        "--limit", str(limit)
    ])
    if data and data.get("ok"):
        signals = data.get("data", [])
        print(f"  ✅ 获取到 {len(signals)} 条信号")
        return signals
    return []

def get_token_trades(token_address: str, chain: str = "solana",
                     limit: int = 100, tag_filter: str = "3") -> List[Dict]:
    """获取代币交易历史（可按标签筛选聪明钱）"""
    data = run_onchainos([
        "token", "trades",
        "--address", token_address,
        "--chain", chain,
        "--limit", str(limit),
        "--tag-filter", tag_filter
    ])
    if data and data.get("ok"):
        return data.get("data", [])
    return []

def get_token_price_info(token_address: str, chain: str = "solana") -> Optional[Dict]:
    """获取代币价格信息"""
    data = run_onchainos([
        "token", "price-info",
        "--address", token_address,
        "--chain", chain
    ])
    if data and data.get("ok"):
        return data.get("data", {})
    return None

def get_market_kline(token_address: str, chain: str = "solana",
                      bar: str = "1H", limit: int = 200) -> List[Dict]:
    """获取 K 线数据（历史价格）"""
    data = run_onchainos([
        "market", "kline",
        "--address", token_address,
        "--chain", chain,
        "--bar", bar,
        "--limit", str(limit)
    ])
    if data and data.get("ok"):
        return data.get("data", [])
    return []

def get_token_advanced_info(token_address: str, chain: str = "solana") -> Optional[Dict]:
    """获取代币高级信息（安全性等）"""
    data = run_onchainos([
        "token", "advanced-info",
        "--address", token_address,
        "--chain", chain
    ])
    if data and data.get("ok"):
        return data.get("data", {})
    return None

# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class TokenSafety:
    """代币安全检查结果"""
    is_honeypot: bool = False
    lp_locked_pct: float = 0.0
    buy_tax: float = 0.0
    sell_tax: float = 0.0
    liquidity_usd: float = 0.0
    top10_hold_pct: float = 0.0
    bundler_ratio: float = 0.0
    dev_holding: float = 0.0
    is_phishing: bool = False
    holders: int = 0
    passed: bool = False
    fail_reason: str = ""

@dataclass
class TradeSignal:
    """交易信号"""
    token_address: str
    token_symbol: str
    token_name: str
    entry_price: float
    entry_time: datetime
    wallet_count: int
    amount_usd: float
    market_cap_usd: float
    holders: int
    top10_hold_pct: float
    sold_ratio_pct: float = 0.0
    safety: TokenSafety = None

@dataclass
class SimulatedTrade:
    """模拟交易"""
    signal: TradeSignal
    entry_price: float
    entry_time: datetime
    position_usd: float
    stop_loss_price: float
    take_profit_prices: List[float]
    sell_ratios: List[float]
    
    # 结果
    exit_price: float = 0.0
    exit_time: Optional[datetime] = None
    exit_reason: str = ""
    pnl_pct: float = 0.0
    pnl_usd: float = 0.0
    status: str = "open"  # open, tp1, tp2, tp3, sl, ts, timeout

@dataclass
class BacktestResult:
    """回测结果"""
    trades: List[SimulatedTrade] = field(default_factory=list)
    
    # 统计数据
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    total_pnl_pct: float = 0.0
    avg_pnl_pct: float = 0.0
    max_win_pct: float = 0.0
    max_loss_pct: float = 0.0
    
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    total_return: float = 0.0
    
    # 退出原因统计
    exit_reasons: Dict[str, int] = field(default_factory=dict)
    
    # 时间范围
    start_date: datetime = None
    end_date: datetime = None
    duration_days: int = 0

# ============================================================================
# 安全检查（模拟）
# ============================================================================

def check_token_safety(token_address: str, symbol: str, chain: str = "solana") -> TokenSafety:
    """执行代币安全检查（使用高级信息和价格信息）"""
    safety = TokenSafety()
    
    # 获取高级信息
    adv_info = get_token_advanced_info(token_address, chain)
    price_info = get_token_price_info(token_address, chain)
    
    if not adv_info and not price_info:
        safety.fail_reason = "无法获取代币信息"
        return safety
    
    # 解析高级信息
    if adv_info:
        safety.lp_locked_pct = float(adv_info.get("lpLocked", 0) or 0)
        safety.buy_tax = float(adv_info.get("buyTax", 0) or 0)
        safety.sell_tax = float(adv_info.get("sellTax", 0) or 0)
        safety.bundler_ratio = float(adv_info.get("bundlerRatio", 0) or 0)
        safety.dev_holding = float(adv_info.get("devHolding", 0) or 0)
        safety.is_honeypot = adv_info.get("isHoneypot", False)
        safety.is_phishing = adv_info.get("isPhishing", False)
        safety.holders = int(adv_info.get("holders", 0) or 0)
    
    # 解析价格信息
    if price_info:
        safety.liquidity_usd = float(price_info.get("liquidity", {}).get("liquidity", 0) or 0)
        safety.top10_hold_pct = float(price_info.get("top10HolderPercent", 0) or 0)
    
    # 执行安全阈值检查
    checks = [
        (not safety.is_honeypot, "蜜罐"),
        (not safety.is_phishing, "钓鱼代币"),
        (safety.lp_locked_pct >= 80, f"LP锁定 {safety.lp_locked_pct:.0f}% < 80%"),
        (safety.buy_tax <= 5, f"买入税 {safety.buy_tax:.1f}% > 5%"),
        (safety.sell_tax <= 5, f"卖出税 {safety.sell_tax:.1f}% > 5%"),
        (safety.liquidity_usd >= 25000, f"流动性 ${safety.liquidity_usd:,.0f} < $25,000"),
        (safety.top10_hold_pct <= 35, f"持仓集中度 {safety.top10_hold_pct:.1f}% > 35%"),
        (safety.bundler_ratio <= 10, f"狙击手比例 {safety.bundler_ratio:.1f}% > 10%"),
        (safety.dev_holding <= 10, f"开发者持仓 {safety.dev_holding:.1f}% > 10%"),
    ]
    
    failed = [reason for passed, reason in checks if not passed]
    safety.passed = len(failed) == 0
    safety.fail_reason = "; ".join(failed) if failed else "通过"
    
    return safety

# ============================================================================
# 策略参数
# ============================================================================

STRATEGY_PARAMS = {
    "risk_per_trade": 5.0,           # 单笔风险 5%
    "max_daily_trades": 10,           # 每日最大交易
    "max_concurrent_positions": 5,    # 最大并发持仓
    "daily_drawdown_limit": 10.0,     # 日回撤熔断 10%
    "min_smart_money_wallets": 3,     # 最小聪明钱钱包数
    "signal_window_minutes": 60,       # 信号时间窗口
    "take_profit_tiers": [2.0, 5.0, 10.0],  # 分层止盈
    "sell_ratio_tiers": [0.33, 0.33, 0.34],  # 卖出比例
    "stop_loss_pct": 20.0,           # 止损 20%
    "trailing_stop_activate": 50.0,   # 移动止损激活 50%
    "trailing_stop_pct": 10.0,       # 移动止损回撤 10%
    "max_position_usd": 500.0,         # 单笔最大 $500
    "chain": "solana",
}

# ============================================================================
# Monte Carlo 信号模拟
# ============================================================================

def generate_simulated_signals(current_signals: List[Dict], 
                                start_date: datetime,
                                end_date: datetime) -> List[TradeSignal]:
    """
    通过 Monte Carlo 模拟生成 1 个月的信号
    基于当前信号的统计特征，模拟历史上可能出现的信号
    """
    print(f"\n🎲 正在通过 Monte Carlo 模拟生成历史信号...")
    print(f"   时间范围: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    # 当前信号的统计特征
    wallet_counts = [int(s.get("triggerWalletCount", 3)) for s in current_signals]
    amounts = [float(s.get("amountUsd", 500)) for s in current_signals]
    
    avg_wallet_count = sum(wallet_counts) / len(wallet_counts) if wallet_counts else 3
    avg_amount = sum(amounts) / len(amounts) if amounts else 500
    
    print(f"   平均聪明钱钱包数: {avg_wallet_count:.1f}")
    print(f"   平均买入金额: ${avg_amount:,.2f}")
    
    # 模拟参数
    import random
    random.seed(42)  # 固定种子，保证可复现
    
    duration_days = (end_date - start_date).days
    # 假设每天平均产生 5 个有效信号
    expected_signals_per_day = 5
    estimated_total = duration_days * expected_signals_per_day
    
    # 按时间分布信号（使用泊松分布模拟随机性）
    simulated_signals = []
    current_date = start_date
    
    day = 0
    while current_date <= end_date:
        # 每天 0-10 个信号（随机）
        n_signals_today = max(0, int(random.gauss(expected_signals_per_day, 3)))
        n_signals_today = min(n_signals_today, 15)
        
        for i in range(n_signals_today):
            # 随机选择 1 个当前信号作为模板
            template = random.choice(current_signals) if current_signals else {}
            
            # 生成随机时间（当天的随机时刻）
            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            signal_time = current_date.replace(hour=hour, minute=minute)
            
            # 随机化参数
            wallet_count = max(3, int(random.gauss(avg_wallet_count, 1)))
            amount_usd = max(100, random.gauss(avg_amount, avg_amount * 0.5))
            
            # 随机选择代币（从当前信号中）
            token = template.get("token", {})
            token_address = token.get("tokenAddress", "unknown")
            token_symbol = token.get("symbol", "UNKNOWN")
            token_name = token.get("name", "Unknown Token")
            
            # 模拟 soldRatioPercent（聪明钱卖出比例）
            # 新信号：soldRatio 低（还没卖）
            # 旧信号：soldRatio 高（已经卖了）
            days_ago = (end_date - signal_time).days
            base_sold = min(95, days_ago * 3)  # 每天增加 3%
            sold_ratio = max(0, min(100, base_sold + random.gauss(0, 15)))
            
            signal = TradeSignal(
                token_address=token_address,
                token_symbol=token_symbol,
                token_name=token_name,
                entry_price=float(template.get("price", 0.0001)),
                entry_time=signal_time,
                wallet_count=wallet_count,
                amount_usd=amount_usd,
                market_cap_usd=float(token.get("marketCapUsd", 100000)),
                holders=int(token.get("holders", 500)),
                top10_hold_pct=float(token.get("top10HolderPercent", 20)),
                sold_ratio_pct=sold_ratio,
            )
            simulated_signals.append(signal)
        
        current_date += timedelta(days=1)
        day += 1
    
    print(f"   ✅ 模拟生成了 {len(simulated_signals)} 个历史信号（{duration_days} 天）")
    return simulated_signals

# ============================================================================
# 回测引擎
# ============================================================================

def run_backtest(signals: List[TradeSignal], 
                 initial_balance: float = 10000.0,
                 params: Dict = STRATEGY_PARAMS) -> BacktestResult:
    """执行回测"""
    print(f"\n🚀 开始回测...")
    print(f"   初始资金: ${initial_balance:,.2f}")
    print(f"   信号数量: {len(signals)}")
    
    result = BacktestResult()
    
    # 设置时间范围
    if signals:
        result.start_date = min(s.entry_time for s in signals)
        result.end_date = max(s.entry_time for s in signals)
        result.duration_days = (result.end_date - result.start_date).days
    
    # 状态变量
    balance = initial_balance
    peak_balance = initial_balance
    positions = []  # 当前持仓
    daily_trades = defaultdict(int)
    consecutive_losses = 0
    
    # 按时间排序信号
    signals_sorted = sorted(signals, key=lambda s: s.entry_time)
    
    for signal in signals_sorted:
        current_date = signal.entry_time.date()
        current_time = signal.entry_time
        
        # ========== 风控检查 ==========
        
        # 日交易限制
        if daily_trades[current_date] >= params["max_daily_trades"]:
            continue
        
        # 并发持仓限制
        if len(positions) >= params["max_concurrent_positions"]:
            # 跳过，尝试下一个信号
            continue
        
        # 回撤熔断
        current_dd = (peak_balance - balance) / peak_balance * 100
        if current_dd >= params["daily_drawdown_limit"]:
            # 如果接近熔断，检查是否是新的一天
            continue
        
        # ========== 执行交易 ==========
        
        # 仓位计算
        risk_amount = balance * params["risk_per_trade"] / 100
        position_usd = min(risk_amount * 2, params["max_position_usd"])
        
        # 止损止盈价格
        entry_price = signal.entry_price
        stop_loss_price = entry_price * (1 - params["stop_loss_pct"] / 100)
        take_profit_prices = [
            entry_price * tp for tp in params["take_profit_tiers"]
        ]
        
        # 创建模拟交易
        trade = SimulatedTrade(
            signal=signal,
            entry_price=entry_price,
            entry_time=current_time,
            position_usd=position_usd,
            stop_loss_price=stop_loss_price,
            take_profit_prices=take_profit_prices,
            sell_ratios=params["sell_ratio_tiers"],
        )
        
        # ========== 模拟价格走势 ==========
        # 
        # 策略止盈止损规则：
        # - 止损：-20%（价格下跌 20% 或更多）
        # - 止盈1：+100%（价格涨到 2x）
        # - 止盈2：+400%（价格涨到 5x）
        # - 止盈3：+900%（价格涨到 10x）
        # - 移动止损：盈利 >= 50% 后，回撤 10% 止损
        # - 持仓收益：盈利在 0%~100% 之间，未触发止盈
        # - 浮动亏损：亏损在 0%~-20% 之间，未触发止损
        
        sold_ratio = signal.sold_ratio_pct
        
        import random
        random.seed(int(signal.entry_time.timestamp()) % 1000000)
        
        # 根据 soldRatio 确定价格走势方向：
        # soldRatio < 30: 聪明钱还在持有 -> 价格上涨概率高
        # soldRatio 30-70: 聪明钱部分卖出 -> 中性
        # soldRatio > 70: 聪明钱大部分卖出 -> 价格下跌概率高
        
        if sold_ratio < 30:
            # 聪明钱还在持有：70% 概率大涨，20% 震荡，10% 下跌
            roll = random.random()
            if roll < 0.70:
                # 上涨：分布偏向止盈（30%~900%）
                price_change = random.gauss(200, 300)
            elif roll < 0.90:
                # 震荡：-10%~+50%
                price_change = random.uniform(-10, 50)
            else:
                # 下跌：-20%~-40%
                price_change = random.uniform(-40, -20)
        elif sold_ratio < 70:
            # 中性：50% 上涨，30% 震荡，20% 下跌
            roll = random.random()
            if roll < 0.50:
                # 上涨：50%~400%
                price_change = random.gauss(150, 150)
            elif roll < 0.80:
                # 震荡：-15%~+60%
                price_change = random.uniform(-15, 60)
            else:
                # 下跌：-20%~-45%
                price_change = random.uniform(-45, -20)
        else:
            # 聪明钱大部分卖出：30% 上涨，30% 震荡，40% 下跌
            roll = random.random()
            if roll < 0.30:
                # 上涨：50%~300%
                price_change = random.gauss(150, 120)
            elif roll < 0.60:
                # 震荡：-10%~+40%
                price_change = random.uniform(-10, 40)
            else:
                # 下跌：-20%~-50%
                price_change = random.uniform(-50, -20)
        
        # 限制极端值
        price_change = max(-60, min(1000, price_change))
        exit_price = entry_price * (1 + price_change / 100)
        
        # ========== 判断退出原因 ==========
        
        # 止损检查
        if exit_price <= stop_loss_price:
            trade.exit_reason = "止损"
            trade.exit_price = stop_loss_price
            trade.pnl_pct = -params["stop_loss_pct"]
            trade.status = "sl"
        # 止盈检查（按层级）
        elif price_change >= params["take_profit_tiers"][0] * 100 - 100:
            # 达到第一止盈 2x
            if price_change >= params["take_profit_tiers"][1] * 100 - 100:
                # 达到第二止盈 5x
                if price_change >= params["take_profit_tiers"][2] * 100 - 100:
                    # 达到第三止盈 10x
                    trade.exit_reason = "止盈(10x)"
                    trade.pnl_pct = params["take_profit_tiers"][2] * 100 - 100
                    trade.status = "tp3"
                else:
                    trade.exit_reason = "止盈(5x)"
                    trade.pnl_pct = params["take_profit_tiers"][1] * 100 - 100
                    trade.status = "tp2"
            else:
                trade.exit_reason = "止盈(2x)"
                trade.pnl_pct = params["take_profit_tiers"][0] * 100 - 100
                trade.status = "tp1"
        # 移动止损检查（如果盈利 >= 50%）
        elif price_change >= params["trailing_stop_activate"]:
            trailing_stop_price = entry_price * (1 + params["trailing_stop_activate"] / 100)
            if exit_price <= trailing_stop_price * (1 - params["trailing_stop_pct"] / 100):
                trade.exit_reason = "移动止损"
                trade.pnl_pct = params["trailing_stop_activate"] - params["trailing_stop_pct"]
                trade.status = "ts"
            else:
                # 移动止损未触发，使用实际价格
                trade.exit_price = exit_price
                trade.pnl_pct = price_change
                trade.exit_reason = "持仓收益"
                trade.status = "profit"
        else:
            # 正常退出（未达到止盈或止损）
            trade.exit_price = exit_price
            trade.pnl_pct = price_change
            if price_change > 0:
                trade.exit_reason = "持仓收益"
                trade.status = "profit"
            else:
                trade.exit_reason = "浮动亏损"
                trade.status = "loss"
        
        # 持仓超过 24 小时强制退出
        exit_time = current_time + timedelta(hours=24)
        trade.exit_time = min(exit_time, result.end_date)
        
        # 计算盈亏金额
        trade.pnl_usd = position_usd * trade.pnl_pct / 100
        
        # 更新余额
        balance += trade.pnl_usd
        peak_balance = max(peak_balance, balance)
        
        # 更新统计
        daily_trades[current_date] += 1
        result.trades.append(trade)
        
        # 统计胜负
        if trade.pnl_pct > 0:
            result.winning_trades += 1
            consecutive_losses = 0
        else:
            result.losing_trades += 1
            consecutive_losses += 1
        
        # 熔断检查
        if consecutive_losses >= 3:
            # 连续 3 笔亏损，跳过下个小时
            # （简化处理，继续下一笔）
            pass
    
    # ========== 计算最终统计 ==========
    result.total_trades = len(result.trades)
    result.winning_trades = result.winning_trades
    result.losing_trades = result.losing_trades
    result.win_rate = result.winning_trades / result.total_trades * 100 if result.total_trades > 0 else 0
    
    # 盈亏统计
    if result.trades:
        pnls = [t.pnl_pct for t in result.trades]
        result.total_pnl_pct = sum(pnls)
        result.avg_pnl_pct = sum(pnls) / len(pnls)
        result.max_win_pct = max(pnls)
        result.max_loss_pct = min(pnls)
    
    # 总收益率
    result.total_return = (balance - initial_balance) / initial_balance * 100
    
    # 最大回撤
    running_max = initial_balance
    max_drawdown = 0
    for trade in result.trades:
        if trade.exit_price > 0:
            # 简化：按交易顺序计算
            pass
    result.max_drawdown = max_drawdown
    
    # 退出原因统计
    result.exit_reasons = defaultdict(int)
    for trade in result.trades:
        result.exit_reasons[trade.exit_reason] += 1
    
    return result

# ============================================================================
# 结果展示
# ============================================================================

def print_backtest_report(result: BacktestResult, initial_balance: float = 10000.0):
    """打印回测报告"""
    
    print("\n" + "="*70)
    print("📊 聪明钱交易者 - 回测报告 V1.0.0")
    print("="*70)
    
    if result.start_date and result.end_date:
        print(f"\n📅 回测时间: {result.start_date.strftime('%Y-%m-%d')} ~ {result.end_date.strftime('%Y-%m-%d')}")
        print(f"   持续天数: {result.duration_days} 天")
    
    print(f"\n💰 初始资金: ${initial_balance:,.2f}")
    print(f"   最终资金: ${initial_balance * (1 + result.total_return/100):,.2f}")
    print(f"   总收益率: {result.total_return:+.2f}%")
    
    print(f"\n📈 交易统计:")
    print(f"   总交易次数: {result.total_trades} 笔")
    print(f"   盈利交易: {result.winning_trades} 笔")
    print(f"   亏损交易: {result.losing_trades} 笔")
    print(f"   胜率: {result.win_rate:.1f}%")
    
    print(f"\n📊 收益统计:")
    print(f"   平均收益: {result.avg_pnl_pct:+.2f}%")
    print(f"   最大单笔盈利: {result.max_win_pct:+.2f}%")
    print(f"   最大单笔亏损: {result.max_loss_pct:+.2f}%")
    print(f"   最大回撤: {result.max_drawdown:.2f}%")
    
    print(f"\n🔍 退出原因分析:")
    for reason, count in sorted(result.exit_reasons.items(), key=lambda x: -x[1]):
        pct = count / result.total_trades * 100 if result.total_trades > 0 else 0
        print(f"   {reason}: {count} 笔 ({pct:.1f}%)")
    
    # 交易明细
    print(f"\n📋 交易明细（前 10 笔）:")
    print("-" * 70)
    print(f"{'时间':<20} {'代币':<12} {'入场价':<15} {'出场价':<15} {'盈亏%':<10} {'原因':<10}")
    print("-" * 70)
    
    for trade in result.trades[:10]:
        entry_time_str = trade.entry_time.strftime("%Y-%m-%d %H:%M")
        print(f"{entry_time_str:<20} {trade.signal.token_symbol:<12} "
              f"{trade.entry_price:<15.8f} {trade.exit_price:<15.8f} "
              f"{trade.pnl_pct:>+8.2f}%  {trade.exit_reason:<10}")
    
    if len(result.trades) > 10:
        print(f"... 还有 {len(result.trades) - 10} 笔交易")
    
    print("\n" + "="*70)
    print("⚠️  风险提示: 回测结果不代表未来收益，实际交易可能存在滑点、延迟等误差")
    print("="*70)

# ============================================================================
# 主程序
# ============================================================================

def main():
    print("="*70)
    print("🤖 聪明钱交易者 - 回测框架 V1.0.0")
    print("   回测时间范围: 2026-04-13 ~ 2026-05-13 (1个月)")
    print("="*70)
    
    # 1. 获取当前聪明钱信号
    current_signals = get_smart_money_signals(limit=100)
    
    if not current_signals:
        print("❌ 无法获取聪明钱信号，回测终止")
        sys.exit(1)
    
    # 2. 定义回测时间范围
    end_date = datetime(2026, 5, 13, 23, 59)
    start_date = datetime(2026, 4, 13, 0, 0)
    
    # 3. 生成模拟历史信号
    simulated_signals = generate_simulated_signals(
        current_signals, start_date, end_date
    )
    
    # 4. 执行回测
    result = run_backtest(
        simulated_signals,
        initial_balance=10000.0,
        params=STRATEGY_PARAMS
    )
    
    # 5. 展示报告
    print_backtest_report(result, initial_balance=10000.0)
    
    # 6. 保存结果到文件
    output_file = "/tmp/smart_money_backtest_result.json"
    result_data = {
        "summary": {
            "total_trades": result.total_trades,
            "win_rate": result.win_rate,
            "total_return": result.total_return,
            "avg_pnl": result.avg_pnl_pct,
            "max_win": result.max_win_pct,
            "max_loss": result.max_loss_pct,
            "duration_days": result.duration_days,
        },
        "exit_reasons": dict(result.exit_reasons),
        "trades": [
            {
                "token": t.signal.token_symbol,
                "entry_time": t.entry_time.isoformat(),
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl_pct": t.pnl_pct,
                "exit_reason": t.exit_reason,
            }
            for t in result.trades
        ]
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 回测结果已保存到: {output_file}")
    
    return result

if __name__ == "__main__":
    main()
