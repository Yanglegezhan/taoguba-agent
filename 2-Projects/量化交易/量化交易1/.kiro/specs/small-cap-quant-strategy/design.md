# Design Document: Small Cap Quantitative Strategy

## Overview

本设计文档描述了小市值量化选股策略系统的技术架构和实现方案。系统采用模块化设计，将数据获取、过滤、选股、回测等功能解耦，便于测试和维护。

系统核心流程：
1. 从数据源获取全A股市场数据
2. 应用多层过滤器剔除不符合条件的股票
3. 按市值排序并选出最小市值的N只股票
4. 构建等权重投资组合
5. 在回测引擎中模拟月度调仓和交易成本
6. 生成绩效报告和可视化图表

## Architecture

系统采用分层架构设计：

```
┌─────────────────────────────────────────────────────────┐
│                    CLI / Main Entry                      │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
│ Config Manager │  │  Backtest   │  │    Reporter     │
│                │  │   Engine    │  │                 │
└────────────────┘  └──────┬──────┘  └─────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼────────┐  ┌─────▼──────┐  ┌───────▼────────┐
│  Data Provider │  │  Strategy  │  │  Portfolio     │
│                │  │  Engine    │  │  Manager       │
└────────────────┘  └─────┬──────┘  └────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼────────┐  ┌────▼──────┐  ┌──────▼────────┐
│ Filter Engine  │  │  Ranker   │  │  Rebalancer   │
│                │  │           │  │               │
└────────────────┘  └───────────┘  └───────────────┘
```

**层次说明：**
- **CLI层**: 命令行接口，处理用户输入和输出
- **配置层**: 管理策略参数和系统配置
- **回测层**: 核心回测引擎，协调各模块执行
- **策略层**: 实现选股逻辑和投资组合管理
- **数据层**: 提供市场数据和基本面数据

## Components and Interfaces

### 1. Config Manager

**职责**: 加载、验证和管理配置参数

**接口**:
```python
class ConfigManager:
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置参数的有效性"""
        
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
```

**配置结构**:
```yaml
strategy:
  portfolio_size: 10
  rebalance_frequency: "monthly"
  market_cap_type: "circulating"  # or "total"
  
filters:
  exclude_st: true
  exclude_boards: ["STAR", "BJ"]  # 科创板、北交所
  min_listing_days: 365
  min_daily_turnover: 10000000  # 1000万元
  turnover_lookback_days: 20
  enable_fundamental: true
  min_net_profit: 0
  max_debt_ratio: 0.8
  
rebalance:
  enable_buffer: true
  buffer_size: 5  # 持仓股跌出前15名才换出
  
trading_costs:
  commission_rate: 0.0003  # 万三
  slippage_rate: 0.003  # 0.3%
  enable_impact_cost: false
  
backtest:
  start_date: "2020-01-01"
  end_date: "2024-12-31"
  initial_capital: 1000000
  
data:
  provider: "akshare"  # or "tushare", "baostock"
  cache_dir: "./data/cache"
```

### 2. Data Provider

**职责**: 从数据源获取市场数据和基本面数据

**接口**:
```python
class DataProvider:
    def get_stock_list(self, date: str) -> pd.DataFrame:
        """获取指定日期的股票列表
        Returns: DataFrame with columns [code, name, listing_date, exchange, board]
        """
        
    def get_daily_prices(self, codes: List[str], start_date: str, 
                        end_date: str) -> pd.DataFrame:
        """获取日线行情数据
        Returns: DataFrame with columns [date, code, open, high, low, close, volume, amount]
        """
        
    def get_market_cap(self, codes: List[str], date: str) -> pd.DataFrame:
        """获取市值数据
        Returns: DataFrame with columns [code, total_mv, circulating_mv]
        """
        
    def get_fundamental_data(self, codes: List[str], date: str) -> pd.DataFrame:
        """获取基本面数据
        Returns: DataFrame with columns [code, net_profit, debt_ratio]
        """
        
    def get_trading_status(self, codes: List[str], date: str) -> pd.DataFrame:
        """获取交易状态
        Returns: DataFrame with columns [code, is_suspended, is_limit_up, is_limit_down]
        """
```

**实现说明**:
- 优先使用AKShare作为数据源（免费、数据全面）
- 支持数据缓存机制，避免重复请求
- 实现重试机制处理网络错误

### 3. Filter Engine

**职责**: 应用多层过滤规则剔除不符合条件的股票

**接口**:
```python
class FilterEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.filters = self._build_filter_chain()
        
    def apply_filters(self, stocks: pd.DataFrame, date: str, 
                     data_provider: DataProvider) -> pd.DataFrame:
        """应用所有过滤器
        Args:
            stocks: 待过滤的股票列表
            date: 过滤日期
            data_provider: 数据提供者
        Returns: 过滤后的股票列表
        """
        
class BaseFilter(ABC):
    @abstractmethod
    def filter(self, stocks: pd.DataFrame, date: str, 
              data_provider: DataProvider) -> pd.DataFrame:
        """过滤逻辑"""
        
class STFilter(BaseFilter):
    """剔除ST和*ST股票"""
    
class BoardFilter(BaseFilter):
    """剔除指定板块股票"""
    
class ListingDateFilter(BaseFilter):
    """剔除上市不满一年的股票"""
    
class LiquidityFilter(BaseFilter):
    """剔除流动性不足的股票"""
    
class FundamentalFilter(BaseFilter):
    """剔除基本面不达标的股票"""
```

**过滤器链模式**:
- 每个过滤器独立实现，便于测试和扩展
- 按顺序应用过滤器，逐步缩小股票池
- 记录每个过滤器剔除的股票数量

### 4. Ranker

**职责**: 按市值对股票进行排序

**接口**:
```python
class Ranker:
    def __init__(self, market_cap_type: str):
        self.market_cap_type = market_cap_type
        
    def rank_by_market_cap(self, stocks: pd.DataFrame, 
                          market_cap_data: pd.DataFrame) -> pd.DataFrame:
        """按市值排序
        Args:
            stocks: 股票列表
            market_cap_data: 市值数据
        Returns: 排序后的股票列表，包含市值列
        """
```

### 5. Strategy Engine

**职责**: 实现核心选股逻辑

**接口**:
```python
class StrategyEngine:
    def __init__(self, config: Dict[str, Any], data_provider: DataProvider):
        self.config = config
        self.data_provider = data_provider
        self.filter_engine = FilterEngine(config)
        self.ranker = Ranker(config['strategy']['market_cap_type'])
        
    def select_stocks(self, date: str, current_holdings: List[str] = None) -> List[str]:
        """选股逻辑
        Args:
            date: 选股日期
            current_holdings: 当前持仓（用于缓冲区逻辑）
        Returns: 选中的股票代码列表
        """
```

**选股流程**:
1. 获取全A股股票列表
2. 应用过滤器链
3. 获取市值数据并排序
4. 应用缓冲区逻辑（如果启用）
5. 选出前N只股票

### 6. Portfolio Manager

**职责**: 管理投资组合状态和权重

**接口**:
```python
class Portfolio:
    def __init__(self, initial_capital: float):
        self.cash = initial_capital
        self.holdings: Dict[str, int] = {}  # {code: shares}
        self.history: List[Dict] = []
        
    def get_value(self, prices: Dict[str, float]) -> float:
        """计算组合总价值"""
        
    def get_positions(self) -> Dict[str, float]:
        """获取持仓权重"""
        
class PortfolioManager:
    def __init__(self, portfolio: Portfolio, config: Dict[str, Any]):
        self.portfolio = portfolio
        self.config = config
        
    def rebalance(self, target_stocks: List[str], prices: Dict[str, float], 
                 date: str) -> Tuple[List[Trade], TradingCost]:
        """执行调仓
        Args:
            target_stocks: 目标持仓股票
            prices: 当前价格
            date: 调仓日期
        Returns: (交易列表, 交易成本)
        """
```

### 7. Rebalancer

**职责**: 计算调仓交易和应用缓冲区逻辑

**接口**:
```python
class Rebalancer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def calculate_trades(self, current_holdings: Dict[str, int], 
                        target_stocks: List[str],
                        prices: Dict[str, float],
                        total_value: float) -> List[Trade]:
        """计算需要执行的交易
        Args:
            current_holdings: 当前持仓
            target_stocks: 目标股票列表
            prices: 股票价格
            total_value: 组合总价值
        Returns: 交易列表
        """
        
    def apply_buffer_zone(self, current_holdings: List[str], 
                         ranked_stocks: pd.DataFrame,
                         portfolio_size: int,
                         buffer_size: int) -> List[str]:
        """应用缓冲区逻辑
        Args:
            current_holdings: 当前持仓股票
            ranked_stocks: 按市值排序的股票
            portfolio_size: 组合大小
            buffer_size: 缓冲区大小
        Returns: 调整后的目标股票列表
        """
```

**缓冲区逻辑**:
- 如果当前持仓股票仍在前(N+buffer_size)名内，保留
- 只有跌出前(N+buffer_size)名的股票才卖出
- 优先保留现有持仓，减少换手

### 8. Backtest Engine

**职责**: 协调回测流程，模拟交易执行

**接口**:
```python
class BacktestEngine:
    def __init__(self, config: Dict[str, Any], 
                strategy: StrategyEngine,
                data_provider: DataProvider):
        self.config = config
        self.strategy = strategy
        self.data_provider = data_provider
        self.portfolio_manager = PortfolioManager(
            Portfolio(config['backtest']['initial_capital']),
            config
        )
        
    def run(self) -> BacktestResult:
        """执行回测
        Returns: 回测结果对象
        """
        
    def _get_rebalance_dates(self) -> List[str]:
        """获取调仓日期列表"""
        
    def _update_portfolio_value(self, date: str):
        """更新组合价值"""
        
    def _execute_rebalance(self, date: str):
        """执行调仓操作"""
```

**回测流程**:
1. 初始化组合和参数
2. 遍历每个交易日：
   - 更新组合价值
   - 如果是调仓日，执行选股和调仓
   - 记录组合状态
3. 计算绩效指标
4. 返回回测结果

### 9. Trading Cost Calculator

**职责**: 计算各类交易成本

**接口**:
```python
class TradingCostCalculator:
    def __init__(self, config: Dict[str, Any]):
        self.commission_rate = config['trading_costs']['commission_rate']
        self.slippage_rate = config['trading_costs']['slippage_rate']
        self.enable_impact_cost = config['trading_costs']['enable_impact_cost']
        
    def calculate_cost(self, trades: List[Trade], 
                      liquidity_data: pd.DataFrame = None) -> TradingCost:
        """计算交易成本
        Args:
            trades: 交易列表
            liquidity_data: 流动性数据（用于冲击成本计算）
        Returns: 交易成本对象
        """
        
    def calculate_commission(self, trade_value: float) -> float:
        """计算佣金"""
        
    def calculate_slippage(self, trade_value: float) -> float:
        """计算滑点成本"""
        
    def calculate_impact_cost(self, trade: Trade, 
                             avg_daily_volume: float) -> float:
        """计算冲击成本"""
```

**成本模型**:
- 佣金: trade_value × commission_rate
- 滑点: trade_value × slippage_rate
- 冲击成本: 基于订单大小与日均成交量的比例

### 10. Reporter

**职责**: 生成回测报告和可视化图表

**接口**:
```python
class Reporter:
    def __init__(self, backtest_result: BacktestResult):
        self.result = backtest_result
        
    def generate_report(self, output_dir: str):
        """生成完整报告"""
        
    def save_holdings_history(self, filepath: str):
        """保存持仓历史"""
        
    def save_portfolio_value(self, filepath: str):
        """保存组合价值序列"""
        
    def plot_equity_curve(self, filepath: str):
        """绘制净值曲线"""
        
    def plot_turnover_analysis(self, filepath: str):
        """绘制换手率分析"""
        
    def calculate_metrics(self) -> Dict[str, float]:
        """计算绩效指标"""
```

**绩效指标**:
- 年化收益率
- 年化波动率
- 夏普比率
- 最大回撤
- Calmar比率
- 月均换手率
- 胜率

## Data Models

### Stock

```python
@dataclass
class Stock:
    code: str
    name: str
    listing_date: str
    exchange: str  # "SH", "SZ", "BJ"
    board: str  # "MAIN", "STAR", "GEM", "BJ"
    is_st: bool
```

### MarketData

```python
@dataclass
class MarketData:
    date: str
    code: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    total_mv: float  # 总市值
    circulating_mv: float  # 流通市值
```

### Trade

```python
@dataclass
class Trade:
    date: str
    code: str
    direction: str  # "BUY" or "SELL"
    shares: int
    price: float
    value: float
```

### TradingCost

```python
@dataclass
class TradingCost:
    commission: float
    slippage: float
    impact_cost: float
    total: float
```

### BacktestResult

```python
@dataclass
class BacktestResult:
    portfolio_values: pd.DataFrame  # 每日组合价值
    holdings_history: List[Dict]  # 持仓历史
    trades: List[Trade]  # 所有交易
    trading_costs: List[TradingCost]  # 交易成本
    rebalance_dates: List[str]  # 调仓日期
    turnover_rates: List[float]  # 换手率
    metrics: Dict[str, float]  # 绩效指标
```

## Correctness Properties

*属性是一种特征或行为，应该在系统的所有有效执行中保持为真——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### Property 1: Stock Pool Completeness
*For any* update operation, the stock pool should contain all active stocks from the data source with complete basic information (code, name, listing_date, exchange, board_type).

**Validates: Requirements 1.1, 1.2, 1.3**

### Property 2: Delisted Stock Marking
*For any* stock that is delisted, the stock pool should mark it as inactive and exclude it from subsequent selections.

**Validates: Requirements 1.4**

### Property 3: Filter Exclusion Correctness
*For any* stock list and filter configuration, after applying filters, the result should contain no stocks that match any exclusion criteria (ST stocks, excluded boards, newly listed stocks, suspended stocks, limit up/down stocks).

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 3.1, 3.2**

### Property 4: Liquidity Filter Threshold
*For any* stock list and minimum turnover threshold, all filtered stocks should have average daily turnover greater than or equal to the threshold over the specified lookback period.

**Validates: Requirements 3.3, 3.4**

### Property 5: Fundamental Filter Correctness
*For any* stock list with fundamental filtering enabled, all filtered stocks should have non-negative net profit, debt ratio below the maximum threshold, and complete fundamental data available.

**Validates: Requirements 4.1, 4.2, 4.3**

### Property 6: Market Cap Ranking Order
*For any* filtered stock list, the ranking result should be sorted by the specified market cap type (total or circulating) in ascending order.

**Validates: Requirements 5.1, 5.2**

### Property 7: Top N Selection Correctness
*For any* ranked stock list and portfolio size N, the selected stocks should be exactly the N stocks with the smallest market cap values.

**Validates: Requirements 5.3**

### Property 8: Deterministic Tie-Breaking
*For any* stock list with identical market cap values, applying the selection algorithm multiple times should always produce the same result.

**Validates: Requirements 5.4**

### Property 9: Equal Weight Allocation
*For any* portfolio with N stocks, each stock should have a weight of exactly 1/N, and the sum of all weights should equal 1.0.

**Validates: Requirements 6.1, 6.2**

### Property 10: Position Sizing Correctness
*For any* portfolio value V and portfolio size N, each stock position should have a target value of V/N (before considering trading costs).

**Validates: Requirements 6.4**

### Property 11: Rebalance Date Correctness
*For any* backtest period with monthly rebalancing, all rebalance dates should be the first trading day of each month.

**Validates: Requirements 6.3**

### Property 12: Buffer Zone Retention
*For any* portfolio with buffer zone enabled, if a current holding ranks within the top (N + buffer_size) by market cap, it should be retained in the next period.

**Validates: Requirements 7.1, 7.2**

### Property 13: Turnover Rate Calculation
*For any* rebalance operation, the turnover rate should equal (total_buy_value + total_sell_value) / (2 × portfolio_value).

**Validates: Requirements 7.3**

### Property 14: Trading Cost Calculation
*For any* trade with value V, commission rate C, and slippage rate S, the total cost should equal V × C + V × S (plus impact cost if enabled).

**Validates: Requirements 8.1, 8.2, 8.3, 8.4**

### Property 15: Portfolio Initialization
*For any* backtest with initial capital I, the portfolio should start with cash = I and empty holdings.

**Validates: Requirements 9.1**

### Property 16: Daily Portfolio Value
*For any* trading day, the portfolio value should equal cash + sum(shares_i × price_i) for all holdings i.

**Validates: Requirements 9.3**

### Property 17: Configuration Validation
*For any* configuration with invalid parameter values (negative numbers, out-of-range values), the system should reject it with a descriptive error message.

**Validates: Requirements 10.3, 10.4**

### Property 18: Configuration Round-Trip
*For any* valid configuration, saving it to a file and then loading it should produce an equivalent configuration object.

**Validates: Requirements 10.1**

### Property 19: Retry Exponential Backoff
*For any* sequence of failed data fetching attempts, the delay between retries should increase exponentially (e.g., 1s, 2s, 4s, 8s).

**Validates: Requirements 11.5**



## Error Handling

### Data Fetching Errors

**策略**: 实现重试机制和降级方案

- 网络错误: 使用指数退避重试，最多3次
- 数据缺失: 记录警告日志，跳过该股票
- API限流: 增加请求间隔，使用缓存数据
- 数据格式错误: 验证数据schema，拒绝无效数据

### Configuration Errors

**策略**: 快速失败，提供清晰的错误信息

- 缺失必需参数: 抛出ConfigurationError，指明缺失的参数名
- 无效参数值: 抛出ValidationError，说明有效范围
- 文件不存在: 抛出FileNotFoundError，提供示例配置路径

### Trading Errors

**策略**: 记录错误但继续回测

- 价格数据缺失: 使用前一日收盘价，记录警告
- 无法买入/卖出: 跳过该交易，记录到报告中
- 资金不足: 按可用资金比例调整仓位

### Calculation Errors

**策略**: 验证输入，防御性编程

- 除零错误: 检查分母，返回默认值或NaN
- 数值溢出: 使用适当的数据类型（Decimal for money）
- 日期错误: 验证日期格式和范围

## Testing Strategy

### Unit Testing

使用pytest框架进行单元测试，覆盖各个组件的核心功能：

**测试范围**:
- 每个Filter类的过滤逻辑
- Ranker的排序逻辑
- TradingCostCalculator的成本计算
- Portfolio的价值计算和持仓管理
- ConfigManager的加载和验证逻辑

**测试方法**:
- 使用mock数据避免依赖外部数据源
- 测试边界条件（空列表、单个元素、大量元素）
- 测试错误处理路径
- 使用parametrize测试多种输入组合

### Property-Based Testing

使用Hypothesis库进行基于属性的测试，验证系统的通用正确性：

**配置**:
- 每个属性测试运行最少100次迭代
- 使用自定义生成器创建有效的测试数据
- 标记每个测试对应的设计属性编号

**测试策略**:
- 生成随机股票列表测试过滤器
- 生成随机市值数据测试排序和选股
- 生成随机交易测试成本计算
- 生成随机配置测试验证逻辑

**示例标记格式**:
```python
# Feature: small-cap-quant-strategy, Property 3: Filter Exclusion Correctness
@given(stock_list=stock_lists(), config=filter_configs())
def test_filter_exclusion_correctness(stock_list, config):
    ...
```

### Integration Testing

测试组件之间的集成：

- 测试完整的选股流程（数据获取→过滤→排序→选股）
- 测试调仓流程（选股→计算交易→应用成本→更新持仓）
- 测试回测流程（初始化→多次调仓→生成报告）

### End-to-End Testing

使用小规模历史数据进行端到端测试：

- 准备测试数据集（1年历史数据，100只股票）
- 运行完整回测流程
- 验证输出文件格式和内容
- 验证绩效指标的合理性

### Performance Testing

验证系统性能满足要求：

- 测试大规模数据处理能力（5000只股票，5年数据）
- 测试回测速度（应在合理时间内完成）
- 测试内存使用（避免内存泄漏）

## Implementation Notes

### Technology Stack

- **语言**: Python 3.9+
- **数据处理**: pandas, numpy
- **数据源**: akshare (优先), tushare (备选)
- **测试**: pytest, hypothesis
- **可视化**: matplotlib, seaborn
- **配置**: PyYAML
- **日志**: logging

### Code Organization

```
small_cap_strategy/
├── config/
│   ├── __init__.py
│   ├── manager.py
│   └── schema.py
├── data/
│   ├── __init__.py
│   ├── provider.py
│   └── cache.py
├── strategy/
│   ├── __init__.py
│   ├── filters.py
│   ├── ranker.py
│   ├── selector.py
│   └── rebalancer.py
├── backtest/
│   ├── __init__.py
│   ├── engine.py
│   ├── portfolio.py
│   └── cost.py
├── reporting/
│   ├── __init__.py
│   ├── reporter.py
│   └── visualizer.py
├── models.py
├── utils.py
├── cli.py
└── main.py
```

### Development Workflow

1. 实现数据层（DataProvider）
2. 实现过滤器链（FilterEngine）
3. 实现选股逻辑（StrategyEngine）
4. 实现投资组合管理（Portfolio, PortfolioManager）
5. 实现回测引擎（BacktestEngine）
6. 实现报告生成（Reporter）
7. 实现CLI接口
8. 编写测试和文档

### Performance Considerations

- 使用pandas向量化操作避免循环
- 缓存数据避免重复请求
- 使用适当的数据类型减少内存占用
- 考虑使用多进程处理大规模回测

### Future Enhancements

- 支持多因子选股（不仅限于市值）
- 支持自定义调仓频率（周度、季度）
- 支持风险平价等其他权重分配方法
- 支持实盘交易接口
- 支持参数优化和回测分析工具
