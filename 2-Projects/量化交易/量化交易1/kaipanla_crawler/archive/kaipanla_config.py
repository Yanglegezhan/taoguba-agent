# -*- coding: utf-8 -*-
"""
开盘啦APP爬虫配置文件

使用说明：
1. 完成抓包后，将获取到的API接口信息填入下方对应位置
2. 填入您的登录凭据（如需要）
"""

# ============== 用户凭据配置 ==============
# 如果需要登录，请填入您的账号信息
USERNAME = ""
PASSWORD = ""

# 登录后获取的Token（抓包获取）
AUTH_TOKEN = ""

# ============== API基础配置 ==============
# 开盘啦API的基础URL（抓包获取）
BASE_URL = "https://apphwhq.longhuvip.com"

# 请求Headers模板（抓包获取）
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Safari/537.36;kaipanla 5.21.0.2",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Origin": "https://apppage.longhuvip.com",
    "X-Requested-With": "com.aiyu.kaipanla",
    "Referer": "https://apppage.longhuvip.com/",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}

# ============== API端点配置 ==============
# 请根据抓包结果填入对应的API端点

API_ENDPOINTS = {
    # 市场情绪
    "market_sentiment": "/w1/api/index.php",
    
    # 复盘啦
    "fupanla": "/api/v1/fupanla",  # 待抓包确认
    
    # 题材库
    "theme_library": "/api/v1/theme/library",  # 待抓包确认
    
    # 百日新高
    "100day_high": "/api/v1/stock/100day_high",  # 待抓包确认
    
    # 异动提醒
    "abnormal_alert": "/api/v1/alert/abnormal",  # 待抓包确认
    
    # 行情-板块
    "sector_quotes": "/api/v1/quotes/sector",  # 待抓包确认
    
    # 行情-打板
    "limit_up_board": "/api/v1/quotes/limitup",  # 待抓包确认
    
    # 登录接口
    "login": "/api/v1/user/login",  # 待抓包确认
}

# ============== 请求参数模板 ==============
# 某些接口可能需要特定的请求参数，抓包后填入

REQUEST_PARAMS_TEMPLATE = {
    "market_sentiment": {
        # URL参数
        "url_params": {
            "apiv": "w42",
            "PhoneOSNew": "1",
            "VerSion": "5.21.0.2",
        },
        # POST body参数
        "post_data": {
            "c": "Index",
            "a": "GetInfo",
            "View": "4,5,11",
            # DeviceID 将在运行时生成
        }
    },
    "fupanla": {
        "date": "",
        "category": "涨停原因",  # 盘面梳理/市场动向/涨停原因
    },
    "theme_library": {
        "sort": "heat",  # 按热度/按涨幅
    },
    "sector_quotes": {
        "category": "精选",  # 精选/行业
    },
}
