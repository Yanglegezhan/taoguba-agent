# 数据模型文档

## 概述

本文档描述了次日核心个股超预期分析系统中使用的所有核心数据模型。所有数据模型都支持JSON序列化/反序列化，并提供了Schema验证功能。

## 核心数据模型

### 1. TechnicalLevels（技术位）

记录个股的关键技术指标和位置信息。

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| ma5 | float | 5日均线 |
| ma10 | float | 10日均线 |
| ma20 | float | 20日均线 |
| previous_high | float | 前期高点 |
| chip_zone_low | float | 筹码密集区下沿 |
| chip_zone_high | float | 筹码密集区上沿 |
| distance_to_ma5_pct | float | 距离5日均线百分比 |
| distance_to_high_pct | float | 距离前高百分比 |

**使用示例：**

```python
from src.common.models import TechnicalLevels

tech = TechnicalLevels(
    ma5=10.5, ma10=10.2, ma20=9.8,
    previous_high=12.0, chip_zone_low=9.5, chip_zone_high=10.5,
    distance_to_ma5_pct=5.0, distance_to_high_pct=-10.0
)

# 序列化
data = tech.to_dict()

# 反序列化
restored = TechnicalLevels.from_dict(data)
```

### 2. Stock（个股）

记录个股的基础信息和实时数据。

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | str | 股票代码 |
| name | str | 股票名称 |
| market_cap | float | 流通市值（亿元） |
| price | float | 当前价格 |
| change_pct | float | 涨跌幅（%） |
| volume | float | 成交量 |
| amount | float | 成交额（万元） |
| turnover_rate | float | 换手率（%） |
| board_height | int | 连板高度 |
| themes | List[str] | 所属题材列表 |
| technical_levels | Optional[TechnicalLevels] | 技术位数据（可选） |

**使用示例：**

```python
from src.common.models import Stock, TechnicalLevels

stock = Stock(
    code='000001',
    name='平安银行',
    market_cap=100.0,
    price=10.5,
    change_pct=5.0,
    volume=1000000,
    amount=10500,
    turnover_rate=2.5,
    board_height=0,
    themes=['银行', '金融'],
    technical_levels=tech  # 可选
)
```

### 3. GenePool（基因库）

记录系统识别的核心个股池。

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| date | str | 日期（YYYY-MM-DD） |
| continuous_limit_up | List[Stock] | 连板梯队 |
| failed_limit_up | List[Stock] | 炸板股 |
| recognition_stocks | List[Stock] | 辨识度个股 |
| trend_stocks | List[Stock] | 趋势股 |
| all_stocks | Dict[str, Stock] | 所有个股字典（code -> Stock） |

**使用示例：**

```python
from src.common.models import GenePool, save_gene_pool, load_gene_pool

gene_pool = GenePool(
    date='2025-02-13',
    continuous_limit_up=[stock1, stock2],
    failed_limit_up=[stock3],
    recognition_stocks=[stock4],
    trend_stocks=[stock5],
    all_stocks={'000001': stock1, '000002': stock2}
)

# 保存到文件
filepath = save_gene_pool(gene_pool, 'data/stage1_output')

# 从文件加载
restored = load_gene_pool(filepath)
```

### 4. BaselineExpectation（基准预期）

记录个股的开盘预期和计算逻辑。

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | str | 股票代码 |
| stock_name | str | 股票名称 |
| expected_open_min | float | 预期开盘涨幅下限（%） |
| expected_open_max | float | 预期开盘涨幅上限（%） |
| expected_amount_min | float | 预期竞价金额下限（万元） |
| logic | str | 计算逻辑说明 |
| confidence | float | 置信度（0-1） |

**使用示例：**

```python
from src.common.models import BaselineExpectation, save_baseline_expectations, load_baseline_expectations

expectation = BaselineExpectation(
    stock_code='000001',
    stock_name='平安银行',
    expected_open_min=3.0,
    expected_open_max=5.0,
    expected_amount_min=10000,
    logic='昨日涨停+题材主升期+隔夜美股科技股上涨',
    confidence=0.85
)

# 保存多个基准预期
expectations = {'000001': expectation}
filepath = save_baseline_expectations(expectations, '2025-02-13', 'data/stage2_output')

# 加载
restored = load_baseline_expectations(filepath)
```

### 5. AuctionData（竞价数据）

记录个股的竞价阶段数据。

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | str | 股票代码 |
| auction_low_price | float | 竞价最低价 |
| auction_high_price | float | 竞价最高价 |
| open_price | float | 开盘价 |
| auction_volume | float | 竞价成交量 |
| auction_amount | float | 竞价成交额（万元） |
| seal_amount | float | 封单金额（万元，涨停时） |
| withdrawal_detected | bool | 是否检测到撤单 |
| trajectory_rating | str | 轨迹评级（强/中/弱） |

### 6. ExpectationScore（超预期分值）

记录个股的超预期评分和建议。

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | str | 股票代码 |
| volume_score | float | 量能分值（0-100） |
| price_score | float | 价格分值（0-100） |
| independence_score | float | 独立性分值（0-100） |
| total_score | float | 总分（0-100） |
| rating | str | 评级（优秀/良好/一般/较差） |
| recommendation | str | 操作建议（打板/低吸/观望/撤退） |
| confidence | float | 置信度（0-1） |

### 7. StatusScore（地位分值）

记录附加池个股的地位评分。

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| stock_code | str | 股票代码 |
| theme_recognition | float | 题材辨识度（0-100） |
| urgency | float | 量价急迫性（0-100） |
| emotion_hedge | float | 情绪对冲力（0-100） |
| total_score | float | 总分（0-100） |
| rank | int | 排名 |

### 8. AdditionalPool（附加票池）

记录竞价阶段发现的异动个股。

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| date | str | 日期（YYYY-MM-DD） |
| top_seals | List[Stock] | 顶级封单池 |
| rush_positioning | List[Stock] | 急迫抢筹池 |
| energy_burst | List[Stock] | 能量爆发池 |
| reverse_nuclear | List[Stock] | 极端反核池 |
| sector_formation | List[Stock] | 板块阵型池 |
| final_candidates | List[Stock] | 最终候选（经过地位判定） |

**使用示例：**

```python
from src.common.models import AdditionalPool, save_additional_pool, load_additional_pool

pool = AdditionalPool(
    date='2025-02-13',
    top_seals=[stock1],
    rush_positioning=[stock2],
    energy_burst=[stock3],
    reverse_nuclear=[],
    sector_formation=[stock4],
    final_candidates=[stock1, stock2, stock3]
)

# 保存
filepath = save_additional_pool(pool, 'data/stage3_output')

# 加载
restored = load_additional_pool(filepath)
```

### 9. SignalPlaybook（信号剧本）

定义特定信号的触发条件和应对策略。

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 剧本名称 |
| trigger_conditions | List[str] | 触发条件列表 |
| status_judgment | str | 地位判定 |
| strategy | str | 应对策略 |
| risk_level | str | 风险等级 |
| applicable_stocks | List[str] | 适用个股代码列表 |

### 10. Scenario（决策场景）

定义特定市场场景的判定和策略。

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 场景名称 |
| trigger_condition | str | 触发条件 |
| market_sentiment | str | 盘感描述 |
| strategy | str | 具体策略 |
| risk_warning | str | 风险提示 |
| confidence | float | 置信度（0-1） |

### 11. DecisionTree（决策树）

包含所有场景和当前判定。

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| scenarios | List[Scenario] | 所有场景列表 |
| current_scenario | str | 当前最可能的场景 |

### 12. NavigationReport（决策导航报告）

9:25后生成的完整决策指南。

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| date | str | 日期（YYYY-MM-DD） |
| generation_time | str | 生成时间（YYYY-MM-DD HH:MM:SS） |
| baseline_table | Dict[str, BaselineExpectation] | 及格线表 |
| signal_playbooks | List[SignalPlaybook] | 信号剧本列表 |
| decision_tree | DecisionTree | 决策树 |
| market_summary | str | 市场概况 |
| key_recommendations | List[str] | 关键建议列表 |

**使用示例：**

```python
from src.common.models import NavigationReport, save_navigation_report, load_navigation_report

report = NavigationReport(
    date='2025-02-13',
    generation_time='2025-02-13 09:26:30',
    baseline_table={'000001': expectation},
    signal_playbooks=[playbook1, playbook2],
    decision_tree=decision_tree,
    market_summary='大盘高开0.8%，涨停家数45家，市场情绪强势',
    key_recommendations=['韩建河山符合预期，可持有', '附加池中300XXX触发暴力抢筹信号']
)

# 保存
filepath = save_navigation_report(report, 'data/stage3_output')

# 加载
restored = load_navigation_report(filepath)
```

