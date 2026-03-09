# AI Trading Agent System

基于价格行为学的多Agent协作交易系统，通过模拟盘实战学习优化交易策略。

## 架构

```
trading-agents/
├── agents/              # Agent系统
│   ├── main_agent.py    # 主决策Agent
│   ├── analysis_agent.py # 分析Agent（市场环境+裸K）
│   ├── risk_agent.py    # 风控Agent
│   └── summary_agent.py # 总结Agent（复盘+RAG）
├── skills/              # Claude Skills
│   ├── price-action-knowledge.md  # 价格行为知识库
│   └── binance-trading.md         # 交易执行Skill
├── mcp_servers/         # MCP服务
│   └── binance_mcp/     # 币安数据服务
├── config/              # 配置
│   ├── trading_config.yaml        # 交易参数
│   └── risk_rules.yaml            # 硬止损规则
├── data/                # 数据存储
│   ├── trades.db        # SQLite交易记录
│   ├── rag_db/          # 向量数据库（交易教训）
│   └── charts/          # TV截图存档
├── utils/               # 工具
│   ├── tv_screenshot.py # TradingView截图
│   ├── pattern_recognition.py # 裸K识别
│   └── market_classifier.py   # 市场环境分类
└── tests/               # 测试
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置API密钥
cp .env.example .env
# 编辑 .env 填入 Binance Testnet API Key

# 3. 启动系统
python run_trading_system.py
```

## Agent工作流程

1. **Main Agent** 触发扫描 → 调用 Analysis Agent
2. **Analysis Agent** 分析市场（Binance数据 + TV截图）→ 返回市场环境+交易机会
3. **Risk Agent** 评估风险 → 返回风控建议
4. **Main Agent** 综合决策 → 生成交易计划 → 执行模拟交易
5. **Summary Agent** 交易结束后复盘 → 提取教训 → 存入RAG

## 硬止损规则

- 单笔最大回撤：2%
- 日最大亏损：5%
- 强制止损：每笔必须设置止损

## 交易对

BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, ARBUSDT

## 时间框架

15m / 1h / 4h
