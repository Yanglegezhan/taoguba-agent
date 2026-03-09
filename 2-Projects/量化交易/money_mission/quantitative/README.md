# 量化交易策略系统

## 功能
1. 支持A股、加密货币、外汇多种市场
2. 多种技术指标和策略
3. 完整的回测框架
4. 信号聚合和共识机制

## 策略列表
| 策略 | 适用市场 | 描述 |
|------|---------|------|
| MACDStrategy | 全部 | 趋势跟踪，金叉买入死叉卖出 |
| RSIStrategy | 全部 | 超买超卖，反转信号 |
| BollingerBandsStrategy | 全部 | 均值回归，触及上下轨反向操作 |
| CryptoVolumeStrategy | 加密货币 | 量价配合，放量突破 |
| ForexCarryTradeStrategy | 外汇 | 利率套利 |

## 使用方法

### 安装依赖
```bash
pip install pandas numpy ccxt yfinance baostock
```

### 运行回测
```python
from quantitative.main import main
main()
```

### 自定义策略
```python
from quantitative.strategies import create_strategy

# 创建MACD策略
strategy = create_strategy('macd', fast=12, slow=26, signal=9)

# 生成信号
signals = strategy.generate_signals(dataframe)
```

## 商业价值

### 可提供的服务
1. **策略开发服务** - 为客户定制专属交易策略
2. **策略回测服务** - 帮客户验证策略有效性
3. **信号推送服务** - 实时推送交易信号
4. **量化投资管理** - 代客理财（需要牌照）

### 定价参考
| 服务 | 价格 |
|------|------|
| 单个策略开发 | 200-500元 |
| 完整回测报告 | 100-300元 |
| 月度信号订阅 | 99-299元/月 |
| 策略优化服务 | 500-2000元 |

### 预期收益
- 策略交付：2-3个订单，收入500-1500元
- 信号订阅：5-10个客户，收入500-3000元/月
