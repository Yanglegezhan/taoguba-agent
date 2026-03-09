# A股超短线复盘系统

基于Akshare公开数据源的超短线复盘分析系统，生成专业的HTML复盘报告。

## 功能特性

- **市场数据获取**: 涨跌家数、涨停跌停统计
- **板块分析**: 概念板块和行业板块强度分析
- **连板梯队**: 连板股梯队分布、最高板个股
- **情绪周期**: 大盘系数、超短情绪、亏钱效应三线指标
- **个股分析**: 首板股、高标股详细分析
- **报告生成**: 专业的HTML格式复盘报告

## 数据源

- **Akshare**: 免费开源的财经数据接口库
  - 东方财富：`ak.stock_zh_a_spot_em()`, `ak.stock_zt_pool_em()`
  - 板块数据：`ak.stock_board_concept_name_em()`, `ak.stock_board_industry_name_em()`

## 安装依赖

```bash
pip install akshare pandas matplotlib seaborn openpyxl requests
```

## 快速开始

```python
from main import MasterReplaySystem

# 创建复盘系统实例
system = MasterReplaySystem()

# 生成今日复盘报告
report_path = system.generate_report(date="2026-03-05")

print(f"复盘报告已生成: {report_path}")
```

## 项目结构

```
A股超短线复盘系统/
├── data/                   # 数据获取层
│   ├── market_data_fetcher.py      # 市场数据获取
│   ├── sector_data_fetcher.py      # 板块数据获取
│   └── stock_data_fetcher.py       # 个股数据获取
├── analysis/               # 分析层
│   ├── sentiment_analyzer.py        # 情绪指标分析
│   ├── sector_analyzer.py           # 板块强度分析
│   ├── stock_analyzer.py            # 个股梯队分析
│   └── cycle_detector.py            # 情绪周期判断
├── report/                 # 报告层
│   ├── html_generator.py            # HTML报告生成
│   ├── markdown_generator.py        # Markdown报告生成
│   └── templates/                   # 报告模板
├── config/                 # 配置层
│   └── settings.py                  # 系统配置
├── output/                 # 输出目录
│   ├── markdown/                    # Markdown报告
│   └── html/                        # HTML报告
├── main.py                 # 主入口
└── requirements.txt        # 依赖包
```

## 核心指标

### 情绪三线指标

1. **大盘系数**: (上涨家数-下跌家数)/(上涨家数+下跌家数)×100 + 指数涨跌幅×10
2. **超短情绪**: 涨停数×2 + 百日新高数×0.5 - 跌停数×3 - 炸板率×50
3. **亏钱效应**: 跌停数×2 + 大幅回撤数 + |昨日涨停今表现|×10

### 情绪周期判断

- **冰点**: 大盘系数<30, 超短情绪<50, 亏钱效应>100
- **修复**: 指标环比上升
- **分歧**: 指标波动>50
- **高潮**: 大盘系数>150, 超短情绪>150, 亏钱效应<40

## 报告示例

报告包含以下章节：
- 一、大盘分析（核心指标、走势分析）
- 二、情绪分析（三线指标、周期阶段）
- 三、板块分析（强势板块、资金流向）
- 四、个股分析（最高板、首板股）
- 五、操作建议（仓位、策略、风险）

## 注意事项

1. **禁用代理**: 确保不使用代理，否则Akshare会报错
2. **频率限制**: 每次请求间隔2-5秒，避免被封禁
3. **数据完整性**: 部分数据（如历史连板）可能不完整，建议配合其他数据源使用

## 许可证

MIT License
