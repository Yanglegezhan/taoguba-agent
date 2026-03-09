# Requirements Document

## Introduction

本文档定义了小市值量化选股策略系统的需求。该系统基于市值因子进行选股，通过严格的过滤条件和风险控制机制，构建月度调仓的量化投资组合。系统需要处理A股市场的特殊性（涨跌停、停牌、退市风险等），并在回测中准确模拟实盘交易的各种摩擦成本。

## Glossary

- **System**: 小市值量化选股策略系统
- **Stock_Pool**: 全A股市场的股票集合
- **Market_Cap**: 总市值或流通市值
- **Portfolio**: 投资组合，包含选中的股票及其权重
- **Rebalance**: 调仓操作，按照策略规则调整持仓
- **Filter_Engine**: 过滤引擎，负责剔除不符合条件的股票
- **Backtest_Engine**: 回测引擎，模拟历史交易并计算收益
- **Trading_Cost**: 交易成本，包括手续费、滑点、冲击成本等
- **ST_Stock**: 特别处理股票，包括*ST和ST标记的股票
- **Liquidity**: 流动性，衡量股票交易的活跃程度
- **Buffer_Zone**: 缓冲区，用于减少不必要的换手

## Requirements

### Requirement 1: 股票池管理

**User Story:** 作为策略管理者，我希望系统能够维护全A股市场的股票池，以便进行选股操作。

#### Acceptance Criteria

1. THE System SHALL maintain a stock pool covering all A-share market stocks
2. WHEN updating the stock pool, THE System SHALL fetch latest stock list from data source
3. THE System SHALL store stock basic information including code, name, listing date, exchange, and board type
4. WHEN a stock is delisted, THE System SHALL mark it as inactive in the stock pool

### Requirement 2: 异常品种过滤

**User Story:** 作为风险控制者，我希望系统能够自动剔除高风险的异常品种，以避免退市风险和极端波动。

#### Acceptance Criteria

1. WHEN filtering stocks, THE Filter_Engine SHALL exclude all ST and *ST stocks
2. WHERE user configuration specifies board exclusion, THE Filter_Engine SHALL exclude stocks from specified boards (STAR Market, Beijing Stock Exchange)
3. WHEN a stock's listing date is less than one year from current date, THE Filter_Engine SHALL exclude it from selection
4. THE Filter_Engine SHALL apply all exclusion rules before market cap ranking

### Requirement 3: 流动性过滤

**User Story:** 作为交易执行者，我希望系统只选择流动性充足的股票，以确保能够顺利买入和卖出。

#### Acceptance Criteria

1. WHEN filtering stocks on rebalance date, THE Filter_Engine SHALL exclude suspended stocks
2. WHEN filtering stocks on rebalance date, THE Filter_Engine SHALL exclude stocks with limit up or limit down
3. WHERE user configuration specifies minimum daily turnover, THE Filter_Engine SHALL exclude stocks with average daily turnover below the threshold
4. THE Filter_Engine SHALL calculate average daily turnover over a configurable lookback period (default 20 trading days)

### Requirement 4: 基本面防雷过滤

**User Story:** 作为基本面分析师，我希望系统能够剔除财务状况恶化的公司，以降低持仓风险。

#### Acceptance Criteria

1. WHERE user configuration enables fundamental filtering, THE Filter_Engine SHALL exclude stocks with negative net profit
2. WHERE user configuration specifies maximum debt ratio, THE Filter_Engine SHALL exclude stocks with debt-to-asset ratio above the threshold
3. WHEN fundamental data is unavailable for a stock, THE Filter_Engine SHALL exclude it from selection
4. THE Filter_Engine SHALL use the most recent quarterly or annual financial report

### Requirement 5: 市值排序与选股

**User Story:** 作为策略核心逻辑实现者，我希望系统按照市值从小到大排序，并选出最小市值的股票。

#### Acceptance Criteria

1. WHEN selecting stocks, THE System SHALL rank all filtered stocks by market cap in ascending order
2. WHERE user configuration specifies market cap type, THE System SHALL use either total market cap or circulating market cap
3. THE System SHALL select the top N stocks with smallest market cap (default N=10)
4. WHEN multiple stocks have identical market cap, THE System SHALL apply a deterministic tie-breaking rule (e.g., by stock code)

