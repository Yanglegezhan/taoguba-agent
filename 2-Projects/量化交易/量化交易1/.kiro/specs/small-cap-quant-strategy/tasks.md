# Implementation Plan: Small Cap Quantitative Strategy

## Overview

本实现计划将小市值量化选股策略系统分解为可执行的编码任务。实现采用自底向上的方式，先构建基础组件（数据模型、配置管理、数据获取），然后实现核心逻辑（过滤、选股、组合管理），最后集成回测引擎和报告生成。

每个任务都包含具体的实现目标和对应的需求引用，确保实现完整覆盖所有功能需求。

## Tasks

- [x] 1. 项目初始化和基础设施
  - 创建项目目录结构
  - 配置Python环境和依赖（requirements.txt）
  - 设置日志系统
  - 创建示例配置文件
  - _Requirements: 10.1, 10.2_

- [ ]* 1.1 编写配置文件schema验证测试
  - **Property 18: Configuration Round-Trip**
  - **Validates: Requirements 10.1**

- [ ] 2. 实现数据模型
  - [x] 2.1 创建核心数据类（Stock, MarketData, Trade, TradingCost, BacktestResult）
    - 使用dataclass定义所有数据模型
    - 添加类型注解和文档字符串
    - _Requirements: 1.3, 8.4, 9.4_

- [ ] 2.2 编写数据模型属性测试

  - 测试数据类的字段完整性
  - 测试数据类的序列化和反序列化
  - _Requirements: 1.3_

- [ ] 3. 实现配置管理模块
  - [x] 3.1 实现ConfigManager类
    - 实现load_config方法（支持YAML格式）
    - 实现validate_config方法（验证必需参数和值范围）
    - 实现get方法（支持默认值）
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [ ]* 3.2 编写配置验证属性测试
  - **Property 17: Configuration Validation**
  - **Validates: Requirements 10.3, 10.4**

- [ ]* 3.3 编写配置加载单元测试
  - 测试有效配置加载
  - 测试无效配置拒绝
  - 测试缺失参数错误
  - _Requirements: 10.1, 10.3_

- [ ] 4. 实现数据提供者模块
  - [x] 4.1 实现DataProvider基类和AKShareProvider
    - 实现get_stock_list方法
    - 实现get_daily_prices方法
    - 实现get_market_cap方法
    - 实现get_fundamental_data方法
    - 实现get_trading_status方法
    - 添加数据缓存机制
    - _Requirements: 1.1, 1.2, 11.1, 11.2, 11.3, 11.4_

- [ ] 4.2 实现重试机制
    - 实现指数退避重试逻辑
    - 添加错误日志记录
    - _Requirements: 11.5_

- [ ]* 4.3 编写重试机制属性测试
  - **Property 19: Retry Exponential Backoff**
  - **Validates: Requirements 11.5**

- [ ]* 4.4 编写数据提供者单元测试
  - 使用mock测试各个数据获取方法
  - 测试缓存机制
  - 测试错误处理
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ] 5. Checkpoint - 基础设施验证
  - 确保所有测试通过，询问用户是否有问题

- [ ] 6. 实现过滤器模块
  - [ ] 6.1 实现BaseFilter抽象类和过滤器链
    - 创建BaseFilter基类
    - 实现FilterEngine类（管理过滤器链）
    - _Requirements: 2.4_

- [ ] 6.2 实现具体过滤器类
    - 实现STFilter（剔除ST和*ST股票）
    - 实现BoardFilter（剔除指定板块）
    - 实现ListingDateFilter（剔除次新股）
    - 实现LiquidityFilter（剔除流动性不足股票）
    - 实现FundamentalFilter（剔除基本面不达标股票）
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4_

- [ ]* 6.3 编写过滤器正确性属性测试
  - **Property 3: Filter Exclusion Correctness**
  - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 3.1, 3.2**

- [ ]* 6.4 编写流动性过滤属性测试
  - **Property 4: Liquidity Filter Threshold**
  - **Validates: Requirements 3.3, 3.4**

- [ ]* 6.5 编写基本面过滤属性测试
  - **Property 5: Fundamental Filter Correctness**
  - **Validates: Requirements 4.1, 4.2, 4.3**

- [ ]* 6.6 编写过滤器单元测试
  - 测试每个过滤器的独立功能
  - 测试过滤器链的组合效果
  - 测试边界条件
  - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2_

- [ ] 7. 实现排序和选股模块
  - [ ] 7.1 实现Ranker类
    - 实现rank_by_market_cap方法
    - 支持总市值和流通市值两种排序
    - 实现确定性的tie-breaking规则
    - _Requirements: 5.1, 5.2, 5.4_

- [ ]* 7.2 编写排序正确性属性测试
  - **Property 6: Market Cap Ranking Order**
  - **Validates: Requirements 5.1, 5.2**

- [ ]* 7.3 编写确定性tie-breaking属性测试
  - **Property 8: Deterministic Tie-Breaking**
  - **Validates: Requirements 5.4**

- [ ] 7.4 实现StrategyEngine类
    - 实现select_stocks方法
    - 集成FilterEngine和Ranker
    - 实现top N选股逻辑
    - _Requirements: 5.3_

