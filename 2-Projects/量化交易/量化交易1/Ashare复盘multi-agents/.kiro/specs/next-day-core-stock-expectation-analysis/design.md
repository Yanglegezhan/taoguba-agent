# 设计文档

## 概述

本系统是一个A股次日核心个股超预期分析的智能体系统，通过三个独立运作的Agent协作，实现从数据沉淀、策略校准到竞价监测的全流程自动化分析。系统的核心目标是在9:25竞价结束后，生成可执行的操作指南，帮助交易者快速决策。

### 系统特点

- **三阶段流水线**：Stage1（数据沉淀与复盘）→ Stage2（早盘策略校准）→ Stage3（竞价轨迹监测）
- **Agent独立运作**：每个Agent可独立启动、运行和失败，通过文件系统传递数据
- **双池设计**：基因池（预设核心股）+ 附加池（竞价异动股）
- **决策导航引擎**：将分析结果转化为可执行的操作剧本和场景决策树
- **LLM增强**：使用Gemini-2.0-Flash进行智能分析和判断

### 技术栈

- **编程语言**：Python 3.9+
- **LLM模型**：Gemini-2.0-Flash
- **数据源**：Kaipanla API（主）、AKShare（补充，需代理）、东方财富API（补充）
- **数据存储**：JSON文件 + SQLite数据库
- **配置管理**：YAML配置文件

## 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         数据源层                                  │
├─────────────────────────────────────────────────────────────────┤
│  Kaipanla API  │  AKShare API  │  Eastmoney API  │  News API    │
└────────┬────────────────┬────────────────┬────────────────┬──────┘
         │                │                │                │
         └────────────────┴────────────────┴────────────────┘
                              │
         ┌────────────────────┴────────────────────┐
         │         数据采集与清洗模块                │
         └────────────────────┬────────────────────┘
                              │
         ┌────────────────────┴────────────────────┐
         │            数据存储层                     │
         │  (JSON Files + SQLite Database)         │
         └────────────────────┬────────────────────┘
                              │
    ┌─────────────────────────┼─────────────────────────┐
    │                         │                         │
┌───▼────┐              ┌────▼─────┐            ┌─────▼────┐
│Stage1  │              │ Stage2   │            │ Stage3   │
│Agent   │─────────────▶│ Agent    │───────────▶│ Agent    │
│        │  Gene_Pool   │          │ Baseline   │          │
│数据复盘 │  Reports     │策略校准   │ Expectation│竞价监测   │
└───┬────┘              └────┬─────┘            └─────┬────┘
    │                        │                        │
    │                        │                        │
    └────────────────────────┴────────────────────────┘
                              │
         ┌────────────────────┴────────────────────┐
         │        决策导航推演引擎                    │
         └────────────────────┬────────────────────┘
                              │
         ┌────────────────────┴────────────────────┐
         │          报告生成与推送模块                │
         └────────────────────┬────────────────────┘
                              │
                         用户界面
```

### Agent架构设计

每个Agent采用相同的架构模式：

```
┌─────────────────────────────────────────┐
│              Agent Core                 │
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────┐   │
│  │   Configuration Manager         │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │   Data Input Handler            │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │   LLM Integration Layer         │   │
│  │   (Gemini-2.0-Flash)            │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │   Business Logic Processor      │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │   Data Output Handler           │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │   Error Handler & Logger        │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## 组件与接口

### Stage1 Agent - 数据沉淀与复盘

**职责**：
- 读取当日收盘行情数据
- 调用现有的复盘Agents生成三份报告
- 构建和更新基因池
- 计算个股技术位

**输入**：
- 当日完整行情数据（从Kaipanla/AKShare获取）
- 历史基因池数据（JSON文件）

**输出**：
- `market_report_{date}.json` - 大盘分析报告
- `emotion_report_{date}.json` - 情绪分析报告
- `theme_report_{date}.json` - 题材分析报告
- `gene_pool_{date}.json` - 更新后的基因池

**核心模块**：

1. **ReportGenerator**
   ```python
   class ReportGenerator:
       def generate_market_report(self, market_data: MarketData) -> MarketReport
       def generate_emotion_report(self, market_data: MarketData) -> EmotionReport
       def generate_theme_report(self, market_data: MarketData) -> ThemeReport
   ```

