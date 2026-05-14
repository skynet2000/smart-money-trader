#!/bin/bash
# Smart Money Monitor + Simulation - Unified Script
# Monitors signals and immediately simulates trades if found
# Runs as a single synchronized cron job

CHAIN="solana"
MAX_MARKET_CAP=20000000
MIN_WALLETS=5  # 降低入场阈值：从10降到5
MIN_LIQUIDITY=25000  # 最低流动性要求（$25K）
MIN_MARKET_CAP=20000  # 过滤过低市值（$20K以下）
SIM_AMOUNT=0.1
STATE_FILE="/Users/skynet/.qclaw/workspace/smart-money-unified-state.json"
LOG_FILE="/Users/skynet/.qclaw/workspace/smart-money-unified.log"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔍 Smart Money Monitor + Simulation"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  SIMULATION MODE - No real trades executed"
echo ""

# Get signals
echo "📡 Fetching smart money signals..."
RESPONSE=$(~/.local/bin/onchainos signal list --chain $CHAIN --max-market-cap-usd $MAX_MARKET_CAP --limit 50 2>&1)

if ! echo "$RESPONSE" | jq -e '.ok == true' > /dev/null 2>&1; then
    echo "❌ Failed to fetch signals"
    echo "$RESPONSE" | head -3
    exit 1
fi

# Parse signals
SIGNALS=$(echo "$RESPONSE" | jq -r '.data[] | @base64' 2>/dev/null)
FOUND=0
TRADED=0

for sig in $SIGNALS; do
    signal=$(echo "$sig" | base64 -d)
    wallet_count=$(echo "$signal" | jq -r '.triggerWalletCount')
    token_address=$(echo "$signal" | jq -r '.token.tokenAddress')
    token_symbol=$(echo "$signal" | jq -r '.token.symbol')
    token_name=$(echo "$signal" | jq -r '.token.name')
    market_cap=$(echo "$signal" | jq -r '.token.marketCapUsd')
    wallet_count=$(echo "$signal" | jq -r '.triggerWalletCount' | sed 's/"//g')
    
    FOUND=$((FOUND + 1))
    
    # Check conditions (添加流动性和市值过滤)
    market_cap_int=$(echo "$market_cap" | cut -d'.' -f1)
    if [ "$wallet_count" -ge "$MIN_WALLETS" ] 2>/dev/null && \
       [ "$market_cap_int" -ge "$MIN_MARKET_CAP" ] 2>/dev/null; then
        
        # 流动性检查
        echo "🔍 Checking liquidity..."
        LIQUIDITY=$(~/.local/bin/onchainos token liquidity "$token_address" --chain $CHAIN 2>&1)
        liquidity_usd=$(echo "$LIQUIDITY" | jq -r '.data.liquidityUsd // 0' 2>/dev/null)
        
        if [ "$(echo "$liquidity_usd >= $MIN_LIQUIDITY" | bc 2>/dev/null)" -eq 1 ]; then
            echo "✅ Liquidity OK: $$liquidity_usd"
            echo ""
            echo "🚨 SIGNAL DETECTED: $token_symbol ($token_name)"
            echo "   Wallets: $wallet_count | Market Cap: $market_cap | Liquidity: $$liquidity_usd"
        else
            echo "⚠️  Liquidity insufficient: $$liquidity_usd < $$MIN_LIQUIDITY"
            continue
        fi
        
        # Get simulated quote (READ-ONLY)
        echo "📊 Simulating trade..."
        QUOTE=$(~/.local/bin/onchainos swap quote \
            --from SOL \
            --to "$token_address" \
            --readable-amount "$SIM_AMOUNT" \
            --chain $CHAIN 2>&1)
        
        if echo "$QUOTE" | jq -e '.ok == true' > /dev/null 2>&1; then
            output_amount=$(echo "$QUOTE" | jq -r '.data[0].toTokenAmount')
            output_symbol=$(echo "$QUOTE" | jq -r '.data[0].toToken.symbol')
            price_impact=$(echo "$QUOTE" | jq -r '.data[0].priceImpactPercent')
            
            # Save state
            echo "{\"lastTrade\": \"$token_address\", \"timestamp\": $(date +%s), \"token\": \"$token_symbol\", \"wallets\": $wallet_count, \"marketCap\": \"$market_cap\", \"simAmount\": \"$output_amount $output_symbol\"}" > "$STATE_FILE"
            
            # Log
            echo "$(date '+%Y-%m-%d %H:%M:%S') | SIM | $token_symbol | $wallet_count wallets | $market_cap | $output_amount $output_symbol" >> "$LOG_FILE"
            
            TRADED=$((TRADED + 1))
            
            echo "   ✅ Simulated: $SIM_AMOUNT SOL → $output_amount $output_symbol"
            echo "   📉 Price Impact: $price_impact%"
            echo ""
            echo "📈 Strategy Logic (Optimized):"
            echo "   Entry: $SIM_AMOUNT SOL"
            echo "   TP 1 (2x): $SIM_AMOUNT * 2 = $(echo "$SIM_AMOUNT * 2" | bc) SOL (+100%)"
            echo "   TP 2 (5x): $SIM_AMOUNT * 5 = $(echo "$SIM_AMOUNT * 5" | bc) SOL (+400%)"
            echo "   Stop Loss: $SIM_AMOUNT * 0.8 = $(echo "$SIM_AMOUNT * 0.8" | bc) SOL (-20%)"
            echo "   🛡️  Risk Control: Min wallets=$MIN_WALLETS, Min liquidity=$$MIN_LIQUIDITY, Min market cap=$$MIN_MARKET_CAP"
            
            echo ""
            echo "✅ Simulation complete for $token_symbol"
            echo "───────────────────────────────────"
        else
            echo "   ⚠️  Could not simulate: $(echo "$QUOTE" | jq -r '.error' 2>/dev/null || echo "$QUOTE" | head -1)"
        fi
    fi
done

echo ""
echo "📊 Summary"
echo "   Signals checked: $FOUND"
echo "   Simulations run: $TRADED"
echo "   ⚠️  NO REAL MONEY USED"