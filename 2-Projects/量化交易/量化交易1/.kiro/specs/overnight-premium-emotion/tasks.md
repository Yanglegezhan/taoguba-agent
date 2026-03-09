# 实现计划：市场情绪隔夜溢价策略

## 概述

本项目分为两大部分实现：
1. **第一部分（研究探索）**：使用Python进行历史数据分析，挖掘市场情绪与个股特征对隔夜溢价的影响规律
2. **第二部分（聚宽实现）**：在聚宽平台实现完整的隔夜溢价交易策略

## 任务

---

# 第一部分：研究探索阶段

- [x] 1. 项目初始化与基础结构
  - [x] 1.1 创建项目目录结构
    - 创建 `overnight_premium_research/` 目录
    - 创建 `data/`, `output/`, `config/` 子目录
    - 创建 `requirements.txt` 依赖文件（pandas, numpy, matplotlib, seaborn, scipy）
    - 创建 `config.yaml` 默认配置文件
    - _Requirements: 1.1_

  - [x] 1.2 定义核心数据类型
    - 创建 `models.py` 定义 StockIndicators, MarketIndicators, ClassifiedSamples, CorrelationResult, GroupStats, TestResult 数据类
    - _Requirements: 2.1-2.8, 3.1-3.12_

- [x] 2. 数据采集模块
  - [x] 2.1 实现研究数据采集 ResearchDataCollector
    - 创建 `data_collector.py`
    - 实现 `fetch_daily_data()` 获取日线数据（使用akshare或tushare）
    - 实现 `fetch_limit_data()` 获取涨跌停数据
    - 实现 `fetch_sector_data()` 获取板块数据
    - 实现 `fetch_stock_info()` 获取股票基本信息
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 2.2 实现数据清洗和预处理
    - 创建 `data_cleaner.py`
    - 实现排除ST、新股的逻辑
    - 实现停牌数据处理
    - 实现除权除息数据处理
    - _Requirements: 1.5, 1.6_

- [-] 3. 指标计算模块
  - [x] 3.1 实现个股指标计算
    - 创建 `indicator_calculator.py`
    - 实现 `calc_change_pct()` 计算涨跌幅
    - 实现 `calc_turnover_rate()` 计算换手率
    - 实现 `calc_volume_ratio()` 计算量比
    - 实现 `calc_amplitude()` 计算振幅
    - 实现 `calc_close_position()` 计算收盘位置
    - 实现 `calc_overnight_premium()` 计算隔夜溢价
    - _Requirements: 1.4, 3.1-3.6_

  - [x] 3.2 编写个股指标计算的属性测试
    - **Property 4: 个股指标计算正确性**
    - **Validates: Requirements 3.1, 3.4, 3.5**

  - [x] 3.3 编写隔夜溢价计算的属性测试
    - **Property 1: 隔夜溢价计算正确性**
    - **Validates: Requirements 1.4**

  - [x] 3.4 实现市场情绪指标计算
    - 实现 `calc_limit_ratio()` 计算涨跌停比
    - 实现 `calc_up_down_ratio()` 计算涨跌家数比
    - 实现 `calc_board_height()` 计算连板高度
    - 实现 `calc_seal_rate()` 计算封板率
    - _Requirements: 2.1-2.8_

  - [x] 3.5 编写市场情绪指标计算的属性测试
    - **Property 2: 涨跌停比计算正确性**
    - **Property 3: 涨跌家数比计算正确性**
    - **Property 6: 连板高度计算正确性**
    - **Property 7: 封板率计算正确性**
    - **Validates: Requirements 2.2, 2.4, 2.5, 2.8**

  - [x] 3.6 实现涨停标记功能
    - 实现 `is_limit_up()` 判断是否涨停
    - 实现 `is_once_limit_up()` 判断是否曾涨停
    - _Requirements: 3.7_

  - [x] 3.7 编写涨停标记的属性测试

    - **Property 18: 涨停标记正确性**
    - **Validates: Requirements 3.7**

- [x] 4. 检查点 - 确保指标计算模块测试通过
  - 确保所有测试通过，如有问题请询问用户
  -需要请你检查，所有测试用数据都可以真实获得，不要模拟数据！