2. **GenePoolBuilder**
   ```python
   class GenePoolBuilder:
       def scan_continuous_limit_up(self, market_data: MarketData) -> List[Stock]
       def identify_failed_limit_up(self, market_data: MarketData) -> List[Stock]
       def identify_recognition_stocks(self, market_data: MarketData) -> List[Stock]
       def identify_trend_stocks(self, market_data: MarketData) -> List[Stock]
       def build_gene_pool(self, stocks: List[Stock]) -> GenePool
   ```

3. **TechnicalCalculator**
   ```python
   class TechnicalCalculator:
       def calculate_moving_averages(self, stock: Stock) -> MovingAverages
       def identify_previous_highs(self, stock: Stock) -> List[PriceLevel]
       def calculate_chip_concentration(self, stock: Stock) -> ChipZone
   ```

### Stage2 Agent - 早盘策略校准

**职责**：
- 获取隔夜外部变量（美股、期货、新闻）
- 为基因池个股生成基准预期
- 捕捉突发新题材

**输入**：
- `gene_pool_{date}.json` - 昨日基因池
- `market_report_{date}.json` - 昨日大盘报告
- `emotion_report_{date}.json` - 昨日情绪报告
- `theme_report_{date}.json` - 昨日题材报告
- 隔夜外部数据（实时获取）

**输出**：
- `overnight_variables_{date}.json` - 隔夜外部变量
- `baseline_expectation_{date}.json` - 基准预期表
- `new_themes_{date}.json` - 新题材列表

**核心模块**：

1. **OvernightDataCollector**
   ```python
   class OvernightDataCollector:
       def fetch_us_stock_data(self) -> USStockData
       def fetch_futures_data(self) -> FuturesData
       def fetch_news_headlines(self) -> List[NewsItem]
       def fetch_policy_announcements(self) -> List[PolicyItem]
   ```

2. **BaselineExpectationEngine**
   ```python
   class BaselineExpectationEngine:
       def calculate_baseline(
           self, 
           stock: Stock, 
           market_context: MarketContext,
           overnight_vars: OvernightVariables
       ) -> BaselineExpectation
       
       def adjust_for_theme_status(
           self, 
           baseline: BaselineExpectation,
           theme_status: ThemeStatus
       ) -> BaselineExpectation
   ```

3. **NewThemeDetector**
   ```python
   class NewThemeDetector:
       def detect_new_themes(self, news: List[NewsItem]) -> List[Theme]
       def find_related_stocks(self, theme: Theme) -> List[Stock]
   ```

### Stage3 Agent - 竞价轨迹监测

**职责**：
- 监测竞价撤单行为（9:15-9:20）
- 监测真实博弈期（9:20-9:25）
- 获取竞价最终快照（9:25）
- 计算超预期分值
- 构建附加票池
- 生成决策导航报告

**输入**：
- `gene_pool_{date}.json` - 基因池
- `baseline_expectation_{date}.json` - 基准预期
- 竞价实时数据（从Kaipanla/AKShare获取）

**输出**：
- `auction_monitoring_{date}.json` - 竞价监测结果
- `additional_pool_{date}.json` - 附加票池
- `decision_navigation_{date}.json` - 决策导航报告
- `daily_report_{date}.html` - 每日监控报告

**核心模块**：

1. **AuctionMonitor**
   ```python
   class AuctionMonitor:
       def monitor_withdrawal_behavior(
           self, 
           stocks: List[Stock],
           time_range: TimeRange
       ) -> Dict[str, WithdrawalBehavior]
       
       def monitor_price_trajectory(
           self,
           stocks: List[Stock],
           time_range: TimeRange
       ) -> Dict[str, PriceTrajectory]
       
       def get_final_snapshot(
           self,
           stocks: List[Stock]
       ) -> Dict[str, AuctionSnapshot]
   ```

2. **ExpectationScoreCalculator**
   ```python
   class ExpectationScoreCalculator:
       def calculate_volume_score(
           self,
           auction_data: AuctionData,
           yesterday_data: StockData
       ) -> float
       
       def calculate_price_score(
           self,
           actual_price: float,
           baseline: BaselineExpectation
       ) -> float
       
       def calculate_independence_score(
           self,
           stock_change: float,
           index_change: float
       ) -> float
       
       def calculate_total_score(
           self,
           volume_score: float,
           price_score: float,
           independence_score: float,
           weights: ScoreWeights
       ) -> ExpectationScore
   ```

