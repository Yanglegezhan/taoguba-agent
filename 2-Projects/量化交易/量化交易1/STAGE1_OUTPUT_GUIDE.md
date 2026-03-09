# Stage1 Agent 输出说明

## 📋 概述

Stage1 Agent 运行后会生成 **4个核心JSON文件**，用于次日核心个股超预期分析。

## 🎯 输出文件列表

### 1. 基因池文件 (gene_pool_YYYY-MM-DD.json)

**路径**: `data/stage1_output/gene_pool_2026-02-13.json`

**用途**: 包含当日所有核心个股的详细信息，是整个分析系统的数据基础

**内容结构**:
```json
{
  "date": "2026-02-13",
  "continuous_limit_up": [...],    // 连板梯队个股
  "failed_limit_up": [...],        // 炸板股
  "recognition_stocks": [...],     // 辨识度个股（使用wencai获取）
  "trend_stocks": [...],           // 趋势股
  "all_stocks": {...}              // 所有个股字典（按代码索引）
}
```

#### 1.1 连板梯队 (continuous_limit_up)

**数据来源**: 开盘啦连板梯队接口

**示例**:
```json
{
  "code": "002810",
  "name": "韩建河山",
  "market_cap": 45.2,              // 流通市值（亿元）
  "price": 15.68,                  // 最新价
  "change_pct": 10.0,              // 涨跌幅
  "volume": 1250000,               // 成交量（手）
  "amount": 19600,                 // 成交额（万元）
  "turnover_rate": 4.2,            // 换手率
  "board_height": 5,               // 连板高度（5板）
  "themes": ["AI", "数字经济"],    // 所属题材
  "technical_levels": {            // 技术位数据
    "ma5": 14.5,                   // 5日均线
    "ma10": 13.8,                  // 10日均线
    "ma20": 13.0,                  // 20日均线
    "previous_high": 16.0,         // 前期高点
    "chip_zone_low": 13.5,         // 筹码密集区下沿
    "chip_zone_high": 14.5,        // 筹码密集区上沿
    "distance_to_ma5_pct": 8.1,    // 距MA5距离（%）
    "distance_to_high_pct": -2.0   // 距前高距离（%）
  }
}
```

**关键指标说明**:
- `board_height`: 连板天数，越高越强势
- `turnover_rate`: 换手率，反映资金活跃度
- `distance_to_ma5_pct`: 正值表示在均线上方，负值表示下方
- `distance_to_high_pct`: 负值表示未突破前高，正值表示已突破

#### 1.2 炸板股 (failed_limit_up)

**数据来源**: 开盘啦历史炸板股接口

**特点**: 曾涨停但未封住的个股，可能是反包机会

**示例**:
```json
{
  "code": "300369",
  "name": "绿盟科技",
  "price": 10.48,
  "change_pct": 9.48,              // 涨幅接近涨停但未封住
  "amount": 2543999361.0,          // 成交额（元）
  "turnover_rate": 36.83,          // 高换手率
  "board_height": 0,               // 未连板
  "themes": ["AI安全", "AI应用"],
  "limit_up_time": 93000,          // 涨停时间（9:30:00）
  "open_time": 100500,             // 打开时间（10:05:00）
  "main_capital_net": -15000000,   // 主力资金净流入（元）
  "technical_levels": {...}
}
```

**关键指标**:
- `limit_up_time`: 涨停时间，越早越强
- `open_time`: 打开时间，与涨停时间差越小越弱
- `main_capital_net`: 主力资金流向，正值为流入

#### 1.3 辨识度个股 (recognition_stocks)

**数据来源**: 同花顺热门股排行（使用 wencai 获取）⭐

**用途**: 高市场关注度个股，具有较强的流动性和话题性

**示例**:
```json
{
  "code": "002009",                // 如果wencai返回了代码
  "name": "天奇股份",
  "hot_rank": 1,                   // 热度排名
  "market_cap": 0.0,               // 基础数据可能为空
  "price": 0.0,
  "change_pct": 0.0,
  "volume": 0.0,
  "amount": 0.0,
  "turnover_rate": 0.0,
  "board_height": 0,
  "themes": [],
  "technical_levels": null,        // 可能没有技术位数据
  "is_recognition_stock": true     // 标记为辨识度个股
}
```

**特点**:
- 数据来自同花顺热度排名前20
- 使用 wencai 获取，速度快（2-5秒）
- 可能包含股票代码（wencai 独有）
- 基础数据可能不完整，需要后续补充

