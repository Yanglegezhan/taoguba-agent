# 存储层实现文档

## 概述

本文档描述了任务4（数据存储层实现）的完成情况，包括文件存储管理器和SQLite数据库管理器的实现。

## 实现内容

### 4.1 文件存储管理器 (FileStorageManager)

**文件位置**: `src/storage/file_storage_manager.py`

**功能特性**:

1. **目录结构管理**
   - 自动创建标准目录结构：
     - `data/config/` - 配置文件
     - `data/stage1_output/` - Stage1输出
     - `data/stage2_output/` - Stage2输出
     - `data/stage3_output/` - Stage3输出
     - `data/historical/` - 历史归档
     - `data/logs/` - 日志文件

2. **文件命名规范**
   - 统一的文件命名模板：`{type}_{date}.json`
   - 支持的文件类型：
     - gene_pool - 基因池
     - market_report - 大盘报告
     - emotion_report - 情绪报告
     - theme_report - 题材报告
     - overnight_variables - 隔夜变量
     - baseline_expectation - 基准预期
     - new_themes - 新题材
     - auction_monitoring - 竞价监测
     - additional_pool - 附加票池
     - decision_navigation - 决策导航
     - daily_report - 每日报告

3. **核心方法**
   ```python
   # 获取文件路径
   get_file_path(file_type, date, stage=None) -> Path
   
   # 保存JSON数据
   save_json(data, file_type, date, stage=None) -> str
   
   # 加载JSON数据
   load_json(file_type, date, stage=None) -> Dict
   
   # 检查文件是否存在
   file_exists(file_type, date, stage=None) -> bool
   
   # 专用保存/加载方法
   save_gene_pool(gene_pool) -> str
   load_gene_pool(date) -> GenePool
   save_baseline_expectations(expectations, date) -> str
   load_baseline_expectations(date) -> Dict[str, BaselineExpectation]
   save_navigation_report(report) -> str
   load_navigation_report(date) -> NavigationReport
   save_additional_pool(pool) -> str
   load_additional_pool(date) -> AdditionalPool
   
   # 文件管理
   list_files(file_type, stage=None) -> List[str]
   get_latest_file(file_type, stage=None) -> Optional[str]
   archive_old_files(days_to_keep=30) -> int
   cleanup_old_files(days_to_keep=90) -> int
   
   # 统计信息
   get_storage_stats() -> Dict[str, Any]
   ```

4. **使用示例**
   ```python
   from src.storage import FileStorageManager
   from src.common.models import GenePool
   
   # 初始化
   storage = FileStorageManager(base_dir='data')
   
   # 保存基因池
   gene_pool = GenePool(date='20250213', ...)
   filepath = storage.save_gene_pool(gene_pool)
   
   # 加载基因池
   loaded_pool = storage.load_gene_pool('20250213')
   
   # 检查文件是否存在
   if storage.file_exists('gene_pool', '20250213'):
       print("文件存在")
   
   # 归档旧文件（保留最近30天）
   archived_count = storage.archive_old_files(days_to_keep=30)
   ```

### 4.2 SQLite数据库管理器 (DatabaseManager)

**文件位置**: `src/storage/database_manager.py`

**功能特性**:

1. **数据库Schema**
   - `gene_pool_history` - 基因池历史表
   - `baseline_expectation_history` - 基准预期历史表
   - `auction_monitoring_history` - 竞价监测结果表
   - `additional_pool_history` - 附加池历史表

2. **基因池历史表结构**
   ```sql
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
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       UNIQUE(date, stock_code, category)
   );
   ```

3. **基准预期历史表结构**
   ```sql
   CREATE TABLE baseline_expectation_history (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       date TEXT NOT NULL,
       stock_code TEXT NOT NULL,
       stock_name TEXT,
       expected_open_min REAL,
       expected_open_max REAL,
       expected_amount_min REAL,
       logic TEXT,
       confidence REAL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       UNIQUE(date, stock_code)
   );
   ```

4. **竞价监测结果表结构**
   ```sql
   CREATE TABLE auction_monitoring_history (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       date TEXT NOT NULL,
       stock_code TEXT NOT NULL,
       stock_name TEXT,
       open_price REAL,
       auction_amount REAL,
       auction_volume REAL,
       seal_amount REAL,
       withdrawal_detected INTEGER,  -- 0 or 1
       trajectory_rating TEXT,
       volume_score REAL,
       price_score REAL,
       independence_score REAL,
       expectation_score REAL,
       recommendation TEXT,
       confidence REAL,
       actual_performance TEXT,  -- JSON格式，用于回测
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       UNIQUE(date, stock_code)
   );
   ```

5. **附加池历史表结构**
   ```sql
   CREATE TABLE additional_pool_history (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       date TEXT NOT NULL,
       stock_code TEXT NOT NULL,
       stock_name TEXT,
       pool_type TEXT,  -- top_seals, rush_positioning, etc.
       theme_recognition REAL,
       urgency REAL,
       emotion_hedge REAL,
       status_score REAL,
       rank INTEGER,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       UNIQUE(date, stock_code, pool_type)
   );
   ```