3. **AdditionalPoolBuilder**
   ```python
   class AdditionalPoolBuilder:
       def scan_top_seals(self, market_data: MarketData) -> List[Stock]
       def scan_rush_positioning(self, market_data: MarketData) -> List[Stock]
       def scan_energy_burst(self, market_data: MarketData) -> List[Stock]
       def scan_reverse_nuclear(self, market_data: MarketData) -> List[Stock]
       def scan_sector_formation(self, market_data: MarketData) -> List[Stock]
   ```

4. **StatusJudgmentEngine**
   ```python
   class StatusJudgmentEngine:
       def calculate_theme_recognition_score(self, stock: Stock) -> float
       def calculate_urgency_score(self, stock: Stock) -> float
       def calculate_emotion_hedge_score(self, stock: Stock) -> float
       def calculate_status_score(self, stock: Stock) -> StatusScore
       def filter_top_candidates(
           self,
           candidates: List[Stock],
           top_n: int = 5
       ) -> List[Stock]
   ```

5. **DecisionNavigationEngine**
   ```python
   class DecisionNavigationEngine:
       def generate_baseline_table(
           self,
           gene_pool: GenePool,
           expectations: Dict[str, BaselineExpectation]
       ) -> BaselineTable
       
       def generate_signal_playbooks(
           self,
           additional_pool: AdditionalPool
       ) -> List[SignalPlaybook]
       
       def generate_decision_tree(
           self,
           market_context: MarketContext,
           gene_pool: GenePool,
           additional_pool: AdditionalPool
       ) -> DecisionTree
       
       def generate_navigation_report(
           self,
           baseline_table: BaselineTable,
           playbooks: List[SignalPlaybook],
           decision_tree: DecisionTree
       ) -> NavigationReport
   ```

## 数据模型

### 核心数据结构

#### Stock（个股）
```python
@dataclass
class Stock:
    code: str                    # 股票代码
    name: str                    # 股票名称
    market_cap: float            # 流通市值（亿元）
    price: float                 # 当前价格
    change_pct: float            # 涨跌幅
    volume: float                # 成交量
    amount: float                # 成交额（万元）
    turnover_rate: float         # 换手率
    board_height: int            # 连板高度
    themes: List[str]            # 所属题材
    technical_levels: TechnicalLevels  # 技术位
```

#### TechnicalLevels（技术位）
```python
@dataclass
class TechnicalLevels:
    ma5: float                   # 5日均线
    ma10: float                  # 10日均线
    ma20: float                  # 20日均线
    previous_high: float         # 前期高点
    chip_zone_low: float         # 筹码密集区下沿
    chip_zone_high: float        # 筹码密集区上沿
    distance_to_ma5_pct: float   # 距离5日均线百分比
    distance_to_high_pct: float  # 距离前高百分比
```

#### GenePool（基因库）
```python
@dataclass
class GenePool:
    date: str                    # 日期
    continuous_limit_up: List[Stock]  # 连板梯队
    failed_limit_up: List[Stock]      # 炸板股
    recognition_stocks: List[Stock]   # 辨识度个股
    trend_stocks: List[Stock]         # 趋势股
    all_stocks: Dict[str, Stock]      # 所有个股字典
```

#### BaselineExpectation（基准预期）
```python
@dataclass
class BaselineExpectation:
    stock_code: str              # 股票代码
    expected_open_min: float     # 预期开盘涨幅下限（%）
    expected_open_max: float     # 预期开盘涨幅上限（%）
    expected_amount_min: float   # 预期竞价金额下限（万元）
    logic: str                   # 计算逻辑说明
    confidence: float            # 置信度（0-1）
```

#### AuctionData（竞价数据）
```python
@dataclass
class AuctionData:
    stock_code: str              # 股票代码
    auction_low_price: float     # 竞价最低价
    auction_high_price: float    # 竞价最高价
    open_price: float            # 开盘价
    auction_volume: float        # 竞价成交量
    auction_amount: float        # 竞价成交额（万元）
    seal_amount: float           # 封单金额（万元，涨停时）
    withdrawal_detected: bool    # 是否检测到撤单
    trajectory_rating: str       # 轨迹评级（强/中/弱）
```

#### ExpectationScore（超预期分值）
```python
@dataclass
class ExpectationScore:
    stock_code: str              # 股票代码
    volume_score: float          # 量能分值（0-100）
    price_score: float           # 价格分值（0-100）
    independence_score: float    # 独立性分值（0-100）
    total_score: float           # 总分（0-100）
    rating: str                  # 评级（优秀/良好/一般/较差）
    recommendation: str          # 操作建议（打板/低吸/观望/撤退）
    confidence: float            # 置信度（0-1）
```

#### AdditionalPool（附加票池）
```python
@dataclass
class AdditionalPool:
    date: str                    # 日期
    top_seals: List[Stock]       # 顶级封单池
    rush_positioning: List[Stock]  # 急迫抢筹池
    energy_burst: List[Stock]    # 能量爆发池
    reverse_nuclear: List[Stock] # 极端反核池
    sector_formation: List[Stock]  # 板块阵型池
    final_candidates: List[Stock]  # 最终候选（经过地位判定）
```

#### StatusScore（地位分值）
```python
@dataclass
class StatusScore:
    stock_code: str              # 股票代码
    theme_recognition: float     # 题材辨识度（0-100）
    urgency: float               # 量价急迫性（0-100）
    emotion_hedge: float         # 情绪对冲力（0-100）
    total_score: float           # 总分（0-100）
    rank: int                    # 排名
```

#### SignalPlaybook（信号剧本）
```python
@dataclass
class SignalPlaybook:
    name: str                    # 剧本名称
    trigger_conditions: List[str]  # 触发条件
    status_judgment: str         # 地位判定
    strategy: str                # 应对策略
    risk_level: str              # 风险等级
    applicable_stocks: List[str]  # 适用个股代码
```

#### DecisionTree（决策树）
```python
@dataclass
class Scenario:
    name: str                    # 场景名称
    trigger_condition: str       # 触发条件
    market_sentiment: str        # 盘感描述
    strategy: str                # 具体策略
    risk_warning: str            # 风险提示
    confidence: float            # 置信度

@dataclass
class DecisionTree:
    scenarios: List[Scenario]    # 所有场景
    current_scenario: str        # 当前最可能的场景
```

#### NavigationReport（决策导航报告）
```python
@dataclass
class NavigationReport:
    date: str                    # 日期
    generation_time: str         # 生成时间
    baseline_table: Dict[str, BaselineExpectation]  # 及格线表
    signal_playbooks: List[SignalPlaybook]  # 信号剧本
    decision_tree: DecisionTree  # 决策树
    market_summary: str          # 市场概况
    key_recommendations: List[str]  # 关键建议
```

### 数据存储结构

#### 文件系统结构
```
data/
├── config/
│   ├── system_config.yaml       # 系统配置
│   ├── agent_config.yaml        # Agent配置
│   └── data_source_config.yaml  # 数据源配置
├── stage1_output/
│   ├── market_report_20250212.json
│   ├── emotion_report_20250212.json
│   ├── theme_report_20250212.json
│   └── gene_pool_20250212.json
├── stage2_output/
│   ├── overnight_variables_20250213.json
│   ├── baseline_expectation_20250213.json
│   └── new_themes_20250213.json
├── stage3_output/
│   ├── auction_monitoring_20250213.json
│   ├── additional_pool_20250213.json
│   ├── decision_navigation_20250213.json
│   └── daily_report_20250213.html
├── historical/
│   └── gene_pool_history.db     # SQLite数据库
└── logs/
    ├── stage1_20250212.log
    ├── stage2_20250213.log
    └── stage3_20250213.log
```