## JSON Schema验证

系统提供了完整的JSON Schema验证功能，确保数据格式正确。

### 使用Schema验证器

```python
from src.common.schema_validator import (
    validate_gene_pool_data,
    validate_baseline_expectation_data,
    validate_decision_navigation_data,
    validate_json_file
)

# 验证基因池数据
gene_pool_data = gene_pool.to_dict()
is_valid, errors = validate_gene_pool_data(gene_pool_data)
if not is_valid:
    print("验证失败:", errors)

# 验证基准预期数据
baseline_data = {
    'date': '2025-02-13',
    'expectations': {code: exp.to_dict() for code, exp in expectations.items()}
}
is_valid, errors = validate_baseline_expectation_data(baseline_data)

# 验证决策导航报告
report_data = report.to_dict()
is_valid, errors = validate_decision_navigation_data(report_data)

# 验证JSON文件
is_valid, errors = validate_json_file('data/stage1_output/gene_pool_20250213.json', 'gene_pool')
```

### Schema文件位置

所有Schema文件位于 `schemas/` 目录：

- `gene_pool_schema.json` - 基因池Schema
- `baseline_expectation_schema.json` - 基准预期Schema
- `decision_navigation_schema.json` - 决策导航报告Schema

## 序列化辅助函数

系统提供了便捷的序列化函数：

### 通用函数

```python
from src.common.models import (
    save_to_json,
    load_from_json,
    serialize_to_json_string,
    deserialize_from_json_string
)

# 保存任意对象到JSON文件
save_to_json(obj, 'path/to/file.json')

# 从JSON文件加载对象
obj = load_from_json('path/to/file.json', ModelClass)

# 序列化为JSON字符串
json_str = serialize_to_json_string(obj)

# 从JSON字符串反序列化
obj = deserialize_from_json_string(json_str, ModelClass)
```

### 专用函数

```python
# 基因池
save_gene_pool(gene_pool, output_dir)
load_gene_pool(filepath)

# 基准预期
save_baseline_expectations(expectations, date, output_dir)
load_baseline_expectations(filepath)

# 决策导航报告
save_navigation_report(report, output_dir)
load_navigation_report(filepath)

# 附加票池
save_additional_pool(pool, output_dir)
load_additional_pool(filepath)
```

## 数据流转

### Stage1 → Stage2

Stage1输出基因池，Stage2读取：

```python
# Stage1保存
gene_pool = GenePool(...)
filepath = save_gene_pool(gene_pool, 'data/stage1_output')

# Stage2读取
gene_pool = load_gene_pool('data/stage1_output/gene_pool_20250213.json')
```

### Stage2 → Stage3

Stage2输出基准预期，Stage3读取：

```python
# Stage2保存
expectations = {...}
filepath = save_baseline_expectations(expectations, '2025-02-13', 'data/stage2_output')

# Stage3读取
expectations = load_baseline_expectations('data/stage2_output/baseline_expectation_20250213.json')
```

### Stage3输出

Stage3输出决策导航报告和附加票池：

```python
# 保存决策导航报告
save_navigation_report(report, 'data/stage3_output')

# 保存附加票池
save_additional_pool(pool, 'data/stage3_output')
```

## 最佳实践

1. **始终使用提供的序列化函数**：避免手动处理JSON，使用 `save_*` 和 `load_*` 函数
2. **验证数据格式**：在保存重要数据前，使用Schema验证器检查格式
3. **处理可选字段**：`technical_levels` 等可选字段可能为 `None`，使用前检查
4. **错误处理**：序列化/反序列化可能失败，使用try-except捕获异常
5. **文件命名规范**：遵循 `{type}_{date}.json` 的命名格式

## 依赖项

数据模型模块需要以下依赖：

- Python 3.9+
- `dataclasses` (标准库)
- `json` (标准库)
- `jsonschema` (可选，用于Schema验证)

安装jsonschema：

```bash
pip install jsonschema
```

如果未安装jsonschema，Schema验证功能会被跳过，但不影响其他功能。
