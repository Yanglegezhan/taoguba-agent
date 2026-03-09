# 核心个股复盘智能体阵列

## 项目概述

设计并实现一个【核心个股复盘智能体阵列】，包括：
1. **连板核心复盘智能体** (ConsecutiveBoardStockAgent) - 分析连板梯队个股
2. **连板Critic智能体** (ConsecutiveBoardCritic) - 对连板分析结果进行批评和验证
3. **趋势核心复盘智能体** (TrendStockAgent) - 分析趋势上升个股
4. **趋势Critic智能体** (TrendCritic) - 对趋势分析结果进行批评和验证
5. **Synthesis Agent** (StockSynthesisAgent) - 综合四个智能体的分析结果，生成最终复盘报告

## 项目结构

```
stock_replay_agent/
├── README.md                     # 项目说明文档
├── pyproject.toml                 # 项目配置
├── config.yaml                    # 配置文件
├── src/
│   ├── agent/                     # Agent主控模块
│   │   ├── consecutive_board_agent.py    # 连板核心复盘智能体
│   │   ├── trend_stock_agent.py         # 趋势核心复盘智能体
│   │   ├── synthesis_agent.py           # 综合智能体
│   │   └── critic_agent.py            # Critic智能体基类
│   ├── data/                      # 数据获取模块
│   │   └── kaipanla_stock_source.py   # Kaipanla数据源
│   ├── models/                    # 数据模型
│   │   └── stock_models.py             # 个股分析数据模型
│   ├── analysis/                   # 分析计算模块
│   │   ├── indicator_calculator.py     # 指标计算器
│   │   ├── special_action_detector.py    # 特殊动作检测器（领涨/逆跌/反核）
│   │   └── sector_comparator.py         # 同题材对比分析器
│   ├── llm/                       # LLM接口模块
│   │   ├── base.py                   # LLM基类
│   │   ├── client.py                 # LLM客户端
│   │   └── prompt_engine.py          # 提示词引擎
│   └── output/                     # 输出模块
│       ├── report_generator.py          # 报告生成器
│       └── json_exporter.py            # JSON数据导出器
├── prompts/                      # LLM提示词模板
│   ├── consecutive_board/
│   ├── trend_stock/
│   ├── critic/
│   └── synthesis/
├── output/                        # 输出目录
│   ├── reports/                    # Markdown报告输出
│   └── data/                       # JSON数据输出
├── tests/                         # 测试文件
└── cli.py                         # 命令行入口
```

## 安装依赖

```bash
pip install -r requirements.txt
# 或
pip install pandas pydantic pyyaml zhipuai akshare openai
```

## 使用方法

```bash
# 分析指定日期的核心个股
python -m src.cli --date 2025-02-10

# 指定股票代码
python -m src.cli --date 2025-02-10 --stocks 605398,002881

# 指定输出格式
python -m src.cli --date 2025-02-10 --output all

# 使用特定LLM
python -m src.cli --date 2025-02-10 --model glm-4
```

## 配置

复制 `config.yaml.example` 为 `config.yaml`，并配置相应的参数，特别是 LLM API 密钥。

```bash
cp config.yaml.example config.yaml
```

## 环境变量

设置环境变量配置 API 密钥：

```bash
export ZHIPUAI_API_KEY="your_api_key_here"
```

## 核心功能模块

### 1. 数据源模块

主要接口：
- `get_consecutive_limit_up(date)` - 获取连板梯队数据
- `get_realtime_all_boards_stocks()` - 获取所有涨停板个股
- `get_stock_intraday(stock_code, date)` - 获取个股分时数据
- `get_index_intraday(index_code, date)` - 获取大盘指数分时
- `get_realtime_sharp_withdrawal()` - 获取大幅回撤数据

### 2. 分析计算模块

- **指标计算器** - 连板指标、趋势股指标计算
- **特殊动作检测器** - 领涨/逆跌/反核检测
- **同题材对比分析器** - 同题材股票识别和溢价水平对比

### 3. LLM分析模块

- **连板核心复盘智能体** - 分析连板梯队个股
- **趋势核心复盘智能体** - 分析趋势上升个股
- **Critic智能体** - 对分析结果进行批评和验证
- **Synthesis Agent** - 综合所有分析结果，生成最终复盘报告

## 输出格式

### Markdown报告

生成详细的复盘报告，包含：
- 个股基本信息
- 连板/趋势分析
- 特殊动作识别
- 同题材对比
- 风险评估
- 操作建议

### JSON数据

导出结构化数据，便于后续处理和可视化。

## 集成外部报告

系统会读取其他agent的报告作为上下文：
- index_replay_agent - 大盘分析
- sentiment_replay_agent - 情绪分析
- Theme_repay_agent - 题材分析
- dark_line_analyse - 暗线分析

## 测试

```bash
# 运行测试
pytest tests/
```

## 注意事项

1. **代理问题**：akshare需要关闭代理
2. **API限流**：kaipanla接口可能有请求频率限制
3. **数据时效性**：确保使用交易日而非自然日
4. **LLM响应解析**：处理中文标点和不同格式响应