#### 1.4 趋势股 (trend_stocks)

**数据来源**: 从基因池中筛选符合趋势特征的个股

**筛选标准**:
1. 价格在5日均线之上（距离0%-20%）
2. 均线呈多头排列（MA5 > MA10 > MA20）
3. 价格有效（price > 0）

**示例**:
```json
{
  "code": "600123",
  "name": "趋势股示例",
  "price": 25.50,
  "technical_levels": {
    "ma5": 24.0,
    "ma10": 23.5,
    "ma20": 23.0,
    "distance_to_ma5_pct": 6.25    // 在MA5上方6.25%
  },
  "is_trend_stock": true
}
```

**注意**: 连板股通常距离MA5较远（12-20%），不符合趋势股标准

#### 1.5 所有个股字典 (all_stocks)

**结构**: 以股票代码为键的字典

```json
{
  "002810": {...},  // 完整的股票对象
  "300369": {...},
  "600123": {...}
}
```

**用途**: 快速按代码查找个股信息

---

### 2. 大盘报告 (market_report_YYYYMMDD.json)

**路径**: `data/stage1_output/market_report_20260213.json`

**用途**: 大盘技术分析和趋势判断

**内容结构**:
```json
{
  "date": "2026-02-13",
  "current_price": 3018.56,        // 当前点位
  "change_pct": 0.62,              // 涨跌幅
  "support_levels": [              // 支撑位
    {
      "price": 3000.0,
      "strength": "强"             // 强/中/弱
    },
    {
      "price": 2990.0,
      "strength": "中"
    }
  ],
  "resistance_levels": [           // 压力位
    {
      "price": 3050.0,
      "strength": "强"
    },
    {
      "price": 3030.0,
      "strength": "中"
    }
  ],
  "short_term_scenario": "震荡修复",  // 短期场景
  "short_term_target": [3030, 3050], // 短期目标位
  "long_term_trend": "震荡趋势"       // 长期趋势
}
```

**关键指标**:
- `support_levels`: 支撑位，跌到此处可能反弹
- `resistance_levels`: 压力位，涨到此处可能回调
- `short_term_scenario`: 短期市场状态（震荡/上涨/下跌/修复）
- `long_term_trend`: 长期趋势判断

---

### 3. 情绪报告 (emotion_report_YYYYMMDD.json)

**路径**: `data/stage1_output/emotion_report_20260213.json`

**用途**: 市场情绪和资金状态分析

**内容结构**:
```json
{
  "date": "2026-02-13",
  "market_coefficient": 150.0,     // 市场系数（赚钱效应）
  "ultra_short_emotion": 45.5,     // 超短情绪值（0-100）
  "loss_effect": 28.3,             // 亏钱效应
  "cycle_node": "修复后分歧",       // 周期节点
  "profit_score": 65,              // 盈利分数（0-100）
  "position_suggestion": "半仓"     // 仓位建议
}
```

**关键指标说明**:
- `market_coefficient`: >100 赚钱效应，<100 亏钱效应
- `ultra_short_emotion`: >60 情绪高涨，<40 情绪低迷
- `cycle_node`: 市场所处周期阶段
  - "启动期" - 情绪开始回暖
  - "主升期" - 情绪高涨
  - "分歧期" - 情绪开始分化
  - "修复期" - 情绪低迷修复中
- `position_suggestion`: 仓位建议
  - "重仓" - 70-90%
  - "半仓" - 40-60%
  - "轻仓" - 10-30%
  - "空仓" - 0-10%

---

### 4. 题材报告 (theme_report_YYYYMMDD.json)

**路径**: `data/stage1_output/theme_report_20260213.json`

**用途**: 热门题材和板块分析

**内容结构**:
```json
{
  "date": "2026-02-13",
  "hot_themes": [
    {
      "name": "AI",
      "strength": 85,              // 强度（0-100）
      "cycle_stage": "主升期",      // 周期阶段
      "capacity": "大容量",         // 容量级别
      "leading_stocks": [          // 龙头股
        "002810",
        "300XXX"
      ]
    },
    {
      "name": "数字经济",
      "strength": 72,
      "cycle_stage": "启动期",
      "capacity": "中容量",
      "leading_stocks": ["600XXX"]
    }
  ],
  "market_summary": "市场整体强势，AI题材持续活跃"
}
```

