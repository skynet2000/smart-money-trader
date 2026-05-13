# CHANGELOG - 聪明钱交易者

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-13

### Added
- 初始版本发布
- 聪明钱信号采集（onchainOS signal list）
- 13 项代币安全检查（蜜罐、LP 锁定、买卖税等）
- 动量确认（价格变动 + 成交量 + K 线形态）
- 分层止盈（2x / 5x / 10x）
- 移动止损（盈利 ≥ 50% 后激活）
- 频率限制和回撤熔断
- OpenClaw Skill 格式（SKILL.md）

### Features
- 动态交易品种发现（不固定交易对）
- 模拟盘 / 实盘切换（profile 参数）
- 定时任务支持（15 分钟轮询）

### Known Issues
- onchainOS API 有频率限制
- 市场极端情况下聪明钱信号可能失效

---

## 待办事项（TODO）
- [ ] 添加更多链支持（Ethereum、Base 等）
- [ ] 支持限价单（当前仅市价单）
- [ ] 添加性能统计和图表
- [ ] 支持 Webhook 通知

---

*Last updated: 2026-05-13*
