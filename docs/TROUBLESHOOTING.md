# 故障排查

本文档帮助您解决 聪明钱交易者 策略使用过程中可能遇到的问题。

---

## 常见问题

### 1. onchainos 命令未找到

**问题**：执行 `onchainos` 时提示 "command not found"

**原因**：onchainOS CLI 未正确安装

**解决方案**：
```bash
# 重新安装 onchainOS CLI
curl -sS https://onchainos.sh | sh

# 验证安装
onchainos --version

# 如果仍有问题，尝试添加 PATH
export PATH="$HOME/.local/bin:$PATH"
```

---

### 2. Wallet 未登录

**问题**：`onchainos wallet status` 显示未登录

**解决方案**：
```bash
# 登录 Agentic Wallet
onchainos wallet login --email your_email@example.com

# 验证登录状态
onchainos wallet status
```

---

### 3. API 频率限制

**问题**：执行命令时返回 "Rate limit exceeded"

**原因**：onchainOS API 有调用频率限制

**解决方案**：
1. 等待 1 分钟后再试
2. 减少检查的代币数量
3. 使用缓存避免重复请求

**建议**：在代码中添加重试逻辑和延迟

```python
import time

def api_call_with_retry(func, max_retries=3):
    for i in range(max_retries):
        try:
            return func()
        except RateLimitError:
            wait_time = (i + 1) * 10  # 递增等待
            time.sleep(wait_time)
    raise Exception("API 调用失败")
```

---

### 4. 安全检查返回空结果

**问题**：安全检查命令返回空或超时

**原因**：
- 代币较新，数据尚未同步
- 网络问题
- API 服务暂时不可用

**解决方案**：
```python
# 添加超时和重试
import requests

def safe_check(token_address, max_retries=3):
    for i in range(max_retries):
        try:
            result = onchainos_check(token_address, timeout=10)
            if result:
                return result
        except TimeoutError:
            continue
    return None  # 返回 None，跳过该代币
```

---

### 5. Swap 执行失败

**问题**：执行 `onchainos swap execute` 失败

**常见原因**：
1. 余额不足
2. 滑点过大
3. 流动性不足
4. 价格已变化

**解决方案**：
1. 检查钱包余额
2. 使用 `swap quote` 预估滑点
3. 调整滑点容忍度
4. 等待市场稳定后再试

```bash
# 先获取报价
onchainos swap quote   --from <USDC_ADDRESS>   --to <token_address>   --readable-amount <amount>   --chain solana

# 检查滑点
# 如果滑点 > 5%，考虑取消交易
```

---

### 6. 定时任务未执行

**问题**：注册的 cron 任务没有按预期执行

**检查步骤**：
```bash
# 1. 检查 cron 任务列表
openclaw cron list

# 2. 检查任务状态
openclaw cron status

# 3. 手动触发测试
openclaw cron run <job_id>

# 4. 检查日志
openclaw logs --tail 100
```

**常见原因**：
1. 任务被禁用
2. Gateway 未运行
3. 时间配置错误

**解决方案**：
```bash
# 启用任务
openclaw cron update <job_id> --enabled true

# 重启 Gateway
openclaw gateway restart

# 检查时区配置
# 确保使用正确的时区（Asia/Shanghai）
```

---

### 7. 策略没有找到交易机会

**问题**：长时间没有开仓

**可能原因**：
1. 聪明钱信号太少
2. 安全检查过滤太严格
3. 市场没有符合条件的机会

**解决方案**：
1. 检查聪明钱信号采集是否正常
2. 适当放宽 `min_smart_money_wallets` 参数
3. 检查 onchainOS API 是否正常

```bash
# 手动测试信号采集
onchainos signal list --chain solana --wallet-type 1 --limit 50

# 检查是否有信号
# 如果信号为 0，可能是 API 问题
```

---

### 8. 持仓未按预期止盈/止损

**问题**：价格达到止盈/止损条件但未执行

**可能原因**：
1. 价格检查频率太低
2. 网络延迟
3. API 返回错误

**解决方案**：
1. 提高价格检查频率（从 1 分钟改为 30 秒）
2. 添加心跳检测确保监控运行
3. 检查日志定位问题

```bash
# 检查最近的任务日志
openclaw logs --since "1 hour ago" | grep "smart-money-trader"

# 检查是否有错误信息
openclaw logs --level error
```

---

## 日志分析

### 查看策略执行日志

```bash
# 查看最近 24 小时的日志
openclaw logs --since "24 hours" --filter "smart-money-trader"

# 导出日志到文件
openclaw logs --since "7 days" > strategy.log
```

### 常见日志关键词

| 关键词 | 含义 |
|--------|------|
| `SIGNAL_DETECTED` | 检测到聪明钱信号 |
| `SAFETY_CHECK_PASSED` | 安全检查通过 |
| `SAFETY_CHECK_FAILED` | 安全检查未通过 |
| `POSITION_OPENED` | 开仓成功 |
| `POSITION_CLOSED` | 平仓成功 |
| `STOP_LOSS_TRIGGERED` | 止损触发 |
| `TAKE_PROFIT_TRIGGERED` | 止盈触发 |
| `RATE_LIMIT` | 触发频率限制 |
| `ERROR` | 执行错误 |

---

## 性能优化建议

### 1. 减少 API 调用

```python
# 使用缓存
from functools import lru_cache

@lru_cache(maxsize=100)
def get_token_price(token_address):
    return onchainos_token_price(token_address)

# 批量获取数据
def batch_safety_check(token_list):
    # 每次最多检查 10 个代币
    for i in range(0, len(token_list), 10):
        batch = token_list[i:i+10]
        for token in batch:
            safety_check(token)
```

### 2. 并行处理

```python
from concurrent.futures import ThreadPoolExecutor

def parallel_safety_check(token_list):
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(safety_check, token_list)
    return list(results)
```

### 3. 异步执行

```python
import asyncio

async def async_signal_fetch():
    tasks = [
        fetch_signals(chain='solana'),
        fetch_signals(chain='ethereum'),
    ]
    results = await asyncio.gather(*tasks)
    return results
```

---

## 联系支持

如果以上方法无法解决您的问题，请通过以下方式联系支持：

1. **GitHub Issues**：https://github.com/skynet2000/smart-money-trader/issues
2. **提交问题**时，请包含：
   - 错误日志
   - 环境信息（OS、onchainOS 版本等）
   - 复现步骤

---

*最后更新：2026-05-13*
