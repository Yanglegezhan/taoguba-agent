# A股超短线复盘系统 - 项目说明

## 项目概述

这是一个基于Akshare公开数据源的A股超短线复盘系统，用于自动生成专业的超短线交易复盘报告。

## 核心功能

### 1. 数据获取层 (data/)
- `market_data_fetcher.py`: 市场数据获取（涨跌家数、涨停跌停）
- `sector_data_fetcher.py`: 板块数据获取（概念板块、行业板块）

### 2. 分析层 (analysis/)
- `sentiment_analyzer.py`: 情绪指标计算和周期判断
  - 大盘系数 = (上涨-下跌)/(上涨+下跌)×100 + 指数涨跌幅×10
  - 超短情绪 = 涨停×2 + 新高×0.5 - 跌停×3 - 炸板率×50
  - 亏钱效应 = 跌停×2 + 回撤 + |昨日涨停表现|×10

### 3. 报告生成 (main.py)
- 自动生成HTML格式复盘报告
- 包含大盘分析、情绪分析、板块分析、个股分析
- 响应式设计，支持浏览器查看

## 数据源

### 主要数据源：Akshare
- 东方财富实时行情: `ak.stock_zh_a_spot_em()`
- 涨停股池: `ak.stock_zt_pool_em()`
- 概念板块: `ak.stock_board_concept_name_em()`
- 行业板块: `ak.stock_board_industry_name_em()`

### 数据限制
由于使用公开数据源，以下数据需要估算：
- 炸板率: 估算为涨停数的12%
- 百日新高: 通过高涨幅高换手股票估算
- 昨日涨停今日表现: 需要历史数据支持

## 系统架构

```
A股超短线复盘系统/
├── data/                      # 数据获取层
│   ├── market_data_fetcher.py     # 市场数据
│   └── sector_data_fetcher.py     # 板块数据
├── analysis/                  # 分析层
│   └── sentiment_analyzer.py      # 情绪分析
├── config/                    # 配置
│   └── settings.py                # 系统配置
├── main.py                    # 主程序
├── test_system.py             # 完整测试
├── simple_test.py             # 简单测试
├── requirements.txt           # 依赖
└── README.md                  # 说明文档
```

## 使用方法

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 运行测试
```bash
# 简单测试
python simple_test.py

# 完整测试
python test_system.py
```

### 3. 生成复盘报告
```python
from main import MasterReplaySystem

system = MasterReplaySystem()
report_path = system.generate_report("2026-03-05")
print(f"Report saved to: {report_path}")
```

## 核心指标说明

### 大盘系数
- < 30: 弱势
- 30-150: 震荡
- > 150: 强势

### 超短情绪
- < 50: 情绪低
- 50-150: 情绪中等
- > 150: 情绪高

### 亏钱效应
- < 40: 亏钱效应低
- 40-100: 亏钱效应中等
- > 100: 亏钱效应高

## 情绪周期判断

系统自动判断以下周期阶段：

1. **冰点**: 市场系数<30, 情绪<50, 亏钱效应>100
2. **修复**: 指标环比上升，亏钱效应减弱
3. **分歧**: 指标波动>50，资金分歧大
4. **高潮**: 市场系数>150, 情绪>150, 亏钱效应<40
5. **震荡**: 默认状态

## 输出示例

报告包含以下章节：
- 一、大盘分析（核心指标）
- 二、情绪分析（三线指标+周期阶段）
- 三、板块分析（概念/行业TOP5）
- 四、个股分析（连板梯队+最高板+首板股）
- 五、操作建议（仓位+策略+风险）

## 注意事项

1. **禁用代理**: Akshare要求不使用代理
2. **频率限制**: 每次请求间隔2-5秒
3. **交易日**: 确保在交易日运行，非交易日数据为空
4. **数据延迟**: 部分数据可能有15分钟延迟

## 扩展建议

如果需要更完整的数据，建议：
1. 配合开盘啦API使用（提供更准确的连板、炸板数据）
2. 添加东方财富数据作为备用源
3. 使用缓存机制减少API请求
4. 添加历史数据回测功能

## 许可证

MIT License

## 作者

基于开源项目改造，数据来源于Akshare。
