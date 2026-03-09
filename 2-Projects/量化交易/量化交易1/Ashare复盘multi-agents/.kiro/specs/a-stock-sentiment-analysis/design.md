# Design Document: A股情绪分析Agent

## Overview

A股情绪分析Agent是一个基于LLM的智能分析系统，通过计算三条核心情绪指标线（大盘系数、超短情绪、亏钱效应），利用大语言模型识别市场周期节点和分析情绪状态，为短线交易提供决策支持。

系统采用"数据驱动+LLM智能分析"的混合架构：
- 数据层：通过AkShare/TuShare API获取市场原始数据（15个交易日）
- 计算层：使用确定性算法计算三条情绪指标线（无需计算均线）
- 分析层：利用LLM进行周期节点识别和情绪分析（LLM自行判断趋势）
- 输出层：生成包含图表和分析的Markdown/PDF报告

**重要说明**：
- 系统分析最近15个交易日的数据（非自然日）
- 对最后一日进行深度分析，包含与昨日（前一个交易日）的环比
- 图表中的周期节点标注在对应交易日期的下方

### 核心设计原则

1. **职责分离**：系统负责数据获取和指标计算，LLM负责情绪分析和节点识别
2. **可复用性**：复用现有大盘分析Agent的基础设施（LLM客户端、配置模块、数据源）
3. **可扩展性**：支持通过配置文件扩展数据源和LLM提供商
4. **可测试性**：确定性计算使用属性测试，LLM分析使用示例测试

## Architecture

系统采用分层架构，从下到上依次为：

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Interface                         │
│              (sentiment_cli.py)                          │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│              Sentiment Analysis Agent                    │
│           (sentiment_agent.py)                           │
│  - 协调整个分析流程                                        │
│  - 调用各模块完成分析                                      │
└─────────────────────────────────────────────────────────┘
          │              │              │              │
┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Data Fetcher│ │  Sentiment   │ │     LLM      │ │    Report    │
│             │ │  Calculator  │ │   Analyzer   │ │   Exporter   │
│ - API调用   │  │ - 指标计算   │ │ - 提示词构建 │ │ - 图表生成   │
│ - 数据验证   │  │             │ │ - LLM调用    │ │ - MD/PDF导出 │
└─────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
          │                                │
┌─────────────────────────────────────────────────────────┐
│              Shared Infrastructure                       │
│  - LLM Client (复用)                                     │
│  - Config Loader (复用)                                  │
│  - AkShare Source (复用/扩展)                            │
└─────────────────────────────────────────────────────────┘
```

### 数据流

1. **数据获取阶段**：
   - CLI接收用户输入（日期、格式等）
   - Data Fetcher通过API获取15个交易日的市场原始数据（非自然日）
   - 数据验证确保所有必需字段完整

2. **指标计算阶段**：
   - Sentiment Calculator计算三条情绪指标线
   - 生成结构化的情绪数据（15个交易日）

3. **LLM分析阶段**：
   - LLM Analyzer构建提示词（包含周期方法论上下文）
   - 调用LLM识别周期节点和分析情绪
   - 解析LLM响应提取结构化结果

4. **报告生成阶段**：
   - Chart Generator绘制三线趋势图
   - Report Exporter组织报告内容
   - 导出Markdown或PDF格式


## Components and Interfaces

### 1. Data Fetcher (数据获取模块)

**职责**：从开盘啦API/AkShare/TuShare API获取市场原始数据并验证完整性

**推荐实现：KaipanlaSentimentSource**

使用kaipanla_crawler获取数据，提供更准确和全面的市场情绪数据。

**接口**：
```python
class KaipanlaSentimentSource:
    def __init__(self, max_retries: int = 3, timeout: int = 30):
        """初始化数据源
        
        Args:
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
        """
        self.crawler = KaipanlaCrawler()
        
    def fetch_day_data(self, trading_date: date) -> MarketDayData:
        """获取单个交易日的市场数据
        
        Args:
            trading_date: 交易日期
            
        Returns:
            MarketDayData对象
            
        Raises:
            DataFetchError: 数据获取失败
        """
        
    def fetch_sentiment_market_data(
        self, 
        end_date: date, 
        num_days: int = 15
    ) -> List[MarketDayData]:
        """获取指定交易日前N个交易日的市场数据
        
        Args:
            end_date: 截止交易日（必须是交易日）
            num_days: 交易日数量（默认15，非自然日）
            
        Returns:
            MarketDayData列表，包含所有必需字段，按日期升序排列
        Raises:
            DataFetchError: 数据获取失败
            ValidationError: 数据验证失败
        """
        
    def validate_data(self, data: MarketDayData) -> ValidationResult:
        """验证单日数据完整性"""
    
    def _get_trading_days(self, end_date: date, num_days: int) -> List[date]:
        """获取交易日列表（自动识别交易日）"""
    
    def _parse_consecutive_limit_up(self, ladder_data: pd.Series) -> Tuple[Dict[int, int], int]:
        """解析连板梯队数据"""
    
    def _get_max_consecutive_info(self, trading_date: date) -> Tuple[str, str]:
        """获取最高板个股信息（名字和概念）"""
```

**备选实现：AKShareSentimentSource**

使用AKShare API获取数据（部分指标为估算值）。

**数据模型**：
```python
@dataclass
class MarketDayData:
    """单日市场数据"""
    trading_date: date  # 交易日期（非自然日）
    index_change: float  # 指数涨幅
    all_a_change: float  # 全A涨幅
    up_count: int  # 上涨家数
    down_count: int  # 下跌家数
    limit_up_count: int  # 涨停数
    consecutive_limit_up: Dict[int, int]  # 连板家数分布
    max_consecutive: int  # 最高板
    max_consecutive_stocks: str  # 最高板个股名字（多个用/分隔）
    max_consecutive_concepts: str  # 最高板个股概念（多个用/分隔）
    yesterday_limit_up_performance: float  # 昨日涨停今日表现
    new_100day_high_count: int  # 新增百日新高个股家数
    limit_down_count: int  # 跌停数
    blown_limit_up_count: int  # 炸板家数
    blown_limit_up_rate: float  # 炸板率
    large_pullback_count: int  # 大幅回撤家数
    yesterday_blown_performance: float  # 昨日断板今日表现
```

**数据源对比**：

| 指标 | AKShare | 开盘啦 | 说明 |
|------|---------|--------|------|
| 涨停数 | ✅ | ✅ 更准确 | 开盘啦准确率99%+ |
| 炸板率 | ⚠️ 估算 | ✅ 精确 | 开盘啦提供真实炸板率 |
| 连板梯队 | ⚠️ 部分 | ✅ 完整 | 开盘啦提供详细分布 |
| 最高板个股 | ❌ | ✅ | 开盘啦独有 |
| 百日新高 | ⚠️ 估算 | ✅ 精确 | 开盘啦提供真实数据 |
| 昨日断板今表现 | ❌ | ✅ | 开盘啦独有 |

**实现细节**：

1. **交易日识别**：通过尝试获取数据判断是否为交易日
2. **连板梯队解析**：从开盘啦API的一板、二板、三板、高度板字段解析
3. **最高板个股**：从涨停原因板块数据中提取连板天数最多的股票
4. **炸板家数计算**：根据炸板率和涨停数反推
5. **错误处理**：自动重试、详细日志、友好错误提示

### 2. Sentiment Calculator (情绪指标计算模块)

**职责**：根据市场原始数据计算三条情绪指标线

**接口**：
```python
class SentimentCalculator:
    @staticmethod
    def calculate_market_coefficient(up_count: int) -> float:
        """计算大盘系数 = 上涨家数 / 20"""
        
    @staticmethod
    def calculate_ultra_short_sentiment(
        limit_up_count: int,
        new_100day_high_count: int,
        yesterday_limit_up_performance: float
    ) -> float:
        """计算超短情绪 = 涨停数 + (新增百日新高 / 2) + (昨日涨停表现 * 10)
        
        注意：昨日涨停表现已经是百分比格式（如2.3表示2.3%），所以乘以10而不是1000
        """
        
    @staticmethod
    def calculate_loss_effect(
        blown_limit_up_rate: float,
        limit_down_count: int,
        large_pullback_count: int
    ) -> float:
        """计算亏钱效应 = (炸板率 * 100) + (跌停数 + 大幅回撤家数) * 2"""
        
    def calculate_all_indicators(
        self, 
        data_list: List[MarketDayData]
    ) -> SentimentIndicators:
        """计算所有指标
        
        Args:
            data_list: 市场数据列表（15个交易日）
            
        Returns:
            SentimentIndicators对象，包含三条线的数据
        """
        
    @staticmethod
    def calculate_change_pct(current: float, previous: float) -> float:
        """计算环比变化百分比"""
```

**数据模型**：
```python
@dataclass
class DailySentiment:
    """单日情绪指标"""
    trading_date: date  # 交易日期
    market_coefficient: float  # 大盘系数
    ultra_short_sentiment: float  # 超短情绪
    loss_effect: float  # 亏钱效应

@dataclass
class SentimentIndicators:
    """情绪指标数据（15个交易日）"""
    daily_sentiments: List[DailySentiment]
    
    def get_latest(self) -> DailySentiment:
        """获取最新一日的情绪指标"""
        return self.daily_sentiments[-1]
    
    def get_previous(self) -> DailySentiment:
        """获取昨日（前一个交易日）的情绪指标"""
        return self.daily_sentiments[-2]
    
    def calculate_change_pct(self) -> Dict[str, float]:
        """计算最新一日与昨日的环比变化百分比"""
        latest = self.get_latest()
        previous = self.get_previous()
        return {
            "market_coefficient_change": (latest.market_coefficient - previous.market_coefficient) / previous.market_coefficient * 100,
            "ultra_short_sentiment_change": (latest.ultra_short_sentiment - previous.ultra_short_sentiment) / previous.ultra_short_sentiment * 100,
            "loss_effect_change": (latest.loss_effect - previous.loss_effect) / previous.loss_effect * 100,
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """转换为DataFrame便于分析"""
        pass

**职责**：构建提示词、调用LLM进行情绪分析和周期节点识别、解析LLM响应

**接口**：
```python
class SentimentLLMAnalyzer:
    def __init__(
        self, 
        llm_client: LLMClient,
        prompt_engine: PromptEngine
    ):
        """初始化LLM分析器"""
        
    def analyze_sentiment(
        self, 
        indicators: SentimentIndicators,
        market_data: List[MarketDayData]
    ) -> SentimentAnalysisResult:
        """执行情绪分析
        
        Args:
            indicators: 情绪指标数据
            market_data: 市场原始数据
            
        Returns:
            SentimentAnalysisResult对象
        """
        
    def build_prompt(
        self,
        indicators: SentimentIndicators,
        market_data: List[MarketDayData]
    ) -> str:
        """构建LLM提示词
        
        包含：
        - 系统提示词（周期方法论、判断依据）
        - 数据上下文（15日三线数据表格 + 最新日与昨日环比）
        - Few-shot示例
        - 输出格式要求
        """
        
    def parse_response(self, response: str) -> SentimentAnalysisResult:
        """解析LLM响应
        
        提取：
        - 周期节点列表
        - 当前阶段判断
        - 赚钱效应评分
        - 操作策略建议
        - 下一节点预判
        """
```

**数据模型**：
```python
@dataclass
class CycleNode:
    """周期节点"""
    date: date
    node_type: str  # 冰冰点、修复、分歧、共振、退潮、背离、三线耦合
    description: str
    key_indicators: Dict[str, float]

@dataclass
class SentimentAnalysisResult:
    """情绪分析结果"""
    cycle_nodes: List[CycleNode]  # 识别的周期节点
    current_stage: str  # 当前所处阶段
    stage_position: str  # 在演绎顺序中的位置
    money_making_score: int  # 赚钱效应评分 (0-100)
    divergence_analysis: str  # 背离分析
    detail_analysis: str  # 细节盘点
    strategy_suggestion: str  # 操作策略建议
    risk_warning: str  # 风险提示
    next_node_prediction: str  # 下一节点预判
```

### 4. Chart Generator (图表生成模块)

**职责**：绘制三线趋势图，标注周期节点

**接口**：
```python
class SentimentChartGenerator:
    def generate_chart(
        self,
        indicators: SentimentIndicators,
        cycle_nodes: List[CycleNode],
        output_path: str
    ) -> str:
        """生成三线趋势图
        
        Args:
            indicators: 情绪指标数据
            cycle_nodes: 周期节点列表
            output_path: 输出文件路径
            
        Returns:
            生成的图片文件路径
        """
```

**实现方案**：
- 使用matplotlib+seaborn绘制折线图
- 三条主线：大盘系数（紫色）、超短情绪（红色粗虚线）、亏钱效应（绿色）
- 节点标注：在对应交易日期的**下方**添加标记和文字（重要：标注位置在x轴日期下方）
- 图例：说明三条线的含义和节点类型
- 输出格式：PNG（可嵌入Markdown）


### 5. Report Exporter (报告导出模块)

**职责**：组织报告内容，导出Markdown或PDF格式

**接口**：
```python
class SentimentReportExporter:
    def export_report(
        self,
        indicators: SentimentIndicators,
        analysis_result: SentimentAnalysisResult,
        chart_path: str,
        output_format: str = "md",
        output_path: Optional[str] = None
    ) -> str:
        """导出情绪分析报告
        
        Args:
            indicators: 情绪指标数据
            analysis_result: LLM分析结果
            chart_path: 图表文件路径
            output_format: 输出格式 (md/pdf)
            output_path: 输出路径（可选）
            
        Returns:
            报告文件路径
        """
```

**报告结构**：
```markdown
# A股情绪分析报告

**分析日期**: YYYY-MM-DD
**数据时间范围**: YYYY-MM-DD 至 YYYY-MM-DD（15个交易日）

## 一、核心指标概览

| 指标 | 最新值 | 昨日值 | 环比变化 |
|------|--------|--------|----------|
| 大盘系数 | XX.XX | XX.XX | +X.XX% |
| 超短情绪 | XX.XX | XX.XX | +X.XX% |
| 亏钱效应 | XX.XX | XX.XX | +X.XX% |

**赚钱效应评分**: XX/100

## 二、情绪趋势图

![三线趋势图](chart.png)

*注：图中周期节点标注在对应交易日期下方*

## 三、周期节点识别

### 识别的周期节点

1. **YYYY-MM-DD - 冰冰点**
   - 描述：...
   - 关键指标：...

### 当前所处阶段

**阶段**: 修复后分歧
**位置**: 周期演绎顺序第3阶段

## 四、背离分析

[LLM生成的背离分析内容]

## 五、细节盘点

[LLM生成的细节分析内容]

## 六、操作策略建议

**仓位建议**: [轻仓/半仓/重仓/空仓]

**策略**: [LLM生成的策略建议]

**风险提示**: [LLM生成的风险提示]

## 七、下一节点预判

[LLM生成的下一节点预判]

```

### 6. Sentiment Analysis Agent (主控模块)

**职责**：协调整个分析流程，处理错误和异常

**接口**：
```python
class SentimentAnalysisAgent:
    def __init__(self, config: AgentConfig):
        """初始化Agent"""
        
    def analyze(
        self,
        analysis_date: Optional[date] = None,
        output_format: str = "md",
        output_path: Optional[str] = None
    ) -> AnalysisResult:
        """执行完整的情绪分析流程
        
        Args:
            analysis_date: 分析日期（默认最新交易日）
            output_format: 输出格式 (md/pdf)
            output_path: 输出路径（可选）
            
        Returns:
            AnalysisResult对象
        """
```

**执行流程**：
1. 数据获取（Data Fetcher）
2. 指标计算（Sentiment Calculator）
3. LLM分析（LLM Analyzer）
4. 图表生成（Chart Generator）
5. 报告导出（Report Exporter）

每个阶段都有错误处理和进度显示。


## Data Models

### 核心数据模型

```python
from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Dict
from enum import Enum

# ============ 市场数据模型 ============

@dataclass
class MarketDayData:
    """单日市场数据（从API获取的原始数据）"""
    date: date
    index_change: float  # 指数涨幅 (%)
    all_a_change: float  # 全A涨幅 (%)
    up_count: int  # 上涨家数
    down_count: int  # 下跌家数
    limit_up_count: int  # 涨停数
    consecutive_limit_up: Dict[int, int]  # 连板家数分布 {连板数: 家数}
    max_consecutive: int  # 最高板
    yesterday_limit_up_performance: float  # 昨日涨停今日表现 (%)
    new_100day_high_count: int  # 新增百日新高个股家数
    limit_down_count: int  # 跌停数
    blown_limit_up_count: int  # 炸板家数
    blown_limit_up_rate: float  # 炸板率
    large_pullback_count: int  # 大幅回撤家数
    yesterday_blown_performance: float  # 昨日断板今日表现 (%)

# ============ 情绪指标模型 ============

@dataclass
class DailySentiment:
    """单日情绪指标"""
    date: date
    market_coefficient: float  # 大盘系数
    ultra_short_sentiment: float  # 超短情绪
    loss_effect: float  # 亏钱效应

@dataclass
class SentimentIndicators:
    """情绪指标数据（15个交易日）"""
    daily_sentiments: List[DailySentiment]
    
    def get_latest(self) -> DailySentiment:
        """获取最新一日的情绪指标"""
        return self.daily_sentiments[-1]
    
    def to_dataframe(self) -> pd.DataFrame:
        """转换为DataFrame便于分析"""
        pass

# ============ 周期节点模型 ============

class NodeType(Enum):
    """周期节点类型"""
    ICE_POINT = "冰冰点"  # 周期之始
    RECOVERY = "冰冰点次日修复"
    DIVERGENCE_AFTER_RECOVERY = "修复后分歧"  # 第二买点
    RESONANCE_HIGH = "共振高潮"
    RETREAT = "退潮阶段"
    ICE_POINT_NEW = "冰点"  # 新周期
    TOP_DIVERGENCE = "顶背离"  # 大盘在上情绪在下
    BOTTOM_DIVERGENCE = "底背离"  # 大盘在下情绪在上
    THREE_LINE_COUPLING = "三线耦合"
    # 上述的节点类型有一些不冲突，比如，某日的情绪可以同时具备冰点+底背离 或者共振高潮和三线耦合等等。
@dataclass
class CycleNode:
    """周期节点"""
    trading_date: date  # 交易日期
    node_type: NodeType
    description: str
    key_indicators: Dict[str, float]  # 关键指标数值
    confidence: str  # 置信度 (高/中/低)

# ============ LLM分析结果模型 ============

@dataclass
class SentimentAnalysisResult:
    """情绪分析结果"""
    cycle_nodes: List[CycleNode]  # 识别的周期节点
    current_stage: str  # 当前所处阶段
    stage_position: str  # 在演绎顺序中的位置
    money_making_score: int  # 赚钱效应评分 (0-100)
    divergence_analysis: str  # 背离分析
    detail_analysis: str  # 细节盘点
    strategy_suggestion: str  # 操作策略建议
    position_advice: str  # 仓位建议
    risk_warning: str  # 风险提示
    next_node_prediction: str  # 下一节点预判

# ============ 配置模型 ============

@dataclass
class DataSourceConfig:
    """数据源配置"""
    provider: str  # akshare / tushare
    api_key: Optional[str] = None  # TuShare需要
    timeout: int = 30
    max_retries: int = 3

@dataclass
class AgentConfig:
    """Agent配置"""
    llm_config: LLMConfig  # 复用现有的LLM配置
    data_source_config: DataSourceConfig
    template_dir: str = "prompts/sentiment/"
    output_dir: str = "output/sentiment/"
    num_trading_days: int = 15  # 分析的交易日数量（默认15）
    verbose: bool = True

# ============ 结果模型 ============

@dataclass
class AnalysisResult:
    """分析结果"""
    success: bool
    report_path: Optional[str] = None
    chart_path: Optional[str] = None
    analysis_result: Optional[SentimentAnalysisResult] = None
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
```

### 数据验证

所有数据模型都应实现验证方法：

```python
class MarketDayData:
    def validate(self) -> Tuple[bool, Optional[str]]:
        """验证数据完整性和合理性"""
        # 检查必需字段
        # 检查数值范围
        # 检查逻辑一致性
        pass
```


## Correctness Properties

*属性（Property）是一个特征或行为，应该在系统的所有有效执行中保持为真。属性是人类可读规范和机器可验证正确性保证之间的桥梁。通过属性测试，我们可以验证系统在大量随机输入下的正确性。*

### Property 1: 大盘系数计算正确性
*For any* 非负整数上涨家数，计算得到的大盘系数应该等于上涨家数除以20
**Validates: Requirements 1.1**

### Property 2: 超短情绪计算正确性
*For any* 有效的涨停数、新增百日新高家数、昨日涨停表现，计算得到的超短情绪应该等于涨停数加上新增百日新高除以2再加上昨日涨停表现乘以1000
**Validates: Requirements 1.2**

### Property 3: 亏钱效应计算正确性
*For any* 有效的炸板率、跌停数、大幅回撤家数，计算得到的亏钱效应应该等于炸板率乘以100加上跌停数与大幅回撤家数之和乘以2
**Validates: Requirements 1.3**

### Property 4: 缺失字段错误处理
*For any* 包含缺失必需字段的市场数据，系统应该返回错误信息并明确标识缺失的字段名称
**Validates: Requirements 1.4**

### Property 5: 指标计算完整性
*For any* 成功计算的情绪指标，返回结果应该包含三条指标线的完整数据
**Validates: Requirements 1.5**

### Property 6: CSV解析健壮性
*For any* 格式正确的CSV文件，解析后应该返回包含所有必需字段的MarketDayData列表，且所有日期字段为交易日
**Validates: Requirements 2.2**

### Property 7: 数据验证错误信息
*For any* 缺少必需字段的导入数据，验证应该失败并返回包含所有缺失字段名称的错误信息
**Validates: Requirements 2.4**

### Property 8: 标准化数据结构
*For any* 成功导入的数据，返回的MarketDayData对象应该包含所有必需字段且类型正确
**Validates: Requirements 2.5**

### Property 9: 报告章节完整性
*For any* 生成的情绪分析报告，应该包含核心指标概览、趋势图、周期节点识别、背离分析、细节盘点、操作策略建议、下一节点预判等所有必需章节
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7**

### Property 10: 报告文件路径返回
*For any* 成功导出的报告，系统应该返回有效的报告文件路径且文件实际存在
**Validates: Requirements 5.10**

### Property 11: 提示词包含周期方法论
*For any* 构建的LLM提示词，应该包含周期方法论的完整定义和演绎顺序说明
**Validates: Requirements 6.1**

### Property 12: 提示词包含节点识别标准
*For any* 构建的LLM提示词，应该包含各类周期节点的识别标准和特征描述
**Validates: Requirements 6.2**

### Property 13: 提示词包含关键概念
*For any* 构建的LLM提示词，应该包含背离、共振、三线耦合等关键概念的详细解释
**Validates: Requirements 6.3**

### Property 14: 提示词包含数据表格
*For any* 构建的LLM提示词，应该包含15个交易日的三线数据以结构化格式呈现，并包含最新日与昨日的环比数据
**Validates: Requirements 6.6**

### Property 15: 配置加载健壮性
*For any* 有效的配置文件，系统应该成功加载LLM配置、数据源配置、输出配置
**Validates: Requirements 7.1, 7.2, 7.3**

### Property 16: 配置缺失降级
*For any* 缺失或格式错误的配置文件，系统应该使用默认配置并记录警告信息
**Validates: Requirements 7.5**

### Property 17: API调用重试机制
*For any* API调用失败，系统应该自动重试最多3次并记录错误日志
**Validates: Requirements 8.1**

### Property 18: 异常数据标记
*For any* 包含异常值的计算结果，系统应该标记异常数据并记录警告
**Validates: Requirements 8.3**

### Property 19: 错误信息清晰性
*For any* 系统错误，应该提供清晰的错误信息和可能的解决方案
**Validates: Requirements 8.8**


## Error Handling

### 错误分类

系统错误分为以下几类：

1. **数据获取错误** (DataFetchError)
   - API调用失败
   - 网络超时
   - 数据源不可用
   - 处理策略：重试3次，失败后返回详细错误信息

2. **数据验证错误** (ValidationError)
   - 必需字段缺失
   - 数据类型错误
   - 数值范围异常
   - 处理策略：立即失败，返回缺失字段列表

3. **计算错误** (CalculationError)
   - 除零错误
   - 数值溢出
   - 处理策略：使用默认值或跳过该数据点，记录警告

4. **LLM调用错误** (LLMError)
   - API调用失败
   - 响应超时
   - 响应解析失败
   - 处理策略：重试3次，失败后返回错误信息

5. **文件操作错误** (FileError)
   - 文件不存在
   - 权限不足
   - 磁盘空间不足
   - 处理策略：返回详细错误信息和建议

### 错误处理策略

```python
class ErrorHandler:
    """统一错误处理器"""
    
    @staticmethod
    def handle_data_fetch_error(error: Exception) -> ErrorResult:
        """处理数据获取错误"""
        if isinstance(error, TimeoutError):
            return ErrorResult(
                error_type="TIMEOUT",
                message="数据获取超时",
                suggestion="请检查网络连接或稍后重试",
                retryable=True
            )
        # ... 其他错误类型
    
    @staticmethod
    def handle_validation_error(
        missing_fields: List[str]
    ) -> ErrorResult:
        """处理数据验证错误"""
        return ErrorResult(
            error_type="VALIDATION",
            message=f"数据验证失败，缺失字段: {', '.join(missing_fields)}",
            suggestion="请检查数据源或手动补充缺失数据",
            retryable=False
        )
```

### 日志记录

所有错误和警告都应记录到日志文件：

```python
import logging

logger = logging.getLogger("sentiment_agent")
logger.setLevel(logging.INFO)

# 文件处理器
file_handler = logging.FileHandler("sentiment_agent.log")
file_handler.setLevel(logging.DEBUG)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 格式化
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)
```

### 降级策略

当某些功能失败时，系统应该尽可能提供降级服务：

1. **图表生成失败** → 仍然生成文本报告
2. **PDF导出失败** → 降级为Markdown格式
3. **LLM分析失败** → 提供基础指标数据和图表
4. **部分数据缺失** → 使用可用数据继续分析，标注缺失部分


## Testing Strategy

### 测试方法论

系统采用**双重测试策略**：单元测试和属性测试相结合，确保全面的代码覆盖和正确性验证。

- **单元测试**：验证特定示例、边界情况和错误条件
- **属性测试**：验证通用属性在大量随机输入下的正确性
- 两者互补：单元测试捕获具体bug，属性测试验证通用正确性

### 属性测试配置

使用Python的`hypothesis`库进行属性测试：

```python
from hypothesis import given, strategies as st
import hypothesis.strategies as st

# 每个属性测试至少运行100次
@given(st.integers(min_value=0, max_value=10000))
@settings(max_examples=100)
def test_market_coefficient_calculation(up_count):
    """Feature: a-stock-sentiment-analysis, Property 1: 大盘系数计算正确性"""
    result = SentimentCalculator.calculate_market_coefficient(up_count)
    expected = up_count / 20
    assert abs(result - expected) < 0.0001
```

### 测试覆盖范围

#### 1. 情绪指标计算模块测试

**单元测试**：
```python
def test_market_coefficient_zero():
    """测试上涨家数为0的情况"""
    assert SentimentCalculator.calculate_market_coefficient(0) == 0.0

def test_ultra_short_sentiment_typical():
    """测试典型的超短情绪计算"""
    result = SentimentCalculator.calculate_ultra_short_sentiment(
        limit_up_count=50,
        new_100day_high_count=20,
        yesterday_limit_up_performance=0.05
    )
    expected = 50 + (20 / 2) + (0.05 * 1000)
    assert abs(result - expected) < 0.0001
```

**属性测试**：
```python
@given(
    st.integers(min_value=0, max_value=500),
    st.integers(min_value=0, max_value=500),
    st.floats(min_value=-1.0, max_value=1.0)
)
@settings(max_examples=100)
def test_ultra_short_sentiment_property(
    limit_up_count, new_100day_high_count, yesterday_performance
):
    """Feature: a-stock-sentiment-analysis, Property 2: 超短情绪计算正确性"""
    result = SentimentCalculator.calculate_ultra_short_sentiment(
        limit_up_count, new_100day_high_count, yesterday_performance
    )
    expected = limit_up_count + (new_100day_high_count / 2) + (yesterday_performance * 1000)
    assert abs(result - expected) < 0.0001
```

#### 2. 数据获取模块测试

**单元测试**：
```python
def test_fetch_market_data_success():
    """测试成功获取市场数据"""
    fetcher = SentimentDataFetcher(config)
    data = fetcher.fetch_market_data(date(2024, 1, 15), num_days=15)
    assert len(data) == 15
    assert all(isinstance(d, MarketDayData) for d in data)

def test_validate_data_missing_fields():
    """测试缺失字段的数据验证"""
    incomplete_data = MarketDayData(date=date(2024, 1, 15))
    result = fetcher.validate_data(incomplete_data)
    assert not result.is_valid
    assert "limit_up_count" in result.missing_fields
```

**属性测试**：
```python
@given(st.data())
@settings(max_examples=100)
def test_csv_parsing_property(data):
    """Feature: a-stock-sentiment-analysis, Property 6: CSV解析健壮性"""
    # 生成随机但格式正确的CSV
    csv_content = generate_valid_csv(data)
    result = parse_csv(csv_content)
    assert all(hasattr(d, field) for d in result for field in REQUIRED_FIELDS)
```

#### 3. LLM分析模块测试

**单元测试**：
```python
def test_build_prompt_contains_methodology():
    """测试提示词包含周期方法论"""
    analyzer = SentimentLLMAnalyzer(llm_client, prompt_engine)
    prompt = analyzer.build_prompt(indicators, market_data)
    assert "冰冰点" in prompt
    assert "共振" in prompt
    assert "背离" in prompt
    assert "三线耦合" in prompt

def test_parse_response_success():
    """测试成功解析LLM响应"""
    response = """
    {
        "cycle_nodes": [...],
        "current_stage": "修复后分歧",
        "money_making_score": 65
    }
    """
    result = analyzer.parse_response(response)
    assert result.current_stage == "修复后分歧"
    assert result.money_making_score == 65
```

**属性测试**：
```python
@given(st.data())
@settings(max_examples=100)
def test_prompt_completeness_property(data):
    """Feature: a-stock-sentiment-analysis, Property 11-14: 提示词完整性"""
    indicators = generate_random_indicators(data)
    market_data = generate_random_market_data(data)
    prompt = analyzer.build_prompt(indicators, market_data)
    
    # 验证包含必需元素
    assert "周期方法论" in prompt or "冰冰点" in prompt
    assert "背离" in prompt
    assert "共振" in prompt
    # 验证包含数据表格
    assert "大盘系数" in prompt
    assert "超短情绪" in prompt
    assert "亏钱效应" in prompt
```

#### 4. 报告生成模块测试

**单元测试**：
```python
def test_export_markdown_report():
    """测试导出Markdown报告"""
    exporter = SentimentReportExporter()
    report_path = exporter.export_report(
        indicators, analysis_result, chart_path, output_format="md"
    )
    assert os.path.exists(report_path)
    assert report_path.endswith(".md")

def test_report_contains_all_sections():
    """测试报告包含所有必需章节"""
    content = read_file(report_path)
    assert "核心指标概览" in content
    assert "情绪趋势图" in content
    assert "周期节点识别" in content
    assert "操作策略建议" in content
```

**属性测试**：
```python
@given(st.data())
@settings(max_examples=100)
def test_report_structure_property(data):
    """Feature: a-stock-sentiment-analysis, Property 9: 报告章节完整性"""
    indicators = generate_random_indicators(data)
    analysis_result = generate_random_analysis_result(data)
    
    report_path = exporter.export_report(indicators, analysis_result, chart_path)
    content = read_file(report_path)
    
    required_sections = [
        "核心指标概览", "情绪趋势图", "周期节点识别",
        "背离分析", "细节盘点", "操作策略建议", "下一节点预判"
    ]
    assert all(section in content for section in required_sections)
```

### 集成测试

```python
def test_end_to_end_analysis():
    """端到端测试：从数据获取到报告生成"""
    agent = SentimentAnalysisAgent(config)
    result = agent.analyze(
        analysis_date=date(2024, 1, 15),
        output_format="md"
    )
    
    assert result.success
    assert os.path.exists(result.report_path)
    assert os.path.exists(result.chart_path)
    assert result.analysis_result is not None
```

### 测试数据生成策略

使用`hypothesis`的策略组合器生成复杂的测试数据：

```python
# 生成有效的市场数据
market_data_strategy = st.builds(
    MarketDayData,
    date=st.dates(min_value=date(2020, 1, 1), max_value=date(2024, 12, 31)),
    index_change=st.floats(min_value=-10.0, max_value=10.0),
    up_count=st.integers(min_value=0, max_value=5000),
    limit_up_count=st.integers(min_value=0, max_value=500),
    # ... 其他字段
)

# 生成情绪指标数据
sentiment_indicators_strategy = st.builds(
    SentimentIndicators,
    daily_sentiments=st.lists(
        st.builds(DailySentiment, ...),
        min_size=15,
        max_size=15
    )
)
```

### 测试覆盖目标

- 代码覆盖率：>= 80%
- 属性测试覆盖所有核心计算逻辑
- 单元测试覆盖所有边界情况和错误处理
- 集成测试覆盖主要用户场景


## LLM Prompt Engineering

### 系统提示词设计

系统提示词定义LLM的角色、能力和输出要求：

```
你是一位资深的A股短线交易专家，精通周期方法论和情绪分析。你的任务是基于三条情绪指标线（大盘系数、超短情绪、亏钱效应）识别市场周期节点，分析当前情绪状态，并提供操作策略建议。

## 周期方法论核心概念

### 周期演绎顺序
1. **冰冰点**（周期之始）：亏钱效应极高，三线同时处于低位，市场恐慌
2. **冰冰点次日修复**：市场开始修复，观察大盘或情绪谁领先
3. **修复后分歧**（第二买点）：修复后出现分歧，大盘与情绪开始分化
4. **共振高潮**：大盘系数与超短情绪同步处于高位（大涨共振）或低位（大跌共振）
5. **退潮阶段**：共振高潮后市场开始分化，出现轮动补涨
6. **冰点/冰冰点**：退潮后亏钱效应再次升高，新周期开始

### 关键信号识别

**背离信号**：
- 顶背离：大盘系数在上，超短情绪在下 → 大盘领先情绪，警惕退潮
- 底背离：大盘系数在下，超短情绪在上 → 情绪领先大盘，可能是出货信号

**共振信号**：
- 大涨共振：大盘系数与超短情绪同步上涨，市场情绪高涨
- 大跌共振：大盘系数与超短情绪同步下跌，市场恐慌

**三线耦合**：
- 三条曲线趋于粘合，波动率降低，变盘临界点

**市场失灵点**：
- 亏钱效应极高，但超短情绪不跌反升 → 破冰信号，新妖王诞生

### 顺序逻辑（核心）

**大盘领先于情绪**是市场的基本规律：
- 大盘领先上涨：指数先涨，情绪后涨 → 健康的上涨
- 大盘领先下跌：指数先跌，情绪后跌 → 阴跌转暴跌的前兆

**情绪领先大盘**是异常信号：
- 情绪领先上涨：情绪先涨，指数后涨 → 可能是短期炒作
- 情绪领先下跌：情绪先跌，指数还翻红 → 出货信号

### 极值定义

使用过去一年数据的标准差定义极值：
- 极端冰点：指标值 < 均值 - 2倍标准差
- 极端高潮：指标值 > 均值 + 2倍标准差

## 分析任务

你需要完成以下分析任务：

1. **周期节点识别**：识别10个交易日内出现的所有周期节点，标注日期和节点类型
2. **当前阶段判断**：判断最后一日所处的周期阶段和在演绎顺序中的位置
3. **赚钱效应评分**：基于超短情绪线所处历史分位点，给出0-100分的评分
4. **背离分析**：分析是否存在背离，判断大盘领先情绪还是情绪透支大盘
5. **细节盘点**：分析最高板溢价、断板反馈、涨停数、连板家数、炸板率等指标
6. **操作策略建议**：根据周期节点给出仓位建议和操作策略
7. **下一节点预判**：预判下一个可能出现的周期节点和触发条件

## 输出格式

请严格按照以下JSON格式输出：

```json
{
  "cycle_nodes": [
    {
      "date": "YYYY-MM-DD",
      "node_type": "冰冰点/修复/分歧/共振/退潮/背离/三线耦合",
      "description": "节点描述",
      "key_indicators": {
        "market_coefficient": XX.XX,
        "ultra_short_sentiment": XX.XX,
        "loss_effect": XX.XX
      },
      "confidence": "高/中/低"
    }
  ],
  "current_stage": "当前所处阶段",
  "stage_position": "在演绎顺序中的位置",
  "money_making_score": 0-100,
  "divergence_analysis": "背离分析内容",
  "detail_analysis": "细节盘点内容",
  "strategy_suggestion": "操作策略建议",
  "position_advice": "轻仓/半仓/重仓/空仓",
  "risk_warning": "风险提示",
  "next_node_prediction": "下一节点预判"
}
```
```

### 用户提示词设计

用户提示词提供具体的数据和分析要求：

```
## 市场数据

### 三线情绪指标（最近15个交易日）

| 交易日期 | 大盘系数 | 超短情绪 | 亏钱效应 |
|----------|----------|----------|----------|
| 2024-01-08 | 150.5 | 85.3 | 45.2 |
| 2024-01-09 | 148.2 | 82.1 | 48.9 |
| ... | ... | ... | ... |
| 2024-01-25 | 165.8 | 95.2 | 38.5 |
| 2024-01-26 | 168.3 | 98.1 | 35.2 |

**最新一日与昨日环比**：
- 大盘系数：168.3（昨日165.8，环比+1.51%）
- 超短情绪：98.1（昨日95.2，环比+3.05%）
- 亏钱效应：35.2（昨日38.5，环比-8.57%）

### 市场细节数据（最后一日：2024-01-26）

- **指数涨幅**: +1.25%
- **全A涨幅**: +1.18%
- **上涨家数**: 3316
- **下跌家数**: 1684
- **涨停数**: 52
- **连板家数**: 2连板15家，3连板8家，4连板3家，5连板1家
- **最高板**: 5连板
- **昨日涨停今日表现**: 平均+2.3%
- **新增百日新高个股**: 28家
- **跌停数**: 8家
- **炸板率**: 15.2%
- **大幅回撤家数**: 45家
- **昨日断板今日表现**: 平均-1.2%

## 分析要求

请基于以上15个交易日的数据，完成周期节点识别、当前阶段判断、情绪分析和策略建议。

特别关注：
1. 三线的相对位置关系（是否背离、共振、耦合）
2. 三线的趋势变化（上升、下降、震荡）
3. 大盘与情绪的领先滞后关系
4. 是否出现极值信号（极端冰点或极端高潮）
5. 是否出现市场失灵点（破冰信号）
6. 最新一日与昨日的环比变化及其意义
```

### Few-Shot示例

提供1-2个高质量的分析示例，展示期望的分析深度和格式：

```json
{
  "input": {
    "sentiment_data": [
      {"trading_date": "2024-01-10", "market_coefficient": 142.3, "ultra_short_sentiment": 78.5, "loss_effect": 85.2},
      {"trading_date": "2024-01-11", "market_coefficient": 155.8, "ultra_short_sentiment": 82.1, "loss_effect": 72.3},
      {"trading_date": "2024-01-12", "market_coefficient": 158.2, "ultra_short_sentiment": 85.6, "loss_effect": 68.5},
      {"trading_date": "2024-01-15", "market_coefficient": 162.5, "ultra_short_sentiment": 88.3, "loss_effect": 62.1},
      {"trading_date": "2024-01-16", "market_coefficient": 165.8, "ultra_short_sentiment": 92.5, "loss_effect": 58.3},
      {"trading_date": "2024-01-17", "market_coefficient": 168.2, "ultra_short_sentiment": 95.2, "loss_effect": 55.8},
      {"trading_date": "2024-01-18", "market_coefficient": 172.5, "ultra_short_sentiment": 98.6, "loss_effect": 52.3},
      {"trading_date": "2024-01-19", "market_coefficient": 175.8, "ultra_short_sentiment": 102.3, "loss_effect": 48.5},
      {"trading_date": "2024-01-22", "market_coefficient": 178.5, "ultra_short_sentiment": 105.8, "loss_effect": 45.2},
      {"trading_date": "2024-01-23", "market_coefficient": 182.3, "ultra_short_sentiment": 110.2, "loss_effect": 42.8},
      {"trading_date": "2024-01-24", "market_coefficient": 185.6, "ultra_short_sentiment": 115.3, "loss_effect": 40.5},
      {"trading_date": "2024-01-25", "market_coefficient": 188.2, "ultra_short_sentiment": 118.5, "loss_effect": 38.2},
      {"trading_date": "2024-01-26", "market_coefficient": 190.5, "ultra_short_sentiment": 122.8, "loss_effect": 36.5},
      {"trading_date": "2024-01-29", "market_coefficient": 192.8, "ultra_short_sentiment": 125.2, "loss_effect": 35.8},
      {"trading_date": "2024-01-30", "market_coefficient": 195.2, "ultra_short_sentiment": 128.5, "loss_effect": 34.2}
    ],
    "latest_vs_yesterday": {
      "market_coefficient": {"latest": 195.2, "yesterday": 192.8, "change_pct": 1.24},
      "ultra_short_sentiment": {"latest": 128.5, "yesterday": 125.2, "change_pct": 2.64},
      "loss_effect": {"latest": 34.2, "yesterday": 35.8, "change_pct": -4.47}
    },
    "market_details": {
      "trading_date": "2024-01-30",
      "index_change": 1.35,
      "limit_up_count": 65,
      "max_consecutive": 6,
      "blown_limit_up_rate": 12.5
    }
  },
  "output": {
    "cycle_nodes": [
      {
        "trading_date": "2024-01-10",
        "node_type": "冰冰点",
        "description": "亏钱效应达到85.2，显著高于大盘系数（142.3）和超短情绪（78.5），三线同时处于低位，市场恐慌情绪浓厚",
        "key_indicators": {
          "market_coefficient": 142.3,
          "ultra_short_sentiment": 78.5,
          "loss_effect": 85.2
        },
        "confidence": "高"
      },
      {
        "trading_date": "2024-01-11",
        "node_type": "冰冰点次日修复",
        "description": "大盘系数率先反弹至155.8，超短情绪跟随至82.1，亏钱效应回落至72.3，大盘领先修复",
        "key_indicators": {
          "market_coefficient": 155.8,
          "ultra_short_sentiment": 82.1,
          "loss_effect": 72.3
        },
        "confidence": "高"
      },
      {
        "trading_date": "2024-01-18",
        "node_type": "修复后分歧",
        "description": "大盘系数与超短情绪开始分化，大盘系数172.5，超短情绪98.6，出现第二买点特征",
        "key_indicators": {
          "market_coefficient": 172.5,
          "ultra_short_sentiment": 98.6,
          "loss_effect": 52.3
        },
        "confidence": "中"
      }
    ],
    "current_stage": "共振高潮前期",
    "stage_position": "周期演绎顺序第4阶段，大盘系数与超短情绪同步上涨，进入共振阶段",
    "money_making_score": 85,
    "divergence_analysis": "当前大盘系数（195.2）与超短情绪（128.5）保持同步上涨，未出现明显背离。从环比数据看，大盘系数环比+1.24%，超短情绪环比+2.64%，情绪略强于大盘，但仍属于健康的共振状态。亏钱效应持续下降至34.2（环比-4.47%），说明市场赚钱效应良好。",
    "detail_analysis": "最高板为6连板，连板梯队完整，说明市场情绪高涨。昨日涨停今日平均表现良好，溢价充足。炸板率仅12.5%，处于低位，说明市场分歧较小，一致性强。新增百日新高个股数量增加，说明市场广度良好。从环比数据看，三线指标均向好，特别是超短情绪环比+2.64%，显示市场情绪加速升温。",
    "strategy_suggestion": "当前处于共振高潮前期，市场情绪高涨，赚钱效应良好。建议重仓参与，重点关注连板股和新高股。但需警惕共振高潮后的退潮风险，一旦出现大盘与情绪背离，或炸板率快速上升，应及时减仓。",
    "position_advice": "重仓",
    "risk_warning": "1. 共振高潮后可能快速进入退潮阶段；2. 连板高度已达6板，需警惕高位风险；3. 市场情绪过热，注意控制仓位和止盈",
    "next_node_prediction": "如果大盘系数与超短情绪继续同步上涨，将进入共振高潮阶段。关键触发条件：超短情绪突破130，大盘系数突破200。如果出现大盘上涨但情绪回落，或炸板率快速上升，则可能直接进入退潮阶段。"
  }
}
```

### 提示词优化策略

1. **迭代优化**：根据LLM输出质量不断调整提示词
2. **A/B测试**：测试不同提示词版本的效果
3. **温度调节**：使用较低的temperature（0.3-0.5）确保输出稳定
4. **输出约束**：明确要求JSON格式，避免额外的解释文本


## Implementation Notes

### 与现有系统集成

情绪分析系统将复用现有大盘分析Agent的基础设施：

1. **LLM客户端复用**：
   ```python
   from src.llm.client import LLMClient, create_client
   from src.llm.base import LLMConfig
   
   # 使用相同的LLM配置
   llm_client = create_client(
       api_key=config.api_key,
       model=config.model,
       provider=config.provider
   )
   ```

2. **配置加载复用**：
   ```python
   from src.llm.config_loader import load_config
   
   # 扩展配置文件，添加sentiment部分
   config = load_config("config.yaml")
   sentiment_config = config.get("sentiment", {})
   ```

3. **数据源选择**：
   ```python
   # 推荐：使用开盘啦数据源
   from src.data.kaipanla_sentiment_source import KaipanlaSentimentSource
   
   source = KaipanlaSentimentSource(
       max_retries=5,
       timeout=60
   )
   
   # 备选：使用AKShare数据源
   from src.data.akshare_sentiment_source import AKShareSentimentSource
   
   source = AKShareSentimentSource(
       max_retries=3,
       timeout=30
   )
   ```

4. **数据源工厂模式**：
   ```python
   def create_sentiment_source(provider: str = "kaipanla", **kwargs):
       """创建数据源的工厂函数"""
       if provider == "kaipanla":
           return KaipanlaSentimentSource(**kwargs)
       elif provider == "akshare":
           return AKShareSentimentSource(**kwargs)
       elif provider == "tushare":
           return TuShareSentimentSource(**kwargs)
       else:
           raise ValueError(f"Unknown provider: {provider}")
   ```

### 目录结构

```
sentiment_replay_agent/
├── src/
│   ├── sentiment/              # 新增：情绪分析模块
│   │   ├── __init__.py
│   │   ├── agent.py            # SentimentAnalysisAgent
│   │   ├── calculator.py       # SentimentCalculator
│   │   ├── data_fetcher.py     # SentimentDataFetcher（已弃用）
│   │   ├── llm_analyzer.py     # SentimentLLMAnalyzer
│   │   ├── chart_generator.py  # SentimentChartGenerator
│   │   └── report_exporter.py  # SentimentReportExporter
│   ├── data/                   # 数据源模块
│   │   ├── __init__.py
│   │   ├── kaipanla_sentiment_source.py  # ✅ 开盘啦数据源（推荐）
│   │   ├── akshare_sentiment_source.py   # AKShare数据源（备选）
│   │   ├── tushare_source.py             # TuShare数据源（备选）
│   │   └── cache_manager.py              # 数据缓存管理
│   ├── sentiment_cli.py        # 新增：情绪分析CLI
│   └── ...                     # 现有模块
├── prompts/
│   └── sentiment/              # 新增：情绪分析提示词
│       ├── system.txt
│       ├── analysis.txt
│       └── examples/
│           └── sentiment_example.json
├── tests/
│   ├── sentiment/              # 新增：情绪分析测试
│   │   ├── test_calculator.py
│   │   ├── test_calculator_properties.py
│   │   ├── test_data_fetcher.py
│   │   ├── test_llm_analyzer.py
│   │   └── test_report_exporter.py
│   └── ...
├── examples/                   # 新增：使用示例
│   └── example_kaipanla_source.py
├── output/
│   └── sentiment/              # 新增：情绪分析输出
│       ├── reports/
│       └── charts/
├── test_kaipanla_source.py     # 新增：数据源测试脚本
├── export_data_to_csv.py       # 新增：数据导出工具
├── KAIPANLA_INTEGRATION.md     # 新增：开盘啦集成说明
├── QUICKSTART_KAIPANLA.md      # 新增：快速开始指南
├── 网络超时说明.md              # 新增：网络问题说明
└── config.yaml                 # 扩展配置
```

**新增文件说明**：

1. **kaipanla_sentiment_source.py**: 开盘啦数据源实现
   - 使用kaipanla_crawler获取数据
   - 提供更准确的炸板率、百日新高等数据
   - 包含最高板个股信息

2. **export_data_to_csv.py**: 数据导出工具
   - 导出原始市场数据为CSV
   - 导出计算的情绪指标为CSV
   - 导出合并数据为CSV
   - 用于数据验证和分析

3. **test_kaipanla_source.py**: 数据源测试脚本
   - 测试单日数据获取
   - 测试多日数据获取
   - 测试数据验证功能

4. **example_kaipanla_source.py**: 使用示例
   - 5个完整的使用示例
   - 涵盖基本使用、数据分析、连板梯队分析等

5. **KAIPANLA_INTEGRATION.md**: 集成说明文档
   - 详细的功能说明和对比
   - 完整的使用方法
   - 故障排查指南

6. **QUICKSTART_KAIPANLA.md**: 快速开始指南
   - 5分钟快速测试指南
   - 常见问题解答
   - 完整示例代码

7. **网络超时说明.md**: 网络问题说明
   - 解释超时是正常现象
   - 提供优化建议
   - 故障排查方法

### 配置文件扩展

在`config.yaml`中添加情绪分析配置：

```yaml
# 现有配置
llm:
  provider: zhipu
  model: glm-4.6
  api_key: "..."

akshare:
  index_code: "000001"
  index_name: "sh000001"

# 新增：情绪分析配置
sentiment:
  # 数据源配置
  data_source:
    provider: kaipanla  # kaipanla（推荐） / akshare / tushare
    timeout: 6000  # 超时时间（秒），开盘啦建议60秒
    max_retries: 5  # 最大重试次数，开盘啦建议5次
  
  # 分析参数
  num_trading_days: 15  # 分析的交易日数量（默认15）
  
  # 输出配置
  output:
    dir: "output/sentiment/"
    default_format: "md"  # md / pdf / all
    chart_format: "png"   # png / svg
  
  # 提示词配置
  prompts:
    template_dir: "prompts/sentiment/"
    temperature: 0.3
    max_tokens: 4096

# 数据源说明：
# - kaipanla: 使用开盘啦APP数据（推荐）
#   优势：数据准确率99%+，炸板率、百日新高等为真实值
#   特点：包含最高板个股信息、昨日断板今表现等详细数据
#   要求：需要kaipanla_crawler模块
# - akshare: 使用AKShare免费API
#   优势：免费，无需API密钥
#   缺点：部分指标为估算值，准确性不如开盘啦
# - tushare: 使用TuShare API（需要积分）
#   优势：数据全面
#   缺点：需要API密钥和积分
```

### 依赖管理

在`pyproject.toml`中添加新的依赖：

```toml
[project]
dependencies = [
    # 现有依赖
    "zhipuai>=2.0.0",
    "openai>=1.0.0",
    "pandas>=2.0.0",
    "matplotlib>=3.7.0",
    "mplfinance>=0.12.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "akshare>=1.12.0",
    
    # 新增依赖
    "hypothesis>=6.0.0",  # 属性测试
    "reportlab>=4.0.0",   # PDF生成
]
```

### 性能优化

1. **数据缓存**：
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def fetch_market_data(end_date: date, num_days: int):
       # 缓存已获取的数据，避免重复API调用
       pass
   ```

2. **并行处理**：
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   # 并行获取多个交易日的数据
   with ThreadPoolExecutor(max_workers=5) as executor:
       futures = [executor.submit(fetch_day_data, date) for date in dates]
       results = [f.result() for f in futures]
   ```

3. **增量计算**：
   ```python
   # 只计算新增交易日的指标，复用历史计算结果
   def calculate_incremental(previous_indicators, new_day_data):
       pass
   ```

### 扩展性设计

1. **数据源插件化**：
   ```python
   class DataSourcePlugin(ABC):
       @abstractmethod
       def fetch_data(self, end_date, num_days) -> List[MarketDayData]:
           pass
   
   # 注册新的数据源
   register_data_source("custom_source", CustomDataSource)
   ```

2. **LLM提供商扩展**：
   ```python
   # 复用现有的LLM客户端架构，支持任何OpenAI兼容的API
   ```

3. **报告格式扩展**：
   ```python
   class ReportFormatter(ABC):
       @abstractmethod
       def format(self, data) -> str:
           pass
   
   # 注册新的报告格式
   register_formatter("html", HTMLFormatter)
   register_formatter("json", JSONFormatter)
   ```

### 开发优先级

**Phase 1: 核心功能**（MVP）
1. 数据获取模块（SentimentDataFetcher）
2. 指标计算模块（SentimentCalculator）
3. LLM分析模块（SentimentLLMAnalyzer）
4. 基础报告导出（Markdown格式）
5. CLI接口

**Phase 2: 可视化**
1. 图表生成模块（SentimentChartGenerator）
2. 报告中嵌入图表
3. 改进报告排版

**Phase 3: 增强功能**
1. PDF导出
2. 历史数据分析
3. 性能优化（缓存、并行）
4. 与大盘分析Agent联合报告

**Phase 4: 高级功能**
1. 实时监控模式
2. 自定义指标公式
3. 策略回测
4. Web界面

