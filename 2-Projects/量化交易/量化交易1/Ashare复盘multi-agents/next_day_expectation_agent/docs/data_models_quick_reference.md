# 数据模型快速参考

## 快速导入

```python
# 导入所有数据模型
from src.common.models import (
    Stock, TechnicalLevels, GenePool, BaselineExpectation,
    AuctionData, ExpectationScore, StatusScore, AdditionalPool,
    SignalPlaybook, Scenario, DecisionTree, NavigationReport
)

# 导入序列化函数
from src.common.models import (
    save_gene_pool, load_gene_pool,
    save_baseline_expectations, load_baseline_expectations,
    save_navigation_report, load_navigation_report,
    save_additional_pool, load_additional_pool
)

# 导入验证函数
from src.common.schema_validator import (
    validate_gene_pool_data,
    validate_baseline_expectation_data,
    validate_decision_navigation_data
)
```

## 常用操作

### 创建和保存基因池

```python
# 创建个股
stock = Stock(
    code='000001', name='平安银行', market_cap=100.0,
    price=10.5, change_pct=5.0, volume=1000000,
    amount=10500, turnover_rate=2.5, board_height=0,
    themes=['银行']
)

# 创建基因池
gene_pool = GenePool(
    date='2025-02-13',
    continuous_limit_up=[stock],
    failed_limit_up=[],
    recognition_stocks=[],
    trend_stocks=[]
)

# 保存
save_gene_pool(gene_pool, 'data/stage1_output')
```

### 加载和验证基因池

```python
# 加载
gene_pool = load_gene_pool('data/stage1_output/gene_pool_20250213.json')

# 验证
data = gene_pool.to_dict()
is_valid, errors = validate_gene_pool_data(data)
if not is_valid:
    for error in errors:
        print(error)
```

### 创建和保存基准预期

```python
# 创建基准预期
expectation = BaselineExpectation(
    stock_code='000001',
    stock_name='平安银行',
    expected_open_min=3.0,
    expected_open_max=5.0,
    expected_amount_min=10000,
    logic='昨日涨停+题材主升期',
    confidence=0.85
)

# 保存多个基准预期
expectations = {'000001': expectation}
save_baseline_expectations(expectations, '2025-02-13', 'data/stage2_output')
```

### 创建决策导航报告

```python
# 创建剧本
playbook = SignalPlaybook(
    name='暴力抢筹卡位流',
    trigger_conditions=['抢筹价差>3%', '量比>50'],
    status_judgment='卡位机会',
    strategy='重仓首选',
    risk_level='高风险',
    applicable_stocks=['000001']
)

# 创建场景
scenario = Scenario(
    name='整体超预期',
    trigger_condition='核心大哥全封一字',
    market_sentiment='资金极度亢奋',
    strategy='扫板附加池',
    risk_warning='顶背离风险',
    confidence=0.7
)

# 创建决策树
decision_tree = DecisionTree(
    scenarios=[scenario],
    current_scenario='整体超预期'
)

# 创建报告
report = NavigationReport(
    date='2025-02-13',
    generation_time='2025-02-13 09:26:30',
    baseline_table={'000001': expectation},
    signal_playbooks=[playbook],
    decision_tree=decision_tree,
    market_summary='市场强势',
    key_recommendations=['建议1', '建议2']
)

# 保存
save_navigation_report(report, 'data/stage3_output')
```

## 数据流转示例

### Stage1 → Stage2

```python
# Stage1: 生成并保存基因池
gene_pool = GenePool(...)
save_gene_pool(gene_pool, 'data/stage1_output')

# Stage2: 读取基因池
gene_pool = load_gene_pool('data/stage1_output/gene_pool_20250213.json')
# 使用基因池数据生成基准预期...
```

### Stage2 → Stage3

```python
# Stage2: 生成并保存基准预期
expectations = {...}
save_baseline_expectations(expectations, '2025-02-13', 'data/stage2_output')

# Stage3: 读取基准预期
expectations = load_baseline_expectations('data/stage2_output/baseline_expectation_20250213.json')
# 使用基准预期进行竞价监测...
```

## 文件命名规范

```
data/
├── stage1_output/
│   ├── gene_pool_20250213.json
│   ├── market_report_20250213.json
│   ├── emotion_report_20250213.json
│   └── theme_report_20250213.json
├── stage2_output/
│   ├── baseline_expectation_20250213.json
│   ├── overnight_variables_20250213.json
│   └── new_themes_20250213.json
└── stage3_output/
    ├── decision_navigation_20250213.json
    ├── additional_pool_20250213.json
    └── auction_monitoring_20250213.json
```

## 常见错误处理

### 文件不存在

```python
import os

filepath = 'data/stage1_output/gene_pool_20250213.json'
if os.path.exists(filepath):
    gene_pool = load_gene_pool(filepath)
else:
    print(f"文件不存在: {filepath}")
```

### 数据验证失败

```python
data = gene_pool.to_dict()
is_valid, errors = validate_gene_pool_data(data)

if not is_valid:
    print("数据验证失败:")
    for error in errors:
        print(f"  - {error}")
    # 处理错误...
```

### 可选字段检查

```python
if stock.technical_levels is not None:
    ma5 = stock.technical_levels.ma5
else:
    print("该股票没有技术位数据")
```

## 性能提示

1. **批量操作**: 使用字典存储多个对象，一次性保存
2. **延迟加载**: 只在需要时加载数据文件
3. **缓存**: 对频繁访问的数据进行缓存
4. **验证时机**: 在保存前验证，而不是每次使用时验证

## 调试技巧

### 打印JSON格式

```python
from src.common.models import serialize_to_json_string

# 美化打印
json_str = serialize_to_json_string(gene_pool, indent=2)
print(json_str)
```

### 检查数据结构

```python
# 转换为字典查看
data = gene_pool.to_dict()
print(data.keys())
print(len(data['continuous_limit_up']))
```

### 验证单个字段

```python
# 检查必需字段
assert gene_pool.date is not None
assert len(gene_pool.date) == 10  # YYYY-MM-DD

# 检查数值范围
assert 0 <= expectation.confidence <= 1
assert expectation.expected_open_max > expectation.expected_open_min
```

## 测试示例

```python
import pytest
from src.common.models import Stock, GenePool

def test_stock_creation():
    stock = Stock(
        code='000001', name='测试股票', market_cap=100.0,
        price=10.0, change_pct=5.0, volume=1000000,
        amount=10000, turnover_rate=2.0, board_height=0,
        themes=['测试']
    )
    assert stock.code == '000001'
    assert stock.change_pct == 5.0

def test_gene_pool_serialization():
    stock = Stock(...)
    gene_pool = GenePool(
        date='2025-02-13',
        continuous_limit_up=[stock],
        failed_limit_up=[],
        recognition_stocks=[],
        trend_stocks=[]
    )
    
    # 序列化和反序列化
    data = gene_pool.to_dict()
    restored = GenePool.from_dict(data)
    
    assert restored.date == gene_pool.date
    assert len(restored.continuous_limit_up) == 1
```

## 更多信息

详细文档请参考：
- [完整数据模型文档](data_models.md)
- [实现总结](task_3_implementation_summary.md)
- [测试代码](../tests/test_models.py)
