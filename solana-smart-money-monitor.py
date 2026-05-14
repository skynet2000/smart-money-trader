#!/usr/bin/env python3
"""Solana 聪明钱监控：市值 < $2000万，≥10 个聪明钱钱包买入"""
import subprocess, json, os, sys, re
from datetime import datetime

STATE_FILE = "/Users/skynet/.qclaw/workspace/solana-smart-money-state.json"
LOG_FILE = "/Users/skynet/.qclaw/workspace/solana-smart-money-alerts.log"
MIN_WALLET_COUNT = 5  # 降低入场阈值：从10降到5，捕捉更早信号
MAX_MARKET_CAP_USD = 20_000_000
MIN_LIQUIDITY_USD = 25_000  # 最低流动性要求（$25K）
MIN_MARKET_CAP_USD = 20_000  # 过滤过低市值（$20K以下流动性通常很差）

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return r.stdout.strip()

def get_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"seen_tokens": [], "last_check": None}

def save_state(s):
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)

def fetch_signals():
    cmd = (
        f"~/.local/bin/onchainos signal list "
        f"--chain solana "
        f"--max-market-cap-usd {MAX_MARKET_CAP_USD}"
    )
    out = run(cmd)
    try:
        data = json.loads(out)
        if data.get("ok"):
            return data["data"]
    except Exception as e:
        log(f"解析信号失败: {e}")
    return []

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def check_liquidity(token_address):
    """检查代币流动性是否达标"""
    try:
        cmd = f"~/.local/bin/onchainos token liquidity {token_address} --chain solana"
        out = run(cmd)
        data = json.loads(out)
        if data.get("ok"):
            liquidity_usd = float(data.get("data", {}).get("liquidityUsd", 0))
            if liquidity_usd >= MIN_LIQUIDITY_USD:
                log(f"✅ 流动性检查通过: ${liquidity_usd:,.0f}")
                return True
            else:
                log(f"⚠️ 流动性不足: ${liquidity_usd:,.0f} < ${MIN_LIQUIDITY_USD:,.0f}")
                return False
    except Exception as e:
        log(f"⚠️ 流动性检查失败: {e}")
    return False

# ========== 主逻辑 ==========
log("========== 开始检查 Solana 聪明钱信号 ==========")

signals = fetch_signals()
if not signals:
    log("未获取到信号数据，跳过本次检查")
    sys.exit(0)

state = get_state()
seen = set(state.get("seen_tokens", []))
new_alerts = []

# 按代币聚合唯一钱包地址
token_wallets = {}
for sig in signals:
    token = sig.get("token", {})
    addr = token.get("tokenAddress", "")
    if not addr:
        continue
    
    # 解析 triggerWalletAddress（逗号分隔的钱包列表）
    wallet_str = sig.get("triggerWalletAddress", "")
    wallets = [w.strip() for w in wallet_str.split(",") if w.strip()]
    
    if addr not in token_wallets:
        token_wallets[addr] = {
            "wallets": set(),
            "signal": sig,
            "total_usd": 0.0
        }
    
    token_wallets[addr]["wallets"].update(wallets)
    try:
        token_wallets[addr]["total_usd"] += float(sig.get("amountUsd", 0))
    except:
        pass

log(f"获取到 {len(signals)} 条信号，涉及 {len(token_wallets)} 个代币")

for addr, info in token_wallets.items():
    wallet_count = len(info["wallets"])
    sig = info["signal"]
    token = sig.get("token", {})
    market_cap = float(token.get("marketCapUsd", 0))
    symbol = token.get("symbol", "")
    name = token.get("name", "")
    price = sig.get("price", "0")
    holders = token.get("holders", "0")
    sold_ratio = sig.get("soldRatioPercent", "0")
    
    # 流动性检查（通过 onchainOS）
    liquidity_ok = check_liquidity(addr)
    
    if (wallet_count >= MIN_WALLET_COUNT and 
        market_cap < MAX_MARKET_CAP_USD and
        market_cap >= MIN_MARKET_CAP_USD and
        liquidity_ok):
        if addr not in seen:
            alert = {
                "token": symbol,
                "name": name,
                "address": addr,
                "wallet_count": wallet_count,
                "market_cap_usd": market_cap,
                "price": price,
                "holders": holders,
                "sold_ratio": sold_ratio,
                "alert_time": now_str()
            }
            new_alerts.append(alert)
            seen.add(addr)
            log(f"🚨 新信号！{symbol} | 钱包数: {wallet_count} | 市值: ${market_cap:,.0f} | 价格: ${price}")

# 保存状态
state["seen_tokens"] = list(seen)
state["last_check"] = now_str()
save_state(state)

if new_alerts:
    log(f"✅ 发现 {len(new_alerts)} 个新信号！")
    # 输出人类可读格式，方便通知
    print("\n🚨 发现新聪明钱信号！")
    for a in new_alerts:
        print(f"\n代币: {a['token']} ({a['name']})")
        print(f"  地址: {a['address']}")
        print(f"  聪明钱钱包数: {a['wallet_count']}")
        print(f"  市值: ${a['market_cap_usd']:,.0f}")
        print(f"  价格: ${a['price']}")
        print(f"  持有者: {a['holders']}")
        print(f"  聪明钱持仓占比: {a['sold_ratio']}%")
    print(f"\n⏰ 检查时间: {now_str()}")
else:
    log("暂无新信号（≥10钱包 + 市值<$2000万）")

log("========== 检查完成 ==========")