6. **核心方法**
   ```python
   # 基因池操作
   insert_gene_pool(gene_pool) -> int
   query_gene_pool(date=None, stock_code=None, category=None, limit=100) -> List[Dict]
   
   # 基准预期操作
   insert_baseline_expectations(expectations, date) -> int
   query_baseline_expectations(date=None, stock_code=None, limit=100) -> List[Dict]
   
   # 竞价监测操作
   insert_auction_monitoring(date, stock_code, stock_name, auction_data, expectation_score) -> int
   query_auction_monitoring(date=None, stock_code=None, min_score=None, recommendation=None, limit=100) -> List[Dict]
   update_actual_performance(date, stock_code, performance_data) -> bool
   
   # 附加池操作
   insert_additional_pool(date, stock, pool_type, status_score) -> int
   query_additional_pool(date=None, stock_code=None, pool_type=None, min_score=None, limit=100) -> List[Dict]
   
   # 统计分析
   get_stock_history(stock_code, start_date=None, end_date=None) -> Dict[str, List[Dict]]
   get_recommendation_accuracy(start_date=None, end_date=None) -> Dict[str, Any]
   get_database_stats() -> Dict[str, Any]
   
   # 数据库维护
   vacuum() -> None
   close() -> None
   ```

7. **使用示例**
   ```python
   from src.storage import DatabaseManager
   from src.common.models import GenePool, BaselineExpectation
   
   # 初始化（支持上下文管理器）
   with DatabaseManager(db_path='data/historical/gene_pool_history.db') as db:
       # 插入基因池
       gene_pool = GenePool(date='20250213', ...)
       count = db.insert_gene_pool(gene_pool)
       
       # 查询基因池
       results = db.query_gene_pool(date='20250213', category='continuous_limit_up')
       
       # 插入基准预期
       expectations = {'002810': BaselineExpectation(...)}
       db.insert_baseline_expectations(expectations, '20250213')
       
       # 查询个股历史
       history = db.get_stock_history('002810', start_date='20250201', end_date='20250213')
       
       # 获取统计信息
       stats = db.get_database_stats()
   ```

## 测试覆盖

**测试文件**: `tests/test_storage.py`

### FileStorageManager测试
- ✅ 目录结构创建
- ✅ 文件路径获取
- ✅ 基因池保存和加载
- ✅ 基准预期保存和加载
- ✅ 文件存在性检查
- ✅ 文件列表
- ✅ 存储统计

### DatabaseManager测试
- ✅ 数据库初始化
- ✅ 基因池插入和查询
- ✅ 基准预期插入和查询
- ✅ 竞价监测插入和查询
- ✅ 数据库统计

**测试结果**: 12个测试全部通过 ✅

## 需求验证

### 需求23.6 - 文件命名规范
✅ 实现了统一的文件命名模板，格式为 `{type}_{date}.json`

### 需求23.7 - 目录结构管理
✅ 实现了标准的目录结构，包括各阶段输出目录和历史归档目录

### 需求17.1 - 基因池历史存储
✅ 实现了基因池历史表，支持按日期、股票代码、类别查询

### 需求17.2 - 基准预期历史存储
✅ 实现了基准预期历史表，支持按日期、股票代码查询

### 需求17.3 - 竞价监测结果存储
✅ 实现了竞价监测历史表，支持按日期、股票代码、分值、建议查询

### 需求17.4 - 操作建议和实际表现存储
✅ 实现了actual_performance字段，支持后续回测分析

### 需求17.5 - 历史数据查询
✅ 实现了多维度查询接口，支持按日期、个股、题材等维度查询

## 设计决策

1. **文件存储 vs 数据库存储**
   - 文件存储：用于Agent间数据传递，便于调试和人工查看
   - 数据库存储：用于历史数据积累，便于统计分析和回测

2. **目录结构设计**
   - 按Stage分离输出目录，便于独立管理
   - 历史目录用于归档，避免主目录文件过多

3. **数据库Schema设计**
   - 使用UNIQUE约束防止重复插入
   - 创建索引优化查询性能
   - 使用JSON字段存储复杂数据（technical_data, actual_performance）

4. **错误处理**
   - 文件操作失败时抛出异常
   - 数据库操作失败时记录日志并返回失败标识
   - 支持上下文管理器自动关闭连接

## 后续优化建议

1. **性能优化**
   - 考虑使用批量插入提高数据库写入性能
   - 添加数据库连接池支持并发访问

2. **功能扩展**
   - 添加数据备份和恢复功能
   - 实现数据导出为CSV/Excel功能
   - 添加数据完整性校验

3. **监控和维护**
   - 添加存储空间监控和告警
   - 实现自动清理过期数据
   - 添加数据库性能监控

## 使用注意事项

1. **文件存储**
   - 确保有足够的磁盘空间
   - 定期执行archive_old_files归档旧文件
   - 定期执行cleanup_old_files清理过期归档

2. **数据库存储**
   - 定期执行vacuum优化数据库
   - 注意关闭数据库连接，避免文件锁定
   - 使用上下文管理器确保连接正确关闭

3. **数据一致性**
   - 文件和数据库应保持同步
   - 建议在Agent完成后同时写入文件和数据库

## 总结

任务4（数据存储层实现）已完成，包括：
- ✅ 4.1 文件存储管理器实现
- ✅ 4.2 SQLite数据库管理器实现
- ✅ 完整的测试覆盖
- ✅ 所有相关需求验证通过

存储层为系统提供了可靠的数据持久化能力，支持Agent间数据传递和历史数据分析。
