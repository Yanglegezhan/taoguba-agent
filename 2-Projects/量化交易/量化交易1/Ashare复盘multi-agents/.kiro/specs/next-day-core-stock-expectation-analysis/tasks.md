# 实现计划：次日核心个股超预期分析系统

## 概述

本实现计划将设计转化为可执行的编码任务。系统采用Python 3.9+实现，使用Gemini-2.0-Flash作为LLM，通过三个独立Agent协作完成从数据沉淀到决策导航的全流程。

## 任务列表

- [ ] 1. 项目基础设施搭建
  - 创建项目目录结构
  - 配置Python虚拟环境和依赖管理（requirements.txt）
  - 设置配置文件模板（YAML格式）
  - 配置日志系统
  - _需求: 0, 20, 21, 22, 23_

- [ ]* 1.1 编写项目配置Schema验证
  - 使用pydantic定义配置数据模型
  - 实现配置文件加载和验证
  - _需求: 20.1, 23.8_

- [ ] 2. 数据源集成层实现
  - [ ] 2.1 实现Kaipanla API客户端
    - 编写KaipanlaClient类
    - 实现行情数据获取接口
    - 实现竞价数据获取接口
    - _需求: 0.1, 1.1, 7.1_

  - [ ] 2.2 实现AKShare API客户端（含代理配置）
    - 编写AKShareClient类
    - 实现代理配置自动应用
    - 实现数据获取接口
    - _需求: 0.2, 0.3_

  - [ ] 2.3 实现东方财富API客户端
    - 编写EastmoneyClient类
    - 实现数据获取接口
    - _需求: 0.4_

  - [ ] 2.4 实现数据源管理器（降级逻辑）
    - 编写DataSourceManager类
    - 实现数据源优先级配置
    - 实现自动降级逻辑
    - 实现数据来源记录
    - _需求: 0.5, 0.6, 0.7_

- [ ]* 2.5 编写数据源集成测试
  - 测试Kaipanla数据获取
  - 测试AKShare代理配置和数据获取
  - 测试数据源降级逻辑
  - **Property 1: 数据源降级一致性**
  - **Property 2: 代理配置自动应用**
  - _需求: 0.3, 0.5, 0.6_

- [ ] 3. 核心数据模型实现
  - [ ] 3.1 定义基础数据类
    - 使用dataclass定义Stock、TechnicalLevels
    - 定义GenePool、BaselineExpectation
    - 定义AuctionData、ExpectationScore
    - 定义AdditionalPool、StatusScore
    - 定义SignalPlaybook、DecisionTree、NavigationReport
    - _需求: 23.1, 23.2_

  - [ ] 3.2 实现数据序列化和反序列化
    - 实现JSON序列化方法
    - 实现JSON反序列化方法
    - _需求: 23.3, 23.4, 23.5_

  - [ ] 3.3 定义JSON Schema文件
    - 编写gene_pool_schema.json
    - 编写baseline_expectation_schema.json
    - 编写decision_navigation_schema.json
    - _需求: 23.8_

- [ ]* 3.4 编写数据格式验证测试
  - 测试JSON Schema验证
  - 测试数据序列化/反序列化
  - **Property 3: 数据格式符合Schema**
  - _需求: 23.8, 23.9, 23.10_

- [ ] 4. 数据存储层实现
  - [ ] 4.1 实现文件存储管理器
    - 编写FileStorageManager类
    - 实现文件命名规范
    - 实现目录结构管理
    - _需求: 23.6, 23.7_

  - [ ] 4.2 实现SQLite数据库管理器
    - 创建数据库Schema
    - 编写DatabaseManager类
    - 实现数据插入和查询接口
    - _需求: 17.1-17.5_

- [ ]* 4.3 编写数据持久化测试
  - 测试文件存储和读取
  - 测试数据库存储和查询
  - **Property 4: 数据持久化一致性**
  - _需求: 1.5, 2.6, 3.7, 17.1-17.4_

- [ ] 5. LLM集成层实现
  - [ ] 5.1 实现Gemini客户端
    - 编写GeminiClient类
    - 实现API调用接口
    - 实现参数配置（温度、max_tokens等）
    - _需求: 22.1, 22.2, 22.3_

  - [ ] 5.2 实现LLM调用重试和错误处理
    - 实现重试机制（最多3次）
    - 实现超时处理
    - 实现错误日志记录
    - _需求: 22.4, 22.5, 22.6, 22.7_

  - [ ] 5.3 实现规则引擎降级方案
    - 编写RuleBasedEngine类
    - 实现基础分析规则
    - _需求: 22.8_

- [ ]* 5.4 编写LLM集成测试
  - 测试Gemini API调用
  - 测试重试机制
  - 测试降级方案
  - **Property 25: LLM调用重试**
  - _需求: 22.5, 22.8_

- [ ] 6. Stage1 Agent - 数据沉淀与复盘
  - [ ] 6.1 实现报告生成器
    - 编写ReportGenerator类
    - 实现generate_market_report方法
    - 实现generate_emotion_report方法
    - 实现generate_theme_report方法
    - 集成现有的Ashare复盘agents
    - _需求: 1.2, 1.3, 1.4, 1.6_

  - [ ] 6.2 实现基因池构建器
    - 编写GenePoolBuilder类
    - 实现scan_continuous_limit_up方法（识别连板梯队）
    - 实现identify_failed_limit_up方法（识别炸板股）
    - 实现identify_recognition_stocks方法（识别辨识度个股）
    - 实现identify_trend_stocks方法（识别趋势股）
    - 实现build_gene_pool方法
    - _需求: 2.1-2.7_

  - [ ] 6.3 实现技术指标计算器
    - 编写TechnicalCalculator类
    - 实现calculate_moving_averages方法（计算5/10/20日均线）
    - 实现identify_previous_highs方法（识别前期高点）
    - 实现calculate_chip_concentration方法（计算筹码密集区）
    - 实现calculate_distance_percentages方法（计算距离百分比）
    - _需求: 3.1-3.7_

  - [ ] 6.4 实现Stage1 Agent主流程
    - 编写Stage1Agent类
    - 实现run方法（协调各模块）
    - 实现数据读取和存储
    - 实现错误处理
    - _需求: 1.1, 1.5, 21.1_

- [ ]* 6.5 编写Stage1 Agent单元测试
  - 测试报告生成
  - 测试基因池构建
  - 测试技术指标计算
  - **Property 5: 基因池完整性**
  - **Property 6: 技术指标计算正确性**
  - _需求: 2.1-2.7, 3.1-3.7_

- [ ]* 6.6 编写Stage1 Agent集成测试
  - 测试完整流程（端到端）
  - 测试输出文件格式
  - _需求: 1.1-1.6, 2.1-2.7, 3.1-3.7_

- [ ] 7. Stage2 Agent - 早盘策略校准
  - [ ] 7.1 实现隔夜数据采集器
    - 编写OvernightDataCollector类
    - 实现fetch_us_stock_data方法（获取美股数据）
    - 实现fetch_futures_data方法（获取期货数据）
    - 实现fetch_news_headlines方法（获取新闻头条）
    - 实现fetch_policy_announcements方法（获取政策公告）
    - _需求: 4.1-4.7_

  - [ ] 7.2 实现基准预期引擎
    - 编写BaselineExpectationEngine类
    - 实现calculate_baseline方法（计算基准预期）
    - 实现adjust_for_theme_status方法（根据题材状态调整）
    - 集成LLM进行智能分析
    - _需求: 5.1-5.7_

  - [ ] 7.3 实现新题材检测器
    - 编写NewThemeDetector类
    - 实现detect_new_themes方法（检测新题材）
    - 实现find_related_stocks方法（查找相关个股）
    - 集成LLM进行题材识别
    - _需求: 6.1-6.6_

  - [ ] 7.4 实现Stage2 Agent主流程
    - 编写Stage2Agent类
    - 实现run方法（协调各模块）
    - 实现数据读取和存储
    - 实现错误处理
    - _需求: 4.8, 5.7, 21.2_

- [ ]* 7.5 编写Stage2 Agent单元测试
  - 测试隔夜数据采集
  - 测试基准预期计算
  - 测试新题材检测
  - **Property 7: 基准预期合理性**
  - **Property 8: 基准预期条件调整**
  - _需求: 5.1-5.7_

- [ ]* 7.6 编写Stage2 Agent集成测试
  - 测试完整流程（端到端）
  - 测试输出文件格式
  - _需求: 4.1-4.8, 5.1-5.7, 6.1-6.6_

- [ ] 8. Stage3 Agent - 竞价轨迹监测（基础监测）
  - [ ] 8.1 实现竞价监测器
    - 编写AuctionMonitor类
    - 实现monitor_withdrawal_behavior方法（监测撤单行为）
    - 实现monitor_price_trajectory方法（监测价格轨迹）
    - 实现get_final_snapshot方法（获取最终快照）
    - _需求: 7.1-7.6, 8.1-8.7, 10.1-10.6_

  - [ ] 8.2 实现超预期分值计算器
    - 编写ExpectationScoreCalculator类
    - 实现calculate_volume_score方法（计算量能分值）
    - 实现calculate_price_score方法（计算价格分值）
    - 实现calculate_independence_score方法（计算独立性分值）
    - 实现calculate_total_score方法（计算总分）
    - _需求: 11.1-11.6, 12.1-12.6, 13.1-13.6, 14.1-14.6_

  - [ ] 8.3 实现板块联动监测器
    - 编写SectorMonitor类
    - 实现monitor_sector_linkage方法（监测板块联动）
    - 实现detect_positioning_signal方法（检测卡位信号）
    - _需求: 9.1-9.6_

- [ ]* 8.4 编写竞价监测单元测试
  - 测试撤单行为识别
  - 测试价格轨迹评级
  - 测试超预期分值计算
  - **Property 9: 竞价数据完整性**
  - **Property 10: 撤单行为识别**
  - **Property 11: 超预期分值范围**
  - **Property 12: 超预期分值单调性**
  - _需求: 7.1-7.6, 11.1-11.6, 12.1-12.6, 13.1-13.6, 14.1-14.6_

- [ ] 9. Stage3 Agent - 附加票池构建
  - [ ] 9.1 实现附加池构建器
    - 编写AdditionalPoolBuilder类
    - 实现scan_top_seals方法（扫描顶级封单）
    - 实现scan_rush_positioning方法（扫描急迫抢筹）
    - 实现scan_energy_burst方法（扫描能量爆发）
    - 实现scan_reverse_nuclear方法（扫描极端反核）
    - 实现scan_sector_formation方法（扫描板块阵型）
    - _需求: 15A.1-15A.8, 15B.1-15B.7, 15C.1-15C.8, 15D.1-15D.8, 15E.1-15E.7_

  - [ ] 9.2 实现地位判定引擎
    - 编写StatusJudgmentEngine类
    - 实现calculate_theme_recognition_score方法（计算题材辨识度）
    - 实现calculate_urgency_score方法（计算量价急迫性）
    - 实现calculate_emotion_hedge_score方法（计算情绪对冲力）
    - 实现calculate_status_score方法（计算总分）
    - 实现filter_top_candidates方法（筛选前5）
    - _需求: 15F.1-15F.7, 15F1.1-15F1.8, 15F2.1-15F2.9, 15F3.1-15F3.9_

- [ ]* 9.3 编写附加池构建测试
  - 测试各维度筛选逻辑
  - 测试地位分值计算
  - 测试最终候选筛选
  - **Property 13: 附加池筛选条件**
  - **Property 14: 地位分值计算**
  - **Property 15: 最终附加池筛选**
  - _需求: 15A.5, 15B.4, 15C.5, 15D.5, 15E.3, 15F.5, 15F.6_

- [ ] 10. Stage3 Agent - 决策导航引擎
  - [ ] 10.1 实现决策导航引擎
    - 编写DecisionNavigationEngine类
    - 实现generate_baseline_table方法（生成及格线表）
    - 实现generate_signal_playbooks方法（生成信号剧本）
    - 实现generate_decision_tree方法（生成决策树）
    - 实现generate_navigation_report方法（生成导航报告）
    - _需求: 15G.1-15G.6_

  - [ ] 10.2 实现剧本生成器
    - 实现generate_rush_positioning_playbook方法（暴力抢筹剧本）
    - 实现generate_reverse_nuclear_playbook方法（极弱转强剧本）
    - 集成LLM进行剧本生成
    - _需求: 15G2.1-15G2.7, 15G2A.1-15G2A.7, 15G2B.1-15G2B.6_

  - [ ] 10.3 实现场景判定器
    - 实现identify_current_scenario方法（识别当前场景）
    - 实现generate_scenario_strategy方法（生成场景策略）
    - 集成LLM进行场景分析
    - _需求: 15G3.1-15G3.7, 15G3A.1-15G3A.5, 15G3B.1-15G3B.5, 15G3C.1-15G3C.6_

  - [ ] 10.4 实现Stage3 Agent主流程
    - 编写Stage3Agent类
    - 实现run方法（协调各模块）
    - 实现数据读取和存储
    - 实现错误处理
    - _需求: 21.3_

- [ ]* 10.5 编写决策导航引擎测试
  - 测试及格线表生成
  - 测试剧本触发逻辑
  - 测试场景判定
  - **Property 16: 决策导航报告完整性**
  - **Property 17: 及格线判定一致性**
  - **Property 18: 剧本触发条件**
  - **Property 19: 场景判定唯一性**
  - _需求: 15G.2, 15G.3, 15G1.5, 15G1.6, 15G2.5, 15G3.1-15G3.6_

- [ ]* 10.6 编写Stage3 Agent集成测试
  - 测试完整流程（端到端）
  - 测试输出文件格式
  - _需求: 7.1-15G3C.6_

- [ ] 11. 报告生成与推送模块
  - [ ] 11.1 实现报告生成器
    - 编写ReportGenerator类
    - 实现generate_html_report方法（生成HTML报告）
    - 实现generate_excel_report方法（生成Excel报告）
    - _需求: 16.1-16.9_

  - [ ] 11.2 实现推送模块
    - 编写NotificationManager类
    - 实现send_wechat_notification方法（企业微信推送）
    - 实现send_email_notification方法（邮件推送）
    - 实现check_push_conditions方法（检查推送条件）
    - _需求: 19.1-19.6_

- [ ]* 11.3 编写报告生成和推送测试
  - 测试报告生成
  - 测试推送触发条件
  - **Property 20: 报告生成时效性**
  - **Property 22: 推送触发条件**
  - _需求: 16.1, 19.2-19.4_

- [ ] 12. 异常处理和数据验证
  - [ ] 12.1 实现数据验证器
    - 编写DataValidator类
    - 实现validate_market_data方法（验证市场数据）
    - 实现validate_json_schema方法（验证JSON格式）
    - 实现generate_error_message方法（生成错误提示）
    - _需求: 23.9, 23.10_

  - [ ] 12.2 实现异常情况处理器
    - 编写ExceptionHandler类
    - 实现handle_suspension方法（处理停牌）
    - 实现handle_major_announcement方法（处理重大公告）
    - 实现handle_extreme_market方法（处理极端市场）
    - _需求: 18.1-18.6_

- [ ]* 12.3 编写异常处理测试
  - 测试各类异常情况识别
  - 测试数据验证
  - 测试错误提示
  - **Property 21: 异常情况正确处理**
  - **Property 26: 数据验证错误提示**
  - _需求: 18.1-18.6, 23.10, 0.8_

- [ ] 13. Agent独立性和协作测试
  - [ ] 13.1 实现Agent独立运行测试
    - 测试Stage1独立运行
    - 测试Stage2独立运行
    - 测试Stage3独立运行
    - **Property 23: Agent独立运作**
    - _需求: 21.1-21.3, 21.6_

  - [ ] 13.2 实现Agent失败隔离测试
    - 测试Stage1失败时Stage2/3的降级
    - 测试Stage2失败时Stage3的降级
    - **Property 24: Agent失败隔离**
    - _需求: 21.5_

  - [ ] 13.3 实现Agent协作流程测试
    - 测试完整的三阶段流水线
    - 测试数据传递正确性
    - _需求: 21.4, 23.4, 23.5_

- [ ] 14. 配置管理和参数优化
  - [ ] 14.1 实现配置管理器
    - 编写ConfigManager类
    - 实现load_config方法（加载配置）
    - 实现validate_config方法（验证配置）
    - 实现save_config方法（保存配置）
    - _需求: 20.1, 20.6, 20.7_

  - [ ] 14.2 创建配置文件模板
    - 创建system_config.yaml模板
    - 创建agent_config.yaml模板
    - 创建data_source_config.yaml模板
    - 添加配置说明文档
    - _需求: 20.6_

- [ ] 15. 文档和部署
  - [ ] 15.1 编写用户文档
    - 编写README.md（项目介绍和快速开始）
    - 编写INSTALL.md（安装指南）
    - 编写CONFIG.md（配置说明）
    - 编写API.md（API文档）

  - [ ] 15.2 编写开发者文档
    - 编写ARCHITECTURE.md（架构说明）
    - 编写CONTRIBUTING.md（贡献指南）
    - 添加代码注释和docstring

  - [ ] 15.3 准备部署脚本
    - 编写启动脚本（start_stage1.sh, start_stage2.sh, start_stage3.sh）
    - 编写定时任务配置（crontab示例）
    - 编写Docker配置（可选）

- [ ] 16. 最终集成测试和验证
  - 确保所有单元测试通过
  - 确保所有集成测试通过
  - 使用历史数据进行端到端测试
  - 验证所有Property
  - 验证报告生成质量

## 注意事项

- 任务标记`*`的为可选任务（主要是测试相关），可以根据时间安排决定是否实施
- 每个任务都标注了相关的需求编号，实现时请参考需求文档
- Property测试任务标注了对应的正确性属性，需要编写property-based tests
- 建议按顺序执行任务，确保依赖关系正确
- 每完成一个主要模块（如Stage1 Agent），建议进行checkpoint测试

## Checkpoint建议

- **Checkpoint 1**（任务1-5完成后）：验证基础设施、数据源、数据模型、存储层、LLM集成是否正常工作
- **Checkpoint 2**（任务6完成后）：验证Stage1 Agent能否正常生成报告和基因池
- **Checkpoint 3**（任务7完成后）：验证Stage2 Agent能否正常生成基准预期
- **Checkpoint 4**（任务10完成后）：验证Stage3 Agent能否正常生成决策导航报告
- **Checkpoint 5**（任务16完成后）：验证整个系统的端到端流程

