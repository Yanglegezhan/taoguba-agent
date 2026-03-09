# 系统配置

# 数据获取配置
DATA_FETCH = {
    'max_retries': 3,           # 最大重试次数
    'retry_delay': 2.0,         # 重试延迟(秒)
    'timeout': 30,              # 请求超时时间(秒)
    'sleep_min': 2.0,           # 最小休眠时间
    'sleep_max': 5.0,           # 最大休眠时间
    'max_requests_per_minute': 10  # 每分钟最大请求数
}

# 防封禁配置
ANTI_BAN = {
    'enable_user_agent_rotation': True,  # 启用User-Agent轮换
    'user_agents': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    ],
    'enable_proxy': False,       # 禁用代理（Akshare要求）
    'circuit_breaker_threshold': 5,  # 熔断器阈值
    'circuit_breaker_reset_time': 300  # 熔断器重置时间(秒)
}

# 数据源优先级（降级策略）
DATA_SOURCES = {
    'primary': 'akshare',       # 主数据源
    'fallback': [],             # 备用数据源（暂无）
    'use_cache': True,          # 使用缓存
    'cache_dir': 'output/cache' # 缓存目录
}

# 情绪分析配置
SENTIMENT = {
    'lookback_days': 15,        # 回溯天数
    'market_coefficient_weight': {
        'up_down_ratio': 1.0,
        'index_change': 10.0
    },
    'ultra_short_sentiment_weight': {
        'limit_up': 2.0,
        'new_high': 0.5,
        'limit_down': -3.0,
        'blown_rate': -50.0
    },
    'loss_effect_weight': {
        'limit_down': 2.0,
        'pullback': 1.0,
        'yesterday_performance': 10.0
    },
    'cycle_thresholds': {
        'ice_point': {'market': 30, 'sentiment': 50, 'loss': 100},
        'high_tide': {'market': 150, 'sentiment': 150, 'loss': 40},
        'divergence': 50
    }
}

# 板块分析配置
SECTOR = {
    'top_n': 5,                 # 返回前N个强势板块
    'min_limit_up': 3,          # 最小涨停数阈值
    'min_change_pct': 2.0,      # 最小涨幅阈值(%)
    'sector_types': ['concept', 'industry']  # 板块类型：概念/行业
}

# 报告输出配置
REPORT = {
    'output_dir': 'output',
    'formats': ['html', 'markdown'],  # 输出格式
    'template_dir': 'report/templates',
    'chart_width': 1200,
    'chart_height': 600,
    'save_charts': True
}

# 日志配置
LOGGING = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'log_file': 'output/system.log',
    'max_bytes': 10485760,  # 10MB
    'backup_count': 5
}