#### 数据库Schema（SQLite）
```sql
-- 基因池历史表
CREATE TABLE gene_pool_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    stock_name TEXT,
    category TEXT,  -- continuous_limit_up, failed_limit_up, etc.
    board_height INTEGER,
    price REAL,
    change_pct REAL,
    amount REAL,
    technical_data TEXT,  -- JSON格式
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 基准预期历史表
CREATE TABLE baseline_expectation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    expected_open_min REAL,
    expected_open_max REAL,
    expected_amount_min REAL,
    logic TEXT,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 竞价监测结果表
CREATE TABLE auction_monitoring_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    open_price REAL,
    auction_amount REAL,
    expectation_score REAL,
    recommendation TEXT,
    actual_performance TEXT,  -- 用于后续回测
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 附加池历史表
CREATE TABLE additional_pool_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    pool_type TEXT,  -- top_seals, rush_positioning, etc.
    status_score REAL,
    rank INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 数据接口规范（需求23）

#### Stage1 → Stage2 数据接口

**文件**: `gene_pool_{date}.json`

**格式**:
```json
{
  "date": "2025-02-13",
  "continuous_limit_up": [
    {
      "code": "002810",
      "name": "韩建河山",
      "market_cap": 45.2,
      "price": 15.68,
      "change_pct": 10.0,
      "volume": 1250000,
      "amount": 19600,
      "turnover_rate": 4.2,
      "board_height": 5,
      "themes": ["AI", "数字经济"],
      "technical_levels": {
        "ma5": 14.2,
        "ma10": 13.1,
        "ma20": 12.5,
        "previous_high": 16.8,
        "chip_zone_low": 13.0,
        "chip_zone_high": 14.5,
        "distance_to_ma5_pct": 10.4,
        "distance_to_high_pct": -6.7
      }
    }
  ],
  "failed_limit_up": [...],
  "recognition_stocks": [...],
  "trend_stocks": [...]
}
```

#### Stage2 → Stage3 数据接口

**文件**: `baseline_expectation_{date}.json`

**格式**:
```json
{
  "date": "2025-02-13",
  "expectations": {
    "002810": {
      "stock_code": "002810",
      "stock_name": "韩建河山",
      "expected_open_min": 5.0,
      "expected_open_max": 8.0,
      "expected_amount_min": 15000,
      "logic": "5连板+题材主升期+隔夜美股科技股上涨",
      "confidence": 0.85
    }
  }
}
```

#### Stage3 输出接口

**文件**: `decision_navigation_{date}.json`

**格式**:
```json
{
  "date": "2025-02-13",
  "generation_time": "2025-02-13 09:26:30",
  "baseline_table": {
    "002810": {
      "stock_code": "002810",
      "stock_name": "韩建河山",
      "expected_open_min": 5.0,
      "expected_open_max": 8.0,
      "actual_open": 6.5,
      "status": "符合预期",
      "recommendation": "可持有或追高"
    }
  },
  "signal_playbooks": [
    {
      "name": "暴力抢筹卡位流",
      "trigger_conditions": [
        "(开盘价 - 竞价最低价) > 3%",
        "竞价量比 > 50"
      ],
      "applicable_stocks": ["300XXX"],
      "strategy": "若核心大哥正常，则轻仓跟随；若核心大哥低开，则重仓首选"
    }
  ],
  "decision_tree": {
    "scenarios": [
      {
        "name": "整体超预期",
        "trigger_condition": "核心大哥全封一字",
        "market_sentiment": "资金极度亢奋",
        "strategy": "扫板附加池X中最先涨停的那只",
        "risk_warning": "顶背离风险，注意及时止盈",
        "confidence": 0.7
      }
    ],
    "current_scenario": "整体超预期"
  },
  "market_summary": "大盘高开0.8%，涨停家数45家，市场情绪强势",
  "key_recommendations": [
    "韩建河山符合预期，可持有",
    "附加池中300XXX触发暴力抢筹信号，建议关注"
  ]
}
```


## 错误处理

### 数据源错误处理

#### 主数据源失败
```python
class DataSourceManager:
    def fetch_data_with_fallback(self, data_type: str) -> Any:
        """
        优先级: Kaipanla -> AKShare -> Eastmoney
        """
        try:
            return self.kaipanla_client.fetch(data_type)
        except Exception as e:
            logger.warning(f"Kaipanla failed: {e}, trying AKShare")
            try:
                return self.akshare_client.fetch(data_type)
            except Exception as e2:
                logger.warning(f"AKShare failed: {e2}, trying Eastmoney")
                return self.eastmoney_client.fetch(data_type)
