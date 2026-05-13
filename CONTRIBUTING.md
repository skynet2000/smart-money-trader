# 贡献指南

感谢您对 聪明钱交易者 项目的关注！我们欢迎各种形式的贡献，包括但不限于：

- 🐛 Bug 报告
- 💡 功能建议
- 📖 文档改进
- 🔧 代码贡献
- 📢 推广分享

---

## 🐛 Bug 报告

如果您发现了 Bug，请通过 GitHub Issues 提交，并包含以下信息：

1. **问题描述**：清晰描述问题
2. **复现步骤**：如何复现该问题
3. **预期行为**：您期望的行为
4. **实际行为**：实际发生的行为
5. **环境信息**：
   - onchainOS CLI 版本
   - OpenClaw 版本
   - 操作系统
   - 其他相关依赖

---

## 💡 功能建议

我们欢迎新的功能建议！请通过 GitHub Issues 提交，并包含：

1. **功能描述**：清晰描述建议的功能
2. **使用场景**：这个功能解决什么问题
3. **可能的替代方案**：您考虑过的其他方案

---

## 🔧 代码贡献

### 开发环境

```bash
# 克隆仓库
git clone https://github.com/skynet2000/smart-money-trader.git
cd smart-money-trader

# 创建功能分支
git checkout -b feature/your-feature-name
```

### 提交规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

类型（type）：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

示例：
```
feat(safety): 添加钓鱼代币黑名单检查

- 新增 onchainos token phishing-check
- 更新安全阈值表

Closes #123
```

### Pull Request 流程

1. Fork 仓库
2. 创建功能分支
3. 进行开发并测试
4. 提交代码（遵循提交规范）
5. 发起 Pull Request
6. 等待代码审查

---

## 📖 文档改进

文档是项目的重要组成部分！我们欢迎：

- 拼写和语法修正
- 解释不清晰的地方
- 缺失的文档内容
- 示例代码

---

## ⚠️ 注意事项

- 请确保您的代码遵循项目的代码风格
- 新功能请添加相应的测试
- 更新文档时注意保持一致性
- 提交前请进行自测

---

## 📞 联系

如有问题，请通过 GitHub Issues 联系作者。

感谢您的贡献！🚀