- [-] 5. 样本分类模块
  - [x] 5.1 实现样本分类器 SampleClassifier
    - 创建 `sample_classifier.py`
    - 实现 `classify()` 将样本分为可交易样本和统计参考样本
    - 实现 `filter_valid_samples()` 过滤有效样本
    - _Requirements: 3.10, 3.11, 3.12_

  - [x] 5.2 编写样本分类的属性测试

    - **Property 8: 样本分类正确性**
    - **Property 9: 数据过滤正确性**
    - **Validates: Requirements 3.10, 1.5**

- [x] 6. 统计分析模块
  - [x] 6.1 实现统计分析器 StatisticalAnalyzer
    - 创建 `statistical_analyzer.py`
    - 实现 `calc_correlation()` 计算相关系数
    - 实现 `calc_ic_series()` 计算IC序列
    - 实现 `group_analysis()` 分组统计分析
    - 实现 `compare_samples()` 对比可交易样本与涨停样本
    - _Requirements: 5.1-5.11_

  - [x] 6.2 编写相关系数计算的属性测试

    - **Property 10: 相关系数范围正确性**
    - **Validates: Requirements 5.2**

  - [x] 6.3 编写胜率计算的属性测试

    - **Property 11: 胜率计算正确性**
    - **Validates: Requirements 6.6**

- [ ] 7. 条件组合测试模块
  - [x] 7.1 实现条件测试器 ConditionTester
    - 创建 `condition_tester.py`
    - 实现 `test_single_condition()` 测试单一条件
    - 实现 `test_combination()` 测试条件组合
    - 实现 `grid_search()` 网格搜索最优参数
    - 实现 `find_best_conditions()` 找出最优条件组合
    - _Requirements: 6.1-6.8_

- [x] 8. 可视化模块
  - [x] 8.1 实现可视化器 Visualizer
    - 创建 `visualizer.py`
    - 实现 `plot_emotion_premium_relation()` 绘制情绪与溢价关系图
    - 实现 `plot_factor_scatter()` 绘制因子散点图
    - 实现 `plot_heatmap()` 绘制胜率热力图
    - 实现 `plot_premium_distribution()` 绘制溢价分布图
    - 实现 `generate_report()` 生成研究报告
    - _Requirements: 7.1-7.5_

- [x] 9. 研究主程序
  - [x] 9.1 实现研究主程序入口
    - 创建 `research_main.py`
    - 集成数据采集、指标计算、样本分类、统计分析、条件测试、可视化模块
    - 实现完整的研究流程
    - 输出研究结论和最优参数
    - _Requirements: 6.7, 6.8_

- [x] 10. 检查点 - 确保研究阶段功能完整
  - 运行完整研究流程
  - 验证输出研究报告和最优参数
  - 如有问题请询问用户

---

# 第二部分：聚宽策略实现阶段

- [ ] 11. 聚宽数据接口模块
  - [ ] 11.1 实现聚宽数据接口 JQDataFetcher
    - 创建 `jq_data_fetcher.py`
    - 实现 `get_daily_price()` 获取日线行情
    - 实现 `get_limit_up_stocks()` 获取涨停股列表
    - 实现 `get_limit_down_stocks()` 获取跌停股列表
    - 实现 `get_sector_stocks()` 获取板块成分股
    - 实现 `get_market_cap()` 获取流通市值
    - _Requirements: 8.1-8.5_

- [ ] 12. 市场情绪计算模块
  - [ ] 12.1 实现市场情绪计算器 EmotionCalculator
    - 创建 `emotion_calculator.py`
    - 实现 `calc_emotion_index()` 计算综合情绪指数
    - 实现 `classify_emotion_level()` 分类情绪等级
    - 实现 `detect_emotion_cycle()` 检测情绪周期
    - 实现 `is_tradable_day()` 判断是否适合交易
    - _Requirements: 9.1-9.6_

  - [ ]* 12.2 编写情绪等级分类的属性测试
    - **Property 14: 情绪等级分类正确性**
    - **Validates: Requirements 9.6**