- [ ]* 7.5 编写选股正确性属性测试
  - **Property 7: Top N Selection Correctness**
  - **Validates: Requirements 5.3**

- [ ]* 7.6 编写选股单元测试
  - 测试完整选股流程
  - 测试不同配置下的选股结果
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 8. Checkpoint - 选股逻辑验证
  - 确保所有测试通过，询问用户是否有问题

- [ ] 9. 实现投资组合管理模块
  - [ ] 9.1 实现Portfolio类
    - 实现get_value方法（计算组合价值）
    - 实现get_positions方法（获取持仓权重）
    - 实现持仓历史记录
    - _Requirements: 6.1, 6.2, 9.3_

- [ ]* 9.2 编写组合价值计算属性测试
  - **Property 16: Daily Portfolio Value**
  - **Validates: Requirements 9.3**

- [ ] 9.3 实现Rebalancer类
    - 实现calculate_trades方法
    - 实现apply_buffer_zone方法
    - 实现换手率计算
    - _Requirements: 6.4, 7.1, 7.2, 7.3_

- [ ]* 9.4 编写等权重分配属性测试
  - **Property 9: Equal Weight Allocation**
  - **Validates: Requirements 6.1, 6.2**

- [ ]* 9.5 编写仓位计算属性测试
  - **Property 10: Position Sizing Correctness**
  - **Validates: Requirements 6.4**

- [ ]* 9.6 编写缓冲区逻辑属性测试
  - **Property 12: Buffer Zone Retention**
  - **Validates: Requirements 7.1, 7.2**

- [ ]* 9.7 编写换手率计算属性测试
  - **Property 13: Turnover Rate Calculation**
  - **Validates: Requirements 7.3**

- [ ] 9.8 实现PortfolioManager类
    - 实现rebalance方法
    - 集成Rebalancer和TradingCostCalculator
    - _Requirements: 6.3, 6.4_

- [ ]* 9.9 编写投资组合管理单元测试
  - 测试调仓交易计算
  - 测试缓冲区机制
  - 测试换手率统计
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3_

- [ ] 10. 实现交易成本计算模块
  - [ ] 10.1 实现TradingCostCalculator类
    - 实现calculate_cost方法
    - 实现calculate_commission方法
    - 实现calculate_slippage方法
    - 实现calculate_impact_cost方法（可选）
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ]* 10.2 编写交易成本计算属性测试
  - **Property 14: Trading Cost Calculation**
  - **Validates: Requirements 8.1, 8.2, 8.3, 8.4**

- [ ]* 10.3 编写交易成本单元测试
  - 测试各类成本计算
  - 测试成本分类统计
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 11. Checkpoint - 组合管理验证
  - 确保所有测试通过，询问用户是否有问题

- [ ] 12. 实现回测引擎
  - [ ] 12.1 实现BacktestEngine类
    - 实现run方法（主回测循环）
    - 实现_get_rebalance_dates方法
    - 实现_update_portfolio_value方法
    - 实现_execute_rebalance方法
    - _Requirements: 9.1, 9.2, 9.3_

- [ ]* 12.2 编写组合初始化属性测试
  - **Property 15: Portfolio Initialization**
  - **Validates: Requirements 9.1**

- [ ]* 12.3 编写调仓日期属性测试
  - **Property 11: Rebalance Date Correctness**
  - **Validates: Requirements 6.3**

- [ ]* 12.4 编写回测引擎集成测试
  - 使用小规模测试数据运行完整回测
  - 验证回测结果的合理性
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 13. 实现报告生成模块
  - [ ] 13.1 实现Reporter类
    - 实现calculate_metrics方法（计算绩效指标）
    - 实现save_holdings_history方法
    - 实现save_portfolio_value方法
    - 实现generate_report方法
    - _Requirements: 9.4, 12.1, 12.2, 12.4_

- [ ] 13.2 实现可视化功能
    - 实现plot_equity_curve方法
    - 实现plot_turnover_analysis方法
    - _Requirements: 12.3, 12.5_

- [ ]* 13.3 编写报告生成单元测试
  - 测试绩效指标计算
  - 测试文件输出
  - 测试图表生成
  - _Requirements: 9.4, 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ] 14. 实现CLI接口
  - [ ] 14.1 创建命令行接口
    - 实现参数解析（配置文件路径、输出目录等）
    - 实现主执行流程
    - 添加进度显示和日志输出
    - _Requirements: 所有需求的集成_

- [ ]* 14.2 编写端到端测试
  - 使用真实配置运行完整流程
  - 验证所有输出文件
  - _Requirements: 所有需求的集成_

- [ ] 15. 最终检查点
  - 运行所有测试确保通过
  - 生成测试覆盖率报告
  - 验证文档完整性
  - 询问用户是否有问题或需要调整

## Notes

- 标记为 `*` 的任务是可选的测试任务，可以根据开发进度决定是否实施
- 每个任务都引用了具体的需求编号，确保实现的可追溯性
- 检查点任务用于阶段性验证，确保增量开发的质量
- 属性测试使用Hypothesis库，每个测试至少运行100次迭代
- 单元测试使用pytest框架，覆盖核心功能和边界条件
- 建议按顺序执行任务，每完成一个模块后运行相关测试
