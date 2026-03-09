# 配置说明

## 配置文件概览

系统使用三个主要配置文件：

1. `config/system_config.yaml` - 系统级配置
2. `config/agent_config.yaml` - Agent业务逻辑配置
3. `config/data_source_config.yaml` - 数据源配置

## system_config.yaml 详解

### 数据存储配置

```yaml
data:
  base_path: "./data"                    # 数据根目录
  stage1_output: "./data/stage1_output"  # Stage1输出目录
  stage2_output: "./data/stage2_output"  # Stage2输出目录
  stage3_output: "./data/stage3_output"  # Stage3输出目录
  historical_db: "./data/historical/gene_pool_history.db"  # 历史数据库
  logs_path: "./data/logs"               # 日志目录
```

### 日志配置

```yaml
logging:
  level: "INFO"          # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "..."          # 日志格式字符串
  rotation: "100 MB"     # 日志文件轮转大小
  retention: "30 days"   # 日志保留时间
  console_output: true   # 是否输出到控制台
  file_output: true      # 是否输出到文件
```

### 时间配置

```yaml
timing:
  stage1_run_time: "15:30"   # Stage1运行时间（收盘后）
  stage2_run_time: "07:00"   # Stage2运行时间（早盘前）
  stage3_start_time: "09:15" # Stage3开始时间（竞价开始）
  stage3_end_time: "09:25"   # Stage3结束时间（竞价结束）
```

### 推送配置

```yaml
notification:
  enabled: true
  wechat:
    enabled: false
    webhook_url: ""      # 企业微信Webhook URL
  email:
    enabled: false
    smtp_server: ""      # SMTP服务器地址
    smtp_port: 587       # SMTP端口
    sender: ""           # 发件人邮箱
    password: ""         # 邮箱密码或授权码
    recipients: []       # 收件人列表
```

### 性能配置

```yaml
performance:
  max_workers: 4      # 最大并发工作线程数
  timeout: 30         # API调用超时时间（秒）
  retry_times: 3      # 失败重试次数
```

## agent_config.yaml 详解

### Stage1配置

```yaml
stage1:
  enabled: true
  gene_pool:
    min_board_height: 2        # 最低连板高度
    min_market_cap: 10         # 最小市值（亿元）
    max_market_cap: 500        # 最大市值（亿元）
    min_turnover_rate: 1.0     # 最小换手率（%）
  
  technical:
    ma_periods: [5, 10, 20]    # 均线周期
    lookback_days: 60          # 回溯天数
    chip_concentration_threshold: 0.3  # 筹码密集度阈值
```

### Stage2配置

```yaml
stage2:
  enabled: true
  baseline:
    continuous_limit_up:
      strong_theme_min: 5.0    # 强势题材最低预期（%）
      strong_theme_max: 8.0    # 强势题材最高预期（%）
      weak_theme_min: -2.0     # 弱势题材最低预期（%）
      weak_theme_max: 2.0      # 弱势题材最高预期（%）
    
    failed_limit_up:
      min: -2.0
      max: 2.0
    
    min_auction_amount: 10000  # 最小竞价金额预期（万元）
  
  new_theme_keywords:          # 新题材检测关键词
    - "政策"
    - "规划"
    - "利好"
```

### Stage3配置

```yaml
stage3:
  enabled: true
  expectation_score:
    volume_weight: 0.4         # 量能权重
    price_weight: 0.4          # 价格权重
    independence_weight: 0.2   # 独立性权重
  
  volume_thresholds:
    excellent: 0.05            # 竞价金额占比>5%为优秀
    good: 0.03                 # 竞价金额占比>3%为良好
    fair: 0.02                 # 竞价金额占比>2%为一般
  
  withdrawal:
    price_drop_threshold: 3.0  # 价格下跌阈值（%）
    volume_drop_threshold: 0.5 # 撤单量阈值
  
  additional_pool:
    top_seals:
      min_seal_ratio: 0.05     # 最小封单比
      min_seal_amount: 50000   # 最小封单金额（万元）
      top_n: 10                # 取前N名
    
    # ... 其他附加池配置
  
  status_score:
    theme_recognition_weight: 0.35
    urgency_weight: 0.35
    emotion_hedge_weight: 0.30
    top_n: 5                   # 最终筛选前N名
  
  recommendation:
    excellent_threshold: 80    # 优秀分值阈值（建议打板）
    good_threshold: 60         # 良好分值阈值（建议低吸）
    fair_threshold: 40         # 一般分值阈值（建议观望）
```

## data_source_config.yaml 详解

### 数据源优先级

```yaml
priority:
  - kaipanla    # 第一优先级
  - akshare     # 第二优先级
  - eastmoney   # 第三优先级
```

### Kaipanla配置

```yaml
kaipanla:
  enabled: true
  base_url: "http://api.kaipanla.com"
  timeout: 30
  retry_times: 3
  api_key: ""   # 如需要API密钥
```

### AKShare配置

```yaml
akshare:
  enabled: true
  proxy:
    enabled: false   # AKShare需要禁用代理
    http: ""
    https: ""
  timeout: 30
  retry_times: 3
```

### 东方财富配置

```yaml
eastmoney:
  enabled: true
  base_url: "http://push2.eastmoney.com"
  timeout: 30
  retry_times: 3
```

### 新闻数据源配置

```yaml
news:
  securities_daily:
    enabled: true
    url: "http://www.zqrb.cn"
  # ... 其他新闻源
```

## 环境变量 (.env)

```bash
# Gemini API配置
GEMINI_API_KEY=your_gemini_api_key_here

# 数据源API密钥
KAIPANLA_API_KEY=

# 推送配置
WECHAT_WEBHOOK_URL=
EMAIL_SMTP_SERVER=
EMAIL_SMTP_PORT=587
EMAIL_SENDER=
EMAIL_PASSWORD=
EMAIL_RECIPIENTS=

# 代理配置
HTTP_PROXY=
HTTPS_PROXY=
```

## 配置最佳实践

1. **开发环境**：使用较低的日志级别（DEBUG）和较短的超时时间
2. **生产环境**：使用INFO级别日志，配置推送通知
3. **测试环境**：禁用推送，使用测试数据源
4. **安全性**：不要将包含敏感信息的配置文件提交到版本控制

## 配置验证

系统启动时会自动验证配置文件的有效性。如果配置有误，会输出详细的错误信息。

可以使用以下命令手动验证配置：

```python
from common.config import ConfigManager

config = ConfigManager()
config.load_config()
print("配置加载成功！")
```