```

#### 代理配置错误
- AKShare需要代理时，系统应在启动时验证代理配置
- 代理失败时，记录详细错误信息并提示用户检查配置
- 提供代理测试工具

#### 数据缺失处理
- 当某个字段缺失时，使用默认值或跳过该个股
- 记录缺失字段的统计信息
- 在报告中标注数据质量问题

### LLM调用错误处理

#### 重试机制
```python
class LLMClient:
    def call_with_retry(
        self,
        prompt: str,
        max_retries: int = 3,
        timeout: int = 30
    ) -> str:
        for attempt in range(max_retries):
            try:
                response = self.gemini_client.generate(
                    prompt,
                    timeout=timeout
                )
                return response
            except TimeoutError:
                logger.warning(f"LLM timeout, attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                logger.error(f"LLM error: {e}, attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    # 降级到规则引擎
                    return self.rule_based_fallback(prompt)
```

#### 降级方案
- 当LLM不可用时，使用规则引擎进行基础分析
- 规则引擎基于历史统计和固定阈值
- 在报告中标注"使用降级方案"

### Agent失败处理

#### Stage1失败
- Stage2和Stage3使用前一日的数据
- 在报告中标注"使用历史数据"
- 发送告警通知

#### Stage2失败
- Stage3使用默认基准预期（基于历史平均值）
- 在报告中标注"使用默认预期"

#### Stage3失败
- 记录错误日志
- 发送紧急告警
- 尝试使用简化版本生成基础报告

### 数据验证

#### 输入数据验证
```python
class DataValidator:
    def validate_market_data(self, data: MarketData) -> ValidationResult:
        """验证市场数据的完整性和合理性"""
        errors = []
        
        # 检查必需字段
        if not data.date:
            errors.append("Missing date field")
        
        # 检查数值合理性
        for stock in data.stocks:
            if stock.change_pct > 20 or stock.change_pct < -20:
                errors.append(f"Abnormal change_pct for {stock.code}")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
```

#### 输出数据验证
- 验证JSON格式是否符合Schema
- 验证数值范围是否合理
- 验证必需字段是否存在

### 异常情况处理

#### 停牌/复牌
- 自动排除停牌股
- 复牌首日单独标注，不参与常规分析

#### 重大公告
- 检测公告关键词（重组、业绩预告等）
- 标注为"事件驱动"
- 单独分析，不与常规个股混合

#### 极端市场
- 当涨停/跌停家数超过阈值时，标记为"极端市场"
- 调整基准预期的计算逻辑
- 在报告中突出显示市场状态

## 测试策略

### 单元测试

测试框架：pytest

#### 数据采集模块测试
```python
def test_kaipanla_data_fetch():
    """测试Kaipanla数据获取"""
    collector = KaipanlaCollector()
    data = collector.fetch_market_data("2025-02-12")
    assert data is not None
    assert len(data.stocks) > 0

def test_data_fallback():
    """测试数据源降级"""
    manager = DataSourceManager()
    # Mock Kaipanla失败
    with patch.object(manager.kaipanla_client, 'fetch', side_effect=Exception):
        data = manager.fetch_data_with_fallback("market_data")
        assert data is not None  # 应该从AKShare获取
```

#### 计算模块测试
```python
def test_moving_average_calculation():
    """测试均线计算"""
    calculator = TechnicalCalculator()
    prices = [10, 11, 12, 13, 14]
    ma5 = calculator.calculate_ma(prices, period=5)
    assert ma5 == 12.0

def test_expectation_score_calculation():
    """测试超预期分值计算"""
    calculator = ExpectationScoreCalculator()
    score = calculator.calculate_total_score(
        volume_score=80,
        price_score=70,
        independence_score=60,
        weights=ScoreWeights(0.4, 0.4, 0.2)
    )
    assert 0 <= score <= 100
```

#### 边界条件测试
```python
def test_empty_gene_pool():
    """测试空基因池"""
    builder = GenePoolBuilder()
    pool = builder.build_gene_pool([])
    assert pool.all_stocks == {}

def test_extreme_change_pct():
    """测试极端涨跌幅"""
    validator = DataValidator()
    stock = Stock(code="000001", change_pct=25.0)
    result = validator.validate_stock(stock)
    assert not result.is_valid
```

### 集成测试

#### Agent端到端测试
```python
def test_stage1_agent_e2e():
    """测试Stage1 Agent完整流程"""
    agent = Stage1Agent()
    result = agent.run(date="2025-02-12")
    
    # 验证输出文件存在
    assert os.path.exists("data/stage1_output/gene_pool_20250212.json")
    assert os.path.exists("data/stage1_output/market_report_20250212.json")
    
    # 验证数据格式
    with open("data/stage1_output/gene_pool_20250212.json") as f:
        data = json.load(f)
        assert "date" in data
        assert "continuous_limit_up" in data
```

#### Agent协作测试
```python
def test_agent_pipeline():
    """测试三个Agent的协作流程"""
    # Stage1
    stage1 = Stage1Agent()
    stage1.run(date="2025-02-12")
    
    # Stage2
    stage2 = Stage2Agent()
    stage2.run(date="2025-02-13")
    
    # Stage3
    stage3 = Stage3Agent()
    result = stage3.run(date="2025-02-13")
    
    # 验证最终报告
    assert result.navigation_report is not None
    assert len(result.navigation_report.key_recommendations) > 0
```

### 数据格式测试

#### JSON Schema验证
```python
def test_gene_pool_schema():
    """测试基因池数据格式"""
    with open("data/stage1_output/gene_pool_20250212.json") as f:
        data = json.load(f)
    
    # 使用JSON Schema验证
    schema = load_schema("gene_pool_schema.json")
    validate(instance=data, schema=schema)

def test_baseline_expectation_schema():
    """测试基准预期数据格式"""
    with open("data/stage2_output/baseline_expectation_20250213.json") as f:
        data = json.load(f)
    
    schema = load_schema("baseline_expectation_schema.json")
    validate(instance=data, schema=schema)
```

### 性能测试

#### 响应时间测试
```python
def test_stage3_response_time():
    """测试Stage3在9:25后的响应时间"""
    import time
    
    agent = Stage3Agent()
    start_time = time.time()
    agent.run(date="2025-02-13")
    elapsed = time.time() - start_time
    
    # 应在3分钟内完成
    assert elapsed < 180
```

#### 并发测试
```python
def test_concurrent_agent_execution():
    """测试多个Agent同时运行"""
    import threading
    
    def run_stage1():
        Stage1Agent().run(date="2025-02-12")
    
    def run_stage2():
        Stage2Agent().run(date="2025-02-13")
    
    t1 = threading.Thread(target=run_stage1)
    t2 = threading.Thread(target=run_stage2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    # 验证两个Agent都成功完成
    assert os.path.exists("data/stage1_output/gene_pool_20250212.json")
    assert os.path.exists("data/stage2_output/baseline_expectation_20250213.json")
```

### LLM集成测试

#### Prompt测试
```python
def test_theme_detection_prompt():
    """测试题材识别的Prompt"""
    detector = NewThemeDetector()
    news = [
        NewsItem(title="工信部发布燃气轮机发展规划", content="...")
    ]
    
    themes = detector.detect_new_themes(news)
    assert len(themes) > 0
    assert any("燃气轮机" in theme.name for theme in themes)
```

#### LLM响应验证
```python
def test_llm_response_format():
    """测试LLM响应格式"""
    client = LLMClient()
    response = client.analyze_market_sentiment(market_data)
    
    # 验证响应包含必需字段
    assert "sentiment" in response
    assert response["sentiment"] in ["强势", "中性", "弱势"]
```

### 回测测试（简化版）

```python
def test_historical_accuracy():
    """测试历史预测准确性（简化版）"""
    # 使用历史数据运行系统
    dates = ["2025-01-20", "2025-01-21", "2025-01-22"]
    
    results = []
    for date in dates:
        # 运行完整流程
        stage1 = Stage1Agent().run(date=date)
        stage2 = Stage2Agent().run(date=next_trading_day(date))
        stage3 = Stage3Agent().run(date=next_trading_day(date))
        
        # 记录预测结果
        results.append(stage3.navigation_report)
    
    # 简单统计（详细回测在后续迭代实现）
    assert len(results) == len(dates)
```


## 正确性属性

*属性（Property）是系统在所有有效执行中都应该保持为真的特征或行为。属性是人类可读规范与机器可验证正确性保证之间的桥梁。*

### Property 1: 数据源降级一致性
*对于任何*数据获取请求，当主数据源失败时，系统应自动切换到补充数据源，并记录数据来源
**验证需求: 0.5, 0.6**

### Property 2: 代理配置自动应用
*对于任何*AKShare API调用，系统应在调用前自动配置代理设置
**验证需求: 0.3**

### Property 3: 数据格式符合Schema
*对于任何*Agent输出的数据文件（JSON格式），其结构应符合预定义的JSON Schema
**验证需求: 23.1, 23.2, 23.8, 23.9**

### Property 4: 数据持久化一致性
*对于任何*生成的报告、基因池、基准预期数据，系统应将其正确存储到指定目录，文件名包含日期标识，并可被后续Agent读取
**验证需求: 1.5, 2.6, 3.7, 17.1-17.4, 23.6**

### Property 5: 基因池完整性
*对于任何*交易日，Stage1_Agent生成的基因池应包含所有识别的个股类别（连板梯队、炸板股、辨识度个股、趋势股），且每只个股应包含完整的基础信息和技术位数据
**验证需求: 2.1-2.7, 3.1-3.7**

### Property 6: 技术指标计算正确性
*对于任何*基因池个股，计算的技术指标（均线、前高距离、筹码密集区）应基于正确的历史数据，且数值在合理范围内
**验证需求: 3.1-3.7**

### Property 7: 基准预期合理性
*对于任何*基因池个股，Stage2_Agent生成的基准预期应基于昨日表现、市场环境和外部变量，且预期区间上限应大于下限
**验证需求: 5.1-5.7**

### Property 8: 基准预期条件调整
*对于任何*昨日涨停且题材处于主升期的个股，基准预期应高于昨日炸板或题材退潮的个股
**验证需求: 5.5, 5.6**

### Property 9: 竞价数据完整性
*对于任何*监控个股，Stage3_Agent应获取完整的竞价数据（9:15-9:25），包括价格轨迹、成交量、成交额
**验证需求: 7.1, 8.1, 10.1**

### Property 10: 撤单行为识别
*对于任何*在9:15涨停但9:19价格下跌超过3%的个股，系统应标记为"诱多嫌疑"
**验证需求: 7.3**

### Property 11: 超预期分值范围
*对于任何*监控个股，计算的超预期分值（量能、价格、独立性、总分）应在0-100范围内
**验证需求: 11.5, 12.6, 13.5, 14.4**

### Property 12: 超预期分值单调性
*对于任何*两只个股A和B，如果A的量能、价格、独立性分值都高于或等于B，则A的总分应高于或等于B
**验证需求: 14.1-14.5**

### Property 13: 附加池筛选条件
*对于任何*进入附加池的个股，其应满足对应维度的筛选条件（顶级封单、急迫抢筹、能量爆发、极端反核、板块阵型）
**验证需求: 15A.5, 15B.4, 15C.5, 15D.5, 15E.3**

### Property 14: 地位分值计算
*对于任何*附加池候选个股，其地位分值应为题材辨识度、量价急迫性、情绪对冲力三个维度的加权平均
**验证需求: 15F.5**

### Property 15: 最终附加池筛选
*对于任何*附加池候选集合，最终附加池应包含地位分值排名前5的个股
**验证需求: 15F.6**

### Property 16: 决策导航报告完整性
*对于任何*交易日，Stage3_Agent生成的决策导航报告应包含三个核心部分：基准对标表、信号剧本、决策树
**验证需求: 15G.2, 15G.3**

### Property 17: 及格线判定一致性
*对于任何*基因池个股，如果实际开盘涨幅在基准预期区间内，应标记为"符合预期"；低于下限应标记为"不及预期"；高于上限应标记为"超预期"
**验证需求: 15G1.5, 15G1.6**

### Property 18: 剧本触发条件
*对于任何*满足剧本触发条件的附加池个股（如抢筹价差>3%且量比>50），系统应将其归类到对应剧本并输出应对策略
**验证需求: 15G2.5, 15G2A.2, 15G2B.2**

### Property 19: 场景判定唯一性
*对于任何*交易日，决策树应判定当前最可能的场景（整体超预期、分歧兑现、高低切之一）
**验证需求: 15G3.1-15G3.6**

### Property 20: 报告生成时效性
*对于任何*交易日，系统应在9:25竞价结束后立即生成监控报告
**验证需求: 16.1**

### Property 21: 异常情况正确处理
*对于任何*停牌、复牌首日、重大公告、极端市场等异常情况，系统应识别并采取相应处理措施（排除、标注、调整参数）
**验证需求: 18.1-18.6**

### Property 22: 推送触发条件
*对于任何*满足推送条件的情况（打板建议且置信度>=80%、卡位信号、诱多嫌疑），系统应立即推送提醒
**验证需求: 19.2-19.4**

### Property 23: Agent独立运作
*对于任何*单个Agent，其应能独立启动和运行，不依赖其他Agent的实时状态
**验证需求: 21.1-21.3**

### Property 24: Agent失败隔离
*对于任何*Agent失败的情况，其他Agent应能继续运行，使用降级数据或默认值
**验证需求: 21.5**

### Property 25: LLM调用重试
*对于任何*LLM调用失败（超时或错误），系统应重试最多3次，最终失败时使用规则引擎降级
**验证需求: 22.5, 22.8**

### Property 26: 数据验证错误提示
*对于任何*不符合格式规范的数据，系统应输出明确的错误提示，指出具体的格式问题
**验证需求: 23.10, 0.8**

