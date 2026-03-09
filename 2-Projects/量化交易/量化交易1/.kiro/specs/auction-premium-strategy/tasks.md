# 实现计划：竞价溢价策略评估系统

## 概述

基于Python实现A股竞价溢价策略评估系统，采用模块化设计，支持数据采集、多维度筛选、回测评估和风险控制。

## 任务

- [x] 1. 项目初始化与基础结构
  - [x] 1.1 创建项目目录结构和配置文件
    - 创建 `auction_strategy/` 目录
    - 创建 `config/`, `data/`, `output/` 子目录
    - 创建 `requirements.txt` 依赖文件
    - 创建 `config.yaml` 默认配置文件
    - _Requirements: 10.1_

  - [x] 1.2 定义核心数据类型和配置类
    - 创建 `models.py` 定义 FilterConfig, RiskConfig, SectorHeat, PressureLevel, MarketEmotion, BacktestResult 数据类
    - _Requirements: 2.1-2.6, 8.1-8.2_

  - [x] 1.3 编写配置保存加载的属性测试

    - **Property 20: 配置保存加载往返一致性**
    - **Validates: Requirements 10.5**

- [x] 2. 数据采集模块
  - [x] 2.1 实现数据采集接口 DataCollector
    - 创建 `data_collector.py`
    - 实现 `fetch_auction_data()` 获取竞价数据
    - 实现 `fetch_daily_data()` 获取日线数据
    - 实现 `fetch_sector_data()` 获取板块数据
    - 实现 `fetch_limit_up_data()` 获取涨跌停数据
    - _Requirements: 1.1, 1.2_

  - [x] 2.2 实现数据清洗和异常处理
    - 排除ST股票和次新股
    - 处理除权除息数据
    - 识别复牌首日个股
    - 处理异常值
    - _Requirements: 2.5, 2.6, 9.1, 9.5, 9.6_

- [x] 3. 指标计算模块
  - [x] 3.1 实现竞价指标计算 IndicatorCalculator
    - 创建 `indicator_calculator.py`
    - 实现 `calc_auction_spread()` 计算竞价价差
    - 实现 `calc_auction_turnover()` 计算竞价换手率
    - 实现 `calc_next_day_premium()` 计算次日溢价
    - 实现 `is_limit_up_open()` 判断涨停开盘
    - _Requirements: 1.3, 1.4, 1.5, 6.2_

  - [x] 3.2 编写竞价指标计算的属性测试

    - **Property 1: 竞价指标计算正确性**
    - **Validates: Requirements 1.3, 1.4**

  - [x] 3.3 编写次日溢价计算的属性测试

    - **Property 10: 次日溢价计算正确性**
    - **Validates: Requirements 6.2**

  - [x] 3.4 编写涨停开盘标记的属性测试

    - **Property 21: 涨停开盘标记正确性**
    - **Validates: Requirements 1.5**

- [x] 4. 检查点 - 确保基础模块测试通过
  - 确保所有测试通过，如有问题请询问用户

- [x] 5. 筛选引擎模块
  - [x] 5.1 实现多维度筛选引擎 FilterEngine
    - 创建 `filter_engine.py`
    - 实现 `apply_basic_filters()` 基础筛选（市值、上市天数、ST）
    - 实现 `apply_auction_filters()` 竞价指标筛选
    - 实现 `apply_spread_ranking()` 价差排名筛选
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 5.2 编写筛选条件一致性的属性测试

    - **Property 2: 筛选条件一致性**
    - **Validates: Requirements 2.2, 2.3, 2.4, 2.5, 2.6**

  - [x] 5.3 编写排名筛选正确性的属性测试

    - **Property 3: 排名筛选正确性**
    - **Validates: Requirements 2.1**

- [x] 6. 题材热度分析模块
  - [x] 6.1 实现题材热度分析 SectorAnalyzer
    - 创建 `sector_analyzer.py`
    - 实现 `get_stock_sectors()` 获取个股所属板块
    - 实现 `calc_limit_up_count()` 计算板块涨停家数
    - 实现 `calc_limit_up_trend()` 计算涨停趋势
    - 实现 `analyze_sector_heat()` 分析板块热度等级
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 6.2 编写板块热度分类的属性测试

    - **Property 4: 板块热度分类正确性**
    - **Validates: Requirements 3.4, 3.5**

  - [x] 6.3 编写涨停趋势计算的属性测试

    - **Property 5: 涨停趋势计算正确性**
    - **Validates: Requirements 3.3**

- [x] 7. 技术压力分析模块
  - [x] 7.1 实现技术压力分析 PressureAnalyzer
    - 创建 `pressure_analyzer.py`
    - 实现 `calc_dense_zone()` 计算成交密集区
    - 实现 `calc_distance_to_high()` 计算距离前高百分比
    - 实现 `analyze_pressure()` 分析压力等级
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 7.2 编写压力等级分类的属性测试

    - **Property 6: 压力等级分类正确性**
    - **Validates: Requirements 4.3, 4.4**

  - [x] 7.3 编写成交密集区计算的属性测试

    - **Property 7: 成交密集区计算正确性**
    - **Validates: Requirements 4.2**

- [x] 8. 市场情绪分析模块
  - [x] 8.1 实现市场情绪分析 MarketEmotionAnalyzer
    - 创建 `market_emotion_analyzer.py`
    - 实现 `calc_emotion_score()` 计算情绪得分
    - 实现 `classify_emotion()` 分类情绪等级
    - 实现 `is_extreme_market()` 判断极端市场
    - 实现 `analyze_emotion()` 综合分析
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6, 9.3_

  - [x] 8.2 编写市场情绪分类的属性测试

    - **Property 8: 市场情绪分类正确性**
    - **Validates: Requirements 5.3, 5.4, 5.5, 5.6**

  - [x] 8.3 编写极端市场识别的属性测试

    - **Property 18: 极端市场识别正确性**
    - **Validates: Requirements 9.3, 9.4**

- [x] 9. 连板高度计算
  - [x] 9.1 实现连板高度计算功能
    - 在 `indicator_calculator.py` 中添加 `calc_board_height()` 方法
    - _Requirements: 5.1_

  - [x] 9.2 编写连板高度计算的属性测试

    - **Property 9: 连板高度计算正确性**
    - **Validates: Requirements 5.1**

- [x] 10. 检查点 - 确保分析模块测试通过
  - 确保所有测试通过，如有问题请询问用户

- [x] 11. 风控模块
  - [x] 11.1 实现风险控制 RiskController
    - 创建 `risk_controller.py`
    - 实现 `check_position_limit()` 检查持仓限制
    - 实现 `check_stop_loss()` 检查止损条件
    - 实现 `check_take_profit()` 检查止盈条件
    - 实现 `update_consecutive_loss()` 更新连续亏损
    - 实现 `should_pause_strategy()` 判断是否暂停
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [x] 11.2 编写止盈止损信号的属性测试

    - **Property 13: 止盈止损信号正确性**
    - **Validates: Requirements 8.3, 8.4**

  - [x] 11.3 编写选股数量限制的属性测试

    - **Property 14: 选股数量限制正确性**
    - **Validates: Requirements 8.1**

  - [x] 11.4 编写连续亏损计数的属性测试

    - **Property 15: 连续亏损计数正确性**
    - **Validates: Requirements 8.6, 8.7**

  - [x] 11.5 编写弱势市场行为的属性测试

    - **Property 16: 弱势市场行为正确性**
    - **Validates: Requirements 5.7, 8.5**

- [x] 12. 回测引擎模块
  - [x] 12.1 实现回测引擎 BacktestEngine
    - 创建 `backtest_engine.py`
    - 实现 `run_backtest()` 执行回测
    - 实现 `calc_win_rate()` 计算胜率
    - 实现 `calc_avg_premium()` 计算平均溢价
    - 实现 `calc_max_drawdown()` 计算最大回撤
    - 实现 `calc_profit_loss_ratio()` 计算盈亏比
    - _Requirements: 6.1, 6.3, 6.4, 6.5, 6.7_

  - [x] 12.2 编写胜率计算的属性测试

    - **Property 11: 胜率计算正确性**
    - **Validates: Requirements 6.3**

  - [x] 12.3 编写绩效指标计算的属性测试

    - **Property 12: 绩效指标计算正确性**
    - **Validates: Requirements 6.4, 6.5**

- [x] 13. 综合评分与排序
  - [x] 13.1 实现综合评分和排序功能
    - 创建 `scorer.py`
    - 实现 `calc_composite_score()` 计算综合评分
    - 实现 `rank_candidates()` 排序候选股票
    - 实现 `add_risk_warnings()` 添加风险提示
    - _Requirements: 7.1, 7.2, 7.5_

  - [x] 13.2 编写综合评分排序的属性测试

    - **Property 23: 综合评分排序正确性**
    - **Validates: Requirements 7.2**

  - [x] 13.3 编写输出字段完整性的属性测试

    - **Property 22: 输出字段完整性**
    - **Validates: Requirements 7.1, 7.5**

- [x] 14. 检查点 - 确保核心功能测试通过
  - 确保所有测试通过，如有问题请询问用户

- [x] 15. 输出与可视化模块
  - [x] 15.1 实现报表生成和导出功能
    - 创建 `reporter.py`
    - 实现 `generate_daily_report()` 生成每日报告
    - 实现 `generate_backtest_report()` 生成回测报告
    - 实现 `export_to_excel()` 导出Excel
    - _Requirements: 7.1, 7.3, 7.4_

- [x] 16. 参数优化模块
  - [x] 16.1 实现参数网格搜索功能
    - 创建 `optimizer.py`
    - 实现 `grid_search()` 参数网格搜索
    - 实现 `compare_results()` 对比分析
    - 实现 `save_best_config()` 保存最优配置
    - _Requirements: 10.2, 10.3, 10.4_

- [x] 17. 主程序集成
  - [x] 17.1 实现主程序入口
    - 创建 `auction_strategy/main.py`
    - 集成所有模块（DataCollector, IndicatorCalculator, FilterEngine, SectorAnalyzer, PressureAnalyzer, MarketEmotionAnalyzer, Scorer, BacktestEngine, RiskController, Reporter, Optimizer）
    - 实现命令行参数解析（使用argparse）
    - 实现日常筛选模式：获取当日竞价数据，执行筛选，输出候选股票
    - 实现回测模式：指定日期范围，执行历史回测，输出绩效报告
    - 实现参数优化模式：执行网格搜索，保存最优配置
    - _Requirements: 6.1, 6.6, 10.1_

  - [x] 17.2 创建批处理脚本
    - 创建 `auction_strategy/run_daily.bat` 每日筛选脚本
    - 创建 `auction_strategy/run_backtest.bat` 回测脚本
    - 创建 `auction_strategy/run_optimize.bat` 参数优化脚本
    - _Requirements: 6.1, 10.2_

- [x] 18. 最终检查点 - 确保所有测试通过
  - 运行完整测试套件确保所有116个测试通过
  - 验证所有模块正确集成
  - 确保命令行工具可正常运行
  - 如有问题请询问用户

## 备注

- 标记 `*` 的任务为可选任务，可跳过以加快MVP开发
- 每个任务都引用了具体的需求编号以便追溯
- 检查点用于确保增量验证
- 属性测试验证通用正确性属性
- 单元测试验证具体示例和边界情况