**关键指标**:
- `strength`: 题材强度，>80 强势，60-80 中等，<60 弱势
- `cycle_stage`: 题材所处周期
  - "启动期" - 刚开始发酵
  - "主升期" - 持续上涨
  - "分歧期" - 开始分化
  - "衰退期" - 热度消退
- `capacity`: 容量级别
  - "大容量" - 可容纳大资金
  - "中容量" - 适合中等资金
  - "小容量" - 仅适合小资金

---

## 📊 数据流向

```
Stage1 Agent 运行
    ↓
1. 生成复盘报告
   ├─ 大盘报告 (market_report)
   ├─ 情绪报告 (emotion_report)
   └─ 题材报告 (theme_report)
    ↓
2. 构建基因池
   ├─ 扫描连板梯队 (kaipanla)
   ├─ 识别炸板股 (kaipanla)
   ├─ 识别辨识度个股 (wencai) ⭐
   └─ 识别趋势股 (从基因池筛选)
    ↓
3. 计算技术位
   └─ 为每只个股计算MA、前高、筹码区等
    ↓
4. 保存文件
   ├─ gene_pool_YYYY-MM-DD.json
   ├─ market_report_YYYYMMDD.json
   ├─ emotion_report_YYYYMMDD.json
   └─ theme_report_YYYYMMDD.json
    ↓
5. 存储到数据库（可选）
   └─ SQLite 历史数据库
```

## 🎯 使用场景

### 场景1: 次日选股

1. 查看 `gene_pool` 中的连板梯队
2. 筛选符合条件的个股：
   - 连板高度适中（2-5板）
   - 换手率合理（3-8%）
   - 距MA5距离适中（5-15%）
   - 题材热度高

### 场景2: 反包机会

1. 查看 `failed_limit_up` 炸板股
2. 筛选条件：
   - 涨停时间早（<10:00）
   - 打开时间晚（>14:00）
   - 主力资金净流入
   - 题材强势

### 场景3: 趋势跟踪

1. 查看 `trend_stocks` 趋势股
2. 筛选条件：
   - 多头排列
   - 距MA5距离5-10%
   - 成交量温和放大

### 场景4: 热点追踪

1. 查看 `recognition_stocks` 辨识度个股
2. 结合 `theme_report` 题材报告
3. 关注热度排名前10的个股

## 📈 数据质量

### 使用 wencai 后的改进

| 数据项 | 改进前 (kaipanla) | 改进后 (wencai) |
|--------|-------------------|-----------------|
| 获取速度 | 15-30秒 | 2-5秒 ⚡ |
| 股票代码 | ✗ 无 | ✓ 有 |
| 数据完整性 | 仅名称 | 名称+代码 |
| 稳定性 | 中等 | 高 |

### 数据更新频率

- 基因池: 每日盘后更新
- 复盘报告: 每日盘后更新
- 技术位: 每日盘后计算

## 🔍 数据验证

### 检查数据完整性

```python
import json

# 读取基因池
with open('data/stage1_output/gene_pool_2026-02-13.json', 'r', encoding='utf-8') as f:
    gene_pool = json.load(f)

# 检查各类个股数量
print(f"连板股: {len(gene_pool['continuous_limit_up'])} 只")
print(f"炸板股: {len(gene_pool['failed_limit_up'])} 只")
print(f"辨识度个股: {len(gene_pool['recognition_stocks'])} 只")
print(f"趋势股: {len(gene_pool['trend_stocks'])} 只")

# 检查技术位数据
for stock in gene_pool['continuous_limit_up']:
    if stock['technical_levels']:
        print(f"{stock['code']} {stock['name']}: 技术位完整")
    else:
        print(f"{stock['code']} {stock['name']}: 技术位缺失")
```

## 📝 注意事项

1. **辨识度个股可能没有代码**: 如果 wencai 未返回代码，`code` 字段为空字符串
2. **趋势股可能为空**: 在高波动日，可能没有符合趋势标准的个股
3. **技术位可能为 null**: 如果历史数据不足，技术位可能无法计算
4. **炸板股价格可能为0**: 如果未获取到分时数据，价格字段可能为0

## 🎉 总结

Stage1 Agent 输出的4个JSON文件构成了完整的市场分析数据集，为次日核心个股超预期分析提供了坚实的数据基础。通过集成 wencai，辨识度个股的获取速度提升了5-10倍，数据质量也得到了显著改善。
