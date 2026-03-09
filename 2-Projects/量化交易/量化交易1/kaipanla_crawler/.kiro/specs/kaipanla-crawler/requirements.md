# 需求文档：开盘啦APP数据爬虫

## 简介

本系统是一个Python爬虫程序，用于从开盘啦APP获取股票市场相关数据。由于开盘啦没有网页版，只有移动应用，系统需要通过抓包获取API接口信息，然后模拟APP请求来获取数据。

## 术语表

- **Crawler（爬虫）**: 自动化数据采集系统
- **API_Client（API客户端）**: 负责发送HTTP请求和处理响应的组件
- **Data_Parser（数据解析器）**: 负责解析API响应并转换为结构化数据的组件
- **Storage_Manager（存储管理器）**: 负责数据持久化的组件
- **Config_Manager（配置管理器）**: 负责管理API配置信息的组件
- **Logger（日志记录器）**: 负责记录系统运行日志的组件
- **抓包**: 通过网络监控工具（如Fiddler）捕获APP的网络请求，获取API接口信息

## 需求

### 需求 1：API配置管理

**用户故事**: 作为开发者，我希望能够灵活配置API接口信息，以便在抓包后快速更新爬虫配置。

#### 验收标准

1. THE Config_Manager SHALL 存储API基础URL、请求头模板、认证令牌和各板块的端点路径
2. WHEN 配置文件不存在或格式错误 THEN THE Config_Manager SHALL 抛出明确的配置错误异常
3. THE Config_Manager SHALL 支持从Python配置文件加载配置信息
4. WHEN 认证令牌被更新 THEN THE Config_Manager SHALL 立即应用新令牌到后续请求

### 需求 2：HTTP请求处理

**用户故事**: 作为系统，我需要可靠地发送HTTP请求并处理各种网络异常，以确保数据采集的稳定性。

#### 验收标准

1. WHEN 发送API请求 THEN THE API_Client SHALL 使用配置的请求头和认证信息
2. IF 请求失败 THEN THE API_Client SHALL 重试最多3次，每次重试前等待1秒
3. WHEN 所有重试都失败 THEN THE API_Client SHALL 抛出包含详细错误信息的异常
4. THE API_Client SHALL 支持GET和POST两种请求方法
5. WHEN 响应状态码不是2xx THEN THE API_Client SHALL 抛出HTTP错误异常
6. THE API_Client SHALL 设置30秒的请求超时时间

### 需求 3：用户认证

**用户故事**: 作为用户，我希望系统能够自动处理登录认证，以便获取需要登录才能访问的数据。

#### 验收标准

1. WHEN 提供用户名和密码 THEN THE API_Client SHALL 调用登录接口获取认证令牌
2. WHEN 登录成功 THEN THE API_Client SHALL 将令牌存储并应用到后续所有请求
3. IF 登录失败 THEN THE API_Client SHALL 返回失败状态和错误信息
4. THE API_Client SHALL 支持从配置文件读取用户凭据
5. THE API_Client SHALL 支持通过函数参数传入用户凭据

### 需求 4：市场情绪数据采集

**用户故事**: 作为用户，我希望获取市场情绪数据，以便分析当日市场整体表现。

#### 验收标准

1. WHEN 调用市场情绪采集函数 THEN THE Crawler SHALL 请求市场情绪API端点
2. THE Crawler SHALL 支持指定日期参数，默认为当天
3. WHEN API返回数据 THEN THE Data_Parser SHALL 解析并提取以下字段：
   - 日期、沪指、沪指涨跌、沪指涨跌幅
   - 实际量能、预测量能、量能增量
   - 一板/二板/三板/高度板数量
   - 一板/二板/三板连板率
   - 涨停破板率
   - 昨日涨停/连板/破板今日表现
4. THE Crawler SHALL 返回pandas DataFrame格式的数据
5. IF API请求失败 THEN THE Crawler SHALL 返回空DataFrame并记录错误日志