- [ ] 13. 个股筛选模块
  - [ ] 13.1 实现个股筛选器 StockFilter
    - 创建 `stock_filter.py`
    - 实现 `exclude_limit_up()` 排除涨停股
    - 实现 `exclude_st_new()` 排除ST和新股
    - 实现 `filter_by_indicators()` 按指标筛选
    - 实现 `filter_by_sector()` 按板块筛选
    - 实现 `filter_stocks()` 综合筛选
    - _Requirements: 10.1-10.8_

  - [ ]* 13.2 编写筛选条件一致性的属性测试
    - **Property 12: 筛选条件一致性**
    - **Validates: Requirements 10.1-10.5**

- [ ] 14. 评分排序模块
  - [ ] 14.1 实现评分排序器 Scorer
    - 创建 `scorer.py`
    - 实现 `calc_score()` 计算综合得分
    - 实现 `rank_stocks()` 排序并返回前N只
    - _Requirements: 11.1-11.4_

  - [ ]* 14.2 编写评分排序的属性测试
    - **Property 13: 评分排序正确性**
    - **Validates: Requirements 11.3**

- [ ] 15. 检查点 - 确保筛选和评分模块测试通过
  - 确保所有测试通过，如有问题请询问用户

- [ ] 16. 风控模块
  - [ ] 16.1 实现风险控制器 RiskController
    - 创建 `risk_controller.py`
    - 实现 `should_trade()` 判断是否应该交易
    - 实现 `check_daily_loss()` 检查单日亏损
    - 实现 `update_consecutive_loss()` 更新连续亏损计数
    - 实现 `get_max_stocks()` 获取最大选股数量
    - _Requirements: 13.1-13.5_

  - [ ]* 16.2 编写选股数量限制的属性测试
    - **Property 15: 选股数量限制正确性**
    - **Validates: Requirements 12.4**

  - [ ]* 16.3 编写连续亏损计数的属性测试
    - **Property 16: 连续亏损计数正确性**
    - **Validates: Requirements 13.4**

  - [ ]* 16.4 编写弱势市场暂停交易的属性测试
    - **Property 17: 弱势市场暂停交易正确性**
    - **Validates: Requirements 13.1, 13.2**

- [ ] 17. 交易执行模块
  - [ ] 17.1 实现交易执行器 TradeExecutor
    - 创建 `trade_executor.py`
    - 实现 `execute_buy()` 执行买入
    - 实现 `execute_sell_all()` 次日开盘全部卖出
    - 实现 `calc_position_size()` 计算仓位大小
    - _Requirements: 12.1-12.6_

- [ ] 18. 聚宽策略主程序
  - [ ] 18.1 实现聚宽策略主程序
    - 创建 `jq_strategy.py`
    - 实现 `initialize()` 初始化函数
    - 实现 `before_trading_start()` 盘前处理
    - 实现 `handle_data()` 主逻辑（14:50选股，14:55-57买入）
    - 实现 `after_trading_end()` 盘后处理
    - 集成所有模块
    - _Requirements: 12.1-12.6, 15.4-15.6_

  - [ ] 18.2 实现回测配置
    - 配置回测参数（起止日期、初始资金等）
    - 实现绩效统计（年化收益、最大回撤、夏普比率、胜率）
    - _Requirements: 14.1-14.6_

- [ ] 19. 参数配置与日志
  - [ ] 19.1 实现参数配置模块
    - 创建 `config.py`
    - 实现筛选阈值参数配置
    - 实现评分权重参数配置
    - 实现风控参数配置
    - _Requirements: 15.1-15.3_

  - [ ] 19.2 实现日志记录模块
    - 创建 `logger.py`
    - 实现每日运行日志记录
    - 实现市场情绪状态记录
    - 实现选股结果和交易结果记录
    - _Requirements: 15.4-15.6_

- [ ] 20. 最终检查点 - 确保所有测试通过
  - 运行完整测试套件
  - 验证研究阶段输出正确
  - 验证聚宽策略可正常运行
  - 如有问题请询问用户

## 备注

- 标记 `*` 的任务为可选任务，可跳过以加快MVP开发
- 每个任务都引用了具体的需求编号以便追溯
- 检查点用于确保增量验证
- 属性测试验证通用正确性属性
- 第一部分研究结论将作为第二部分的参数输入