### Requirement 6: 投资组合构建

**User Story:** 作为投资组合管理者，我希望系统能够构建等权重的投资组合，并支持月度调仓。

#### Acceptance Criteria

1. WHEN constructing portfolio, THE System SHALL assign equal weight to each selected stock
2. THE Portfolio SHALL contain exactly N stocks (default N=10)
3. WHEN rebalancing, THE System SHALL execute on the first trading day of each month
4. THE System SHALL calculate target positions based on total portfolio value and equal weight allocation

### Requirement 7: 调仓优化与缓冲区

**User Story:** 作为交易成本控制者,我希望系统能够通过缓冲区机制减少不必要的换手，以降低交易成本。

#### Acceptance Criteria

1. WHERE user configuration enables buffer zone, THE System SHALL only sell a holding stock if it ranks outside top (N + buffer_size) by market cap
2. WHEN buffer zone is enabled, THE System SHALL prioritize keeping existing holdings that still qualify
3. THE System SHALL calculate turnover rate for each rebalance period
4. THE System SHALL log turnover statistics for performance analysis

### Requirement 8: 交易成本模拟

**User Story:** 作为回测准确性保证者，我希望系统能够准确模拟各种交易成本，以反映真实交易环境。

#### Acceptance Criteria

1. WHEN executing trades in backtest, THE Backtest_Engine SHALL apply commission fees based on user configuration
2. WHEN executing trades in backtest, THE Backtest_Engine SHALL apply slippage cost (default 0.2% - 0.5% per side)
3. WHERE user configuration specifies impact cost model, THE Backtest_Engine SHALL calculate impact cost based on order size and liquidity
4. THE Backtest_Engine SHALL separately track and report each type of trading cost

### Requirement 9: 回测执行引擎

**User Story:** 作为策略验证者，我希望系统能够在历史数据上回测策略表现，并生成详细的绩效报告。

#### Acceptance Criteria

1. WHEN starting backtest, THE Backtest_Engine SHALL initialize portfolio with specified starting capital
2. WHEN reaching rebalance date, THE Backtest_Engine SHALL execute stock selection and portfolio rebalancing
3. THE Backtest_Engine SHALL update portfolio value daily based on stock price changes
4. WHEN backtest completes, THE Backtest_Engine SHALL generate performance report including returns, Sharpe ratio, max drawdown, and turnover

### Requirement 10: 配置管理

**User Story:** 作为策略使用者，我希望能够通过配置文件灵活调整策略参数，而无需修改代码。

#### Acceptance Criteria

1. THE System SHALL load strategy parameters from a configuration file (YAML or JSON format)
2. THE System SHALL support configuration of: portfolio size, rebalance frequency, market cap type, filter thresholds, trading costs, and buffer zone settings
3. WHEN configuration file is invalid or missing required parameters, THE System SHALL report clear error messages
4. THE System SHALL validate configuration parameters and reject invalid values

### Requirement 11: 数据接口

**User Story:** 作为数据集成者，我希望系统能够从标准数据源获取所需的市场数据和财务数据。

#### Acceptance Criteria

1. THE System SHALL support fetching daily stock price data (open, high, low, close, volume)
2. THE System SHALL support fetching stock basic information (listing date, ST status, board type)
3. THE System SHALL support fetching market cap data (total and circulating)
4. THE System SHALL support fetching fundamental data (net profit, debt-to-asset ratio)
5. WHEN data fetching fails, THE System SHALL retry with exponential backoff and log error details

### Requirement 12: 结果输出与可视化

**User Story:** 作为策略分析者，我希望系统能够输出详细的回测结果和可视化图表，以便分析策略表现。

#### Acceptance Criteria

1. WHEN backtest completes, THE System SHALL save portfolio holdings history to CSV file
2. WHEN backtest completes, THE System SHALL save daily portfolio value to CSV file
3. THE System SHALL generate equity curve chart showing portfolio value over time
4. THE System SHALL generate performance metrics table including annualized return, volatility, Sharpe ratio, max drawdown, and Calmar ratio
5. WHERE user requests, THE System SHALL generate turnover analysis chart showing monthly turnover rates