### 需求 5：复盘啦数据采集

**用户故事**: 作为用户，我希望获取复盘啦数据，以便了解各板块涨停股票和市场动向。

#### 验收标准

1. WHEN 调用复盘啦采集函数 THEN THE Crawler SHALL 请求复盘啦API端点
2. THE Crawler SHALL 支持指定日期参数，默认为当天
3. THE Crawler SHALL 支持指定分类参数：盘面梳理、市场动向、涨停原因
4. WHEN 分类为"涨停原因" THEN THE Data_Parser SHALL 解析并提取以下字段：
   - 日期、板块、板块涨停数
   - 股票代码、股票名称、涨停时间
   - 连板状态、实际流通市值、涨停原因
5. THE Crawler SHALL 返回pandas DataFrame格式的数据
6. IF API请求失败 THEN THE Crawler SHALL 返回空DataFrame并记录错误日志

### 需求 6：题材库数据采集

**用户故事**: 作为用户，我希望获取题材库数据，以便了解当前热门题材和涨停分布。

#### 验收标准

1. WHEN 调用题材库采集函数 THEN THE Crawler SHALL 请求题材库API端点
2. THE Crawler SHALL 支持按热度或涨幅排序
3. WHEN API返回数据 THEN THE Data_Parser SHALL 解析并提取以下字段：
   - 排序、题材名称、涨停数
   - 热度标签、涨幅
4. THE Crawler SHALL 返回pandas DataFrame格式的数据
5. IF API请求失败 THEN THE Crawler SHALL 返回空DataFrame并记录错误日志

### 需求 7：百日新高数据采集

**用户故事**: 作为用户，我希望获取创百日新高的股票列表，以便发现强势股票。

#### 验收标准

1. WHEN 调用百日新高采集函数 THEN THE Crawler SHALL 请求百日新高API端点
2. THE Crawler SHALL 支持指定日期参数，默认为当天
3. WHEN API返回数据 THEN THE Data_Parser SHALL 解析并提取以下字段：
   - 日期、股票代码、股票名称
   - 当前价格、涨跌幅、成交额
   - 所属板块
4. THE Crawler SHALL 返回pandas DataFrame格式的数据
5. IF API请求失败 THEN THE Crawler SHALL 返回空DataFrame并记录错误日志

### 需求 8：异动提醒数据采集

**用户故事**: 作为用户，我希望获取异动提醒数据，以便及时发现异常波动的股票。

#### 验收标准

1. WHEN 调用异动提醒采集函数 THEN THE Crawler SHALL 请求异动提醒API端点
2. THE Crawler SHALL 支持指定日期参数，默认为当天
3. WHEN API返回数据 THEN THE Data_Parser SHALL 解析并提取以下字段：
   - 日期、股票名称、当日涨幅
   - 偏离天数、涨幅偏离值
   - 触发条件、触发类型、规则说明
4. THE Crawler SHALL 返回pandas DataFrame格式的数据
5. IF API请求失败 THEN THE Crawler SHALL 返回空DataFrame并记录错误日志

### 需求 9：板块行情数据采集

**用户故事**: 作为用户，我希望获取板块行情数据，以便分析各板块的资金流向和强度。

#### 验收标准

1. WHEN 调用板块行情采集函数 THEN THE Crawler SHALL 请求板块行情API端点
2. THE Crawler SHALL 支持指定分类参数：精选、行业
3. WHEN API返回数据 THEN THE Data_Parser SHALL 解析并提取以下字段：
   - 板块名称、板块代码、强度
   - 主力净额、机构增仓、涨跌幅
4. THE Crawler SHALL 返回pandas DataFrame格式的数据
5. IF API请求失败 THEN THE Crawler SHALL 返回空DataFrame并记录错误日志

### 需求 10：打板数据采集

**用户故事**: 作为用户，我希望获取打板股票数据，以便分析涨停板的封单强度和连板情况。

#### 验收标准

1. WHEN 调用打板数据采集函数 THEN THE Crawler SHALL 请求打板API端点
2. THE Crawler SHALL 支持指定日期参数，默认为当天
3. WHEN API返回数据 THEN THE Data_Parser SHALL 解析并提取以下字段：
   - 日期、股票代码、股票名称
   - 涨停时间、连板天数
   - 封单金额、成交额、流通市值
   - 涨停原因
4. THE Crawler SHALL 返回pandas DataFrame格式的数据
5. IF API请求失败 THEN THE Crawler SHALL 返回空DataFrame并记录错误日志

### 需求 11：数据存储

**用户故事**: 作为用户，我希望爬取的数据能够持久化存储，以便后续分析使用。

#### 验收标准

1. THE Storage_Manager SHALL 支持将DataFrame保存为CSV文件
2. WHEN 保存数据 THEN THE Storage_Manager SHALL 使用"板块名称_日期.csv"的文件命名格式
3. THE Storage_Manager SHALL 支持指定存储目录
4. IF 目标文件已存在 THEN THE Storage_Manager SHALL 提供覆盖或追加选项
5. WHEN 保存失败 THEN THE Storage_Manager SHALL 抛出存储异常并记录错误日志

### 需求 12：日志记录

**用户故事**: 作为开发者，我希望系统记录详细的运行日志，以便排查问题和监控运行状态。

#### 验收标准

1. THE Logger SHALL 记录所有API请求的URL、方法和参数
2. THE Logger SHALL 记录所有API响应的状态码和响应时间
3. WHEN 发生异常 THEN THE Logger SHALL 记录完整的异常堆栈信息
4. THE Logger SHALL 支持不同日志级别：DEBUG、INFO、WARNING、ERROR
5. THE Logger SHALL 将日志输出到控制台和日志文件
6. THE Logger SHALL 使用日期滚动的日志文件命名方式

### 需求 13：错误处理

**用户故事**: 作为用户，我希望系统能够优雅地处理各种错误情况，并提供清晰的错误信息。

#### 验收标准

1. WHEN 配置文件缺失或格式错误 THEN THE Crawler SHALL 抛出ConfigurationError异常
2. WHEN 网络请求超时 THEN THE Crawler SHALL 抛出TimeoutError异常
3. WHEN API返回错误状态码 THEN THE Crawler SHALL 抛出APIError异常并包含状态码和响应内容
4. WHEN 数据解析失败 THEN THE Crawler SHALL 抛出ParseError异常并包含原始响应数据
5. WHEN 认证失败 THEN THE Crawler SHALL 抛出AuthenticationError异常
6. THE Crawler SHALL 在所有异常中包含足够的上下文信息以便调试

### 需求 14：便捷接口

**用户故事**: 作为用户，我希望有简单易用的函数接口，以便快速获取数据而无需创建爬虫实例。

#### 验收标准

1. THE Crawler SHALL 提供模块级别的便捷函数，对应每个数据板块
2. WHEN 调用便捷函数 THEN THE Crawler SHALL 自动创建或复用全局爬虫实例
3. THE Crawler SHALL 支持通过类实例调用和便捷函数调用两种方式
4. THE Crawler SHALL 在模块导入时不自动执行任何网络请求

### 需求 15：数据验证

**用户故事**: 作为用户，我希望系统能够验证返回的数据格式，以便及时发现API变更。

#### 验收标准

1. WHEN 解析API响应 THEN THE Data_Parser SHALL 验证响应是否为有效的JSON格式
2. WHEN 提取数据字段 THEN THE Data_Parser SHALL 检查必需字段是否存在
3. IF 响应结构与预期不符 THEN THE Data_Parser SHALL 记录警告日志并返回部分可用数据
4. THE Data_Parser SHALL 对缺失的字段使用空字符串或None作为默认值
5. WHEN 返回空数据列表 THEN THE Data_Parser SHALL 返回空DataFrame而不是抛出异常
