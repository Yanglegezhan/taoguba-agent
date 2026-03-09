# 技术指标计算器实现文档

## 概述

本文档记录了 `TechnicalCalculator` 类的实现细节，该类负责计算个股的技术指标，包括移动平均线、前期高点、筹码密集区和距离百分比。

## 实现日期

2026-02-13

## 实现的功能

### 1. 移动平均线计算 (calculate_moving_averages)

**功能描述**：
- 计算5日、10日、20日移动平均线
- 支持数据不足时的降级处理

**算法**：
- MA5 = 最近5个交易日收盘价的平均值
- MA10 = 最近10个交易日收盘价的平均值
- MA20 = 最近20个交易日收盘价的平均值

**边界处理**：
- 数据不足时使用所有可用数据计算平均值
- 空数据时返回0值

### 2. 前期高点识别 (identify_previous_highs)

**功能描述**：
- 识别近60个交易日内的局部高点
- 返回按价格降序排列的高点列表

**算法**：
- 使用局部极大值方法
- 窗口大小：前后各2个交易日
- 如果某个价格点比其前后各2个交易日的价格都高，则认为是局部高点

**边界处理**：
- 数据不足5天时返回空列表
- 未找到局部高点时返回历史最高价

### 3. 筹码密集区计算 (calculate_chip_concentration)

**功能描述**：
- 计算近10个交易日的筹码密集区
- 返回筹码密集区的上沿和下沿

**算法**：
1. 计算成交量加权平均价格（VWAP）
   - VWAP = Σ(价格 × 成交量) / Σ成交量
2. 计算价格标准差
   - σ = √(Σ(价格 - 平均价格)² / N)
3. 筹码密集区 = VWAP ± 0.5σ

**边界处理**：
- 成交量为0时使用平均价格的±5%作为区间
- 价格和成交量长度不匹配时返回(0.0, 0.0)

### 4. 距离百分比计算 (calculate_distance_percentages)

**功能描述**：
- 计算当前价格与各技术位的距离百分比
- 包括距离MA5、MA10、MA20和前期高点的百分比

**算法**：
- 距离百分比 = (当前价格 - 技术位) / 技术位 × 100
- 正值表示在技术位上方
- 负值表示在技术位下方

**边界处理**：
- 技术位为0时返回0值

### 5. 完整技术位计算 (calculate_technical_levels)

**功能描述**：
- 整合所有技术指标计算
- 返回完整的 `TechnicalLevels` 对象

**流程**：
1. 计算移动平均线
2. 识别前期高点
3. 计算筹码密集区
4. 计算距离百分比
5. 构建并返回 `TechnicalLevels` 对象

**错误处理**：
- 捕获所有异常并记录日志
- 异常时返回默认值（全0）

## 测试覆盖

### 测试文件
`tests/test_technical_calculator.py`

### 测试用例统计
- 总测试用例：17个
- 通过率：100%

### 测试类别

1. **移动平均线测试** (3个测试)
   - 充足数据测试
   - 数据不足测试
   - 空数据测试

2. **前期高点识别测试** (3个测试)
   - 明显高点测试
   - 单调上涨测试
   - 数据不足测试

3. **筹码密集区测试** (4个测试)
   - 正常情况测试
   - 零成交量测试
   - 空数据测试
   - 长度不匹配测试

4. **距离百分比测试** (3个测试)
   - 价格在均线上方测试
   - 价格在均线下方测试
   - 均线为0测试

5. **完整技术位测试** (3个测试)
   - 完整数据测试
   - 最少数据测试
   - 错误处理测试

6. **集成测试** (1个测试)
   - 真实股票场景测试

## 性能考虑

### 时间复杂度
- `calculate_moving_averages`: O(n)，n为价格历史长度
- `identify_previous_highs`: O(n×w)，w为窗口大小（固定为5）
- `calculate_chip_concentration`: O(n)
- `calculate_distance_percentages`: O(1)
- `calculate_technical_levels`: O(n)

### 空间复杂度
- 所有方法的空间复杂度均为 O(1)（不考虑输入数据）

## 使用示例

```python
from src.stage1.technical_calculator import TechnicalCalculator
from src.common.models import Stock

# 创建计算器实例
calculator = TechnicalCalculator()

# 创建股票对象
stock = Stock(
    code="002810",
    name="韩建河山",
    market_cap=45.2,
    price=15.68,
    change_pct=10.0,
    volume=1250000,
    amount=19600,
    turnover_rate=4.2,
    board_height=5,
    themes=["AI", "数字经济"]
)

# 准备历史数据
price_history = [10.0, 10.5, 11.0, ..., 15.68]  # 至少20天
volume_history = [100000, 120000, 150000, ..., 1250000]

# 计算技术位
technical_levels = calculator.calculate_technical_levels(
    stock, price_history, volume_history
)

# 访问结果
print(f"MA5: {technical_levels.ma5}")
print(f"MA10: {technical_levels.ma10}")
print(f"MA20: {technical_levels.ma20}")
print(f"前期高点: {technical_levels.previous_high}")
print(f"筹码密集区: [{technical_levels.chip_zone_low}, {technical_levels.chip_zone_high}]")
print(f"距离MA5: {technical_levels.distance_to_ma5_pct}%")
print(f"距离前高: {technical_levels.distance_to_high_pct}%")
```

## 依赖关系

### 内部依赖
- `src.common.logger`: 日志记录
- `src.common.models`: 数据模型（Stock, TechnicalLevels）

### 外部依赖
- Python 标准库：typing, datetime

## 验证需求

本实现满足以下需求（来自 requirements.md）：

- **需求 3.1**: 计算5日、10日、20日均线 ✓
- **需求 3.2**: 识别前期高点 ✓
- **需求 3.3**: 计算筹码密集区 ✓
- **需求 3.4**: 计算距离MA5的百分比 ✓
- **需求 3.5**: 计算距离前高的百分比 ✓
- **需求 3.6**: 标注是否处于筹码密集区 ✓
- **需求 3.7**: 将技术位数据存储到基因池 ✓

## 后续工作

1. 可以考虑添加更多技术指标：
   - MACD
   - RSI
   - 布林带
   - KDJ

2. 性能优化：
   - 对于大量个股的批量计算，可以考虑并行处理
   - 缓存历史数据以避免重复计算

3. 算法改进：
   - 前期高点识别可以使用更复杂的峰值检测算法
   - 筹码密集区可以考虑使用更精确的成本分布算法

## 变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2026-02-13 | 1.0.0 | 初始实现 | Kiro AI |

## 相关文档

- [设计文档](../.kiro/specs/next-day-core-stock-expectation-analysis/design.md)
- [需求文档](../.kiro/specs/next-day-core-stock-expectation-analysis/requirements.md)
- [任务列表](../.kiro/specs/next-day-core-stock-expectation-analysis/tasks.md)
