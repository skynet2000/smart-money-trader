#!/bin/bash
# Smart Money Simulation Trader - Paper Trading Mode
# Uses 'swap quote' (read-only) to simulate trades WITHOUT executing real transactions
# Usage: ./smart-money-simulation.sh

CHAIN="solana"
MAX_MARKET_CAP=20000000
MIN_WALLETS=5  # 降低入场阈值：从10降到5
MIN_LIQUIDITY=25000  # 最低流动性要求
SIM_AMOUNT=0.1  # Simulate with 0.1 SOL
STATE_FILE="/Users/skynet/.qclaw/workspace/smart-money-simulation-state.json"
LOG_FILE="/Users/skynet/.qclaw/workspace/smart-money-simulation.log"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📊 Smart Money Simulation Trader (Paper)"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  SIMULATION MODE - No real trades executed"
echo ""

# Load state - skip already simulated signals
SKIPPED=""
if [ -f "$STATE_FILE" ]; then
    last=$(jq -r '.lastSimulated // ""' "$STATE_FILE" 2>/dev/null)
    [ -n "$last" ] && SKIPPED="$last"
fi

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
COUNT=0
SIMULATED=0

for sig in $SIGNALS; do
    signal=$(echo "$sig" | base64 -d)
    wallet_count=$(echo "$signal" | jq -r '.triggerWalletCount')
    token_address=$(echo "$signal" | jq -r '.tokenAddress')
    token_symbol=$(echo "$signal" | jq -r '.tokenSymbol')
    token_name=$(echo "$signal" | jq -r '.tokenName')
    market_cap=$(echo "$signal" | jq -r '.marketCapUsd')
    
    COUNT=$((COUNT + 1))
    
    # Skip if already simulated
    if [ "$token_address" = "$SKIPPED" ]; then
        echo "⏭️  $token_symbol (already simulated today)"
        continue
    fi
    
    # 流动性检查
    echo "🔍 Checking liquidity..."
    LIQUIDITY=$(onchainos token liquidity "$token_address" --chain $CHAIN 2>&1)
    liquidity_usd=$(echo "$LIQUIDITY" | jq -r '.data.liquidityUsd // 0' 2>/dev/null)
    
    if [ "$(echo "$liquidity_usd >= $MIN_LIQUIDITY" | bc 2>/dev/null)" -eq 1 ]; then
        echo "✅ Liquidity OK: $$liquidity_usd"
        echo ""
        echo "🚨 SIMULATION SIGNAL: $token_symbol ($token_name)"
        echo "   Wallets: $wallet_count | Market Cap: $market_cap | Liquidity: $$liquidity_usd"
        
        # Get simulated quote (READ-ONLY - no trade executed)
        echo "📊 Getting simulated quote..."
        QUOTE=$(~/.local/bin/onchainos swap quote \
            --from SOL \
            --to "$token_address" \
            --readable-amount "$SIM_AMOUNT" \
            --chain $CHAIN 2>&1)
        
        if echo "$QUOTE" | jq -e '.ok == true' > /dev/null 2>&1; then
            output_amount=$(echo "$QUOTE" | jq -r '.data[0].toTokenAmount')
            output_symbol=$(echo "$QUOTE" | jq -r '.data[0].toToken.symbol')
            price_impact=$(echo "$QUOTE" | jq -r '.data[0].priceImpactPercent')
            exchange_rate=$(echo "$QUOTE" | jq -r '.data[0].exchangeRate')
            price=$(echo "$QUOTE" | jq -r '.data[0].toToken.tokenUnitPrice')
            
            echo "   💰 Simulated Result: $SIM_AMOUNT SOL → $output_amount $output_symbol"
            echo "   📉 Price Impact: $price_impact%"
            echo "   💵 Est. Price: $price"
            
            # Calculate simulated P&L
            echo ""
            echo "📈 SIMULATED TRADE LOGIC:"
            echo "   Entry: $SIM_AMOUNT SOL"
            echo "   Exit (2x): $(echo "$SIM_AMOUNT * 2" | bc) SOL (~+100%)"
            echo "   Stop Loss (-20%): $(echo "$SIM_AMOUNT * 0.8" | bc) SOL"
            
            # Save simulation state
            echo "{\"lastSimulated\": \"$token_address\", \"timestamp\": $(date +%s), \"token\": \"$token_symbol\", \"wallets\": $wallet_count, \"marketCap\": \"$market_cap\"}" > "$STATE_FILE"
            
            # Log
            echo "$(date '+%Y-%m-%d %H:%M:%S') | SIM | $token_symbol | $wallet_count wallets | $market_cap | $output_amount $output_symbol" >> "$LOG_FILE"
            
            SIMULATED=$((SIMULATED + 1))
            echo "✅ Simulation recorded for $token_symbol"
            
            # Only simulate one per run
            break
        else
            echo "   ⚠️  Could not get quote for $token_symbol"
            echo "   $(echo "$QUOTE" | jq -r '.error' 2>/dev/null || echo "$QUOTE" | head -1)"
        fi
    fi
done

echo ""
echo "✅ Simulation complete"
echo "   Signals checked: $COUNT"
echo "   Simulations run: $SIMULATED"
echo "   ⚠️  NO REAL MONEY WAS USED"