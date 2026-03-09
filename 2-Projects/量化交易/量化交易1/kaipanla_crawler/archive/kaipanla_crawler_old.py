# -*- coding: utf-8 -*-
"""
开盘啦APP数据爬虫

用于爬取开盘啦APP的以下板块数据：
- 市场情绪
- 复盘啦
- 题材库
- 百日新高
- 异动提醒
- 行情-板块
- 行情-打板

使用说明：
1. 首先完成抓包，获取API接口信息
2. 将API信息填入 kaipanla_config.py
3. 调用对应函数获取数据（返回DataFrame格式）

示例：
    from kaipanla_crawler import KaipanlaCrawler
    
    crawler = KaipanlaCrawler()
    df = crawler.get_market_sentiment()
    print(df)
"""

import requests
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any
import time
import json

# 导入配置
try:
    from kaipanla_config import (
        BASE_URL, DEFAULT_HEADERS, API_ENDPOINTS,
        AUTH_TOKEN, USERNAME, PASSWORD, REQUEST_PARAMS_TEMPLATE
    )
except ImportError:
    raise ImportError("请确保 kaipanla_config.py 文件存在且配置正确")


class KaipanlaCrawler:
    """
    开盘啦数据爬虫
    
    支持的数据板块:
    - 市场情绪 (get_market_sentiment)
    - 复盘啦 (get_fupanla)
    - 题材库 (get_theme_library)
    - 百日新高 (get_100day_high)
    - 异动提醒 (get_abnormal_alert)
    - 行情-板块 (get_sector_quotes)
    - 行情-打板 (get_limit_up_board)
    """
    
    def __init__(self, token: str = None):
        """
        初始化爬虫
        
        Args:
            token: 认证token，如不传入则使用配置文件中的token
        """
        self.base_url = BASE_URL
        self.headers = DEFAULT_HEADERS.copy()
        self.token = token or AUTH_TOKEN
        self.session = requests.Session()
        
        # 设置token到headers
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
        
        self.session.headers.update(self.headers)
    
    def _request(self, method: str, endpoint: str, params: Dict = None, 
                 data: Dict = None, retry: int = 3) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        Args:
            method: 请求方法 (GET/POST)
            endpoint: API端点
            params: URL参数
            data: POST数据
            retry: 重试次数
            
        Returns:
            响应JSON数据
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(retry):
            try:
                if method.upper() == "GET":
                    response = self.session.get(url, params=params, timeout=30)
                else:
                    response = self.session.post(url, json=data, timeout=30)
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == retry - 1:
                    raise Exception(f"请求失败: {url}, 错误: {str(e)}")
                time.sleep(1)  # 重试前等待
        
        return {}
    
    def login(self, username: str = None, password: str = None) -> bool:
        """
        登录获取token
        
        Args:
            username: 用户名，不传则使用配置文件中的
            password: 密码，不传则使用配置文件中的
            
        Returns:
            登录是否成功
        """
        username = username or USERNAME
        password = password or PASSWORD
        
        if not username or not password:
            raise ValueError("请提供用户名和密码，或在配置文件中设置")
        
        endpoint = API_ENDPOINTS.get("login", "/api/v1/user/login")
        
        try:
            # TODO: 根据实际抓包结果调整登录请求格式
            response = self._request("POST", endpoint, data={
                "username": username,
                "password": password,
            })
            
            # TODO: 根据实际响应格式提取token
            if "token" in response:
                self.token = response["token"]
                self.headers["Authorization"] = f"Bearer {self.token}"
                self.session.headers.update(self.headers)
                print("登录成功!")
                return True
            else:
                print(f"登录失败: {response}")
                return False
                
        except Exception as e:
            print(f"登录异常: {str(e)}")
            return False
    
    def get_market_sentiment(self, date: str = None) -> pd.DataFrame:
        """
        获取市场情绪数据
        
        包含：涨停/跌停数据、涨跌家数、量能、连板率、破板率等
        
        Args:
            date: 日期，格式YYYY-MM-DD，默认当天（注意：API可能不支持历史日期查询）
            
        Returns:
            DataFrame，包含市场情绪各项指标
        """
        endpoint = API_ENDPOINTS.get("market_sentiment")
        
        # 获取参数模板
        params = REQUEST_PARAMS_TEMPLATE.get("market_sentiment", {}).copy()
        
        try:
            response = self._request("POST", endpoint, params=params)
            
            # 解析响应数据
            daban_list = response.get("DaBanList", {})
            day = response.get("Day", date or datetime.now().strftime("%Y-%m-%d"))
            
            # 构建DataFrame
            data = {
                "日期": [day],
                "实际涨停": [daban_list.get("tZhangTing", 0)],
                "实际跌停": [daban_list.get("tDieTing", 0)],
                "涨家数": [daban_list.get("SZJS", 0)],  # 上涨家数
                "跌家数": [daban_list.get("XDJS", 0)],  # 下跌家数
                "平盘家数": [daban_list.get("PPJS", 0)],
                "实际量能_深圳": [daban_list.get("szln", 0)],
                "预测量能_全市场": [daban_list.get("qscln", 0)],
                "一板数量": [daban_list.get("tZhangTing", 0)],  # 实际涨停数
                "二板数量": [0],  # API未直接提供，需要从其他接口获取
                "三板数量": [0],  # API未直接提供
                "高度板数量": [0],  # API未直接提供
                "一板连板率": [0],  # API未直接提供
                "二板连板率": [0],  # API未直接提供
                "三板连板率": [0],  # API未直接提供
                "今日涨停封板率": [daban_list.get("tFengBan", 0)],
                "今日涨停破板率": [100 - daban_list.get("tFengBan", 0)],
                "昨日涨停今表现": [daban_list.get("ZRZTJ", 0)],
                "昨日连板今表现": [daban_list.get("ZRLBJ", 0)],
                "昨日破板今表现": [0],  # API未直接提供
                "综合强度": [daban_list.get("ZHQD", 0)],
            }
            
            df = pd.DataFrame(data)
            
            # 添加计算字段
            df["涨跌比"] = df["涨家数"] / (df["跌家数"] + 1)  # 避免除零
            df["涨停率"] = (df["实际涨停"] / (df["涨家数"] + df["跌家数"] + df["平盘家数"])) * 100
            
            return df
            
        except Exception as e:
            print(f"获取市场情绪数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_fupanla(self, date: str = None, category: str = "涨停原因") -> pd.DataFrame:
        """
        获取复盘啦数据
        
        Args:
            date: 日期，格式YYYY-MM-DD，默认当天
            category: 分类，可选 "盘面梳理"/"市场动向"/"涨停原因"
            
        Returns:
            DataFrame，包含复盘数据
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        endpoint = API_ENDPOINTS.get("fupanla")
        
        # TODO: 根据实际API调整参数
        params = {
            "date": date,
            "category": category
        }
        
        try:
            response = self._request("GET", endpoint, params=params)
            
            # TODO: 根据实际响应格式解析数据
            # 涨停原因分类下，返回各板块涨停股票列表
            records = []
            
            # 示例解析逻辑，需根据实际响应调整
            for sector in response.get("sectors", []):
                sector_name = sector.get("name", "")
                limit_count = sector.get("limit_count", 0)
                
                for stock in sector.get("stocks", []):
                    records.append({
                        "日期": date,
                        "板块": sector_name,
                        "板块涨停数": limit_count,
                        "股票代码": stock.get("code", ""),
                        "股票名称": stock.get("name", ""),
                        "涨停时间": stock.get("limit_time", ""),
                        "连板状态": stock.get("continue_status", ""),
                        "实际流通市值": stock.get("float_market_cap", ""),
                        "涨停原因": stock.get("reason", ""),
                    })
            
            return pd.DataFrame(records)
            
        except Exception as e:
            print(f"获取复盘啦数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_theme_library(self, sort_by: str = "热度") -> pd.DataFrame:
        """
        获取题材库数据
        
        Args:
            sort_by: 排序方式，可选 "热度"/"涨幅"
            
        Returns:
            DataFrame，包含题材列表
        """
        endpoint = API_ENDPOINTS.get("theme_library")
        
        # TODO: 根据实际API调整参数
        sort_map = {"热度": "heat", "涨幅": "change"}
        params = {"sort": sort_map.get(sort_by, "heat")}
        
        try:
            response = self._request("GET", endpoint, params=params)
            
            # TODO: 根据实际响应格式解析数据
            records = []
            
            for idx, theme in enumerate(response.get("themes", []), 1):
                records.append({
                    "排序": idx,
                    "题材名称": theme.get("name", ""),
                    "涨停数": theme.get("limit_count", 0),
                    "热度标签": theme.get("hot_tag", ""),
                    "涨幅": theme.get("change_pct", ""),
                })
            
            return pd.DataFrame(records)
            
        except Exception as e:
            print(f"获取题材库数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_100day_high(self, date: str = None) -> pd.DataFrame:
        """
        获取百日新高数据
        
        Args:
            date: 日期，格式YYYY-MM-DD，默认当天
            
        Returns:
            DataFrame，包含创百日新高的股票列表
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        endpoint = API_ENDPOINTS.get("100day_high")
        
        params = {"date": date}
        
        try:
            response = self._request("GET", endpoint, params=params)
            
            # TODO: 根据实际响应格式解析数据
            records = []
            
            for stock in response.get("stocks", []):
                records.append({
                    "日期": date,
                    "股票代码": stock.get("code", ""),
                    "股票名称": stock.get("name", ""),
                    "当前价格": stock.get("price", ""),
                    "涨跌幅": stock.get("change_pct", ""),
                    "成交额": stock.get("amount", ""),
                    "所属板块": stock.get("sector", ""),
                })
            
            return pd.DataFrame(records)
            
        except Exception as e:
            print(f"获取百日新高数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_abnormal_alert(self, date: str = None) -> pd.DataFrame:
        """
        获取异动提醒数据
        
        Args:
            date: 日期，格式YYYY-MM-DD，默认当天
            
        Returns:
            DataFrame，包含异动股票列表
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        endpoint = API_ENDPOINTS.get("abnormal_alert")
        
        params = {"date": date}
        
        try:
            response = self._request("GET", endpoint, params=params)
            
            # TODO: 根据实际响应格式解析数据
            records = []
            
            for alert in response.get("alerts", []):
                records.append({
                    "日期": date,
                    "股票名称": alert.get("name", ""),
                    "当日涨幅": alert.get("change_pct", ""),
                    "偏离天数": alert.get("deviation_days", ""),
                    "涨幅偏离值": alert.get("deviation_value", ""),
                    "触发条件": alert.get("trigger_condition", ""),
                    "触发类型": alert.get("trigger_type", ""),  # 次日/当日
                    "规则说明": alert.get("rule_desc", ""),
                })
            
            return pd.DataFrame(records)
            
        except Exception as e:
            print(f"获取异动提醒数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_sector_quotes(self, category: str = "精选") -> pd.DataFrame:
        """
        获取行情-板块数据
        
        Args:
            category: 分类，可选 "精选"/"行业"
            
        Returns:
            DataFrame，包含板块行情列表
        """
        endpoint = API_ENDPOINTS.get("sector_quotes")
        
        params = {"category": category}
        
        try:
            response = self._request("GET", endpoint, params=params)
            
            # TODO: 根据实际响应格式解析数据
            records = []
            
            for sector in response.get("sectors", []):
                records.append({
                    "板块名称": sector.get("name", ""),
                    "板块代码": sector.get("code", ""),
                    "强度": sector.get("strength", ""),
                    "主力净额": sector.get("main_net_inflow", ""),
                    "机构增仓": sector.get("institution_increase", ""),
                    "涨跌幅": sector.get("change_pct", ""),
                })
            
            return pd.DataFrame(records)
            
        except Exception as e:
            print(f"获取板块行情数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_limit_up_board(self, date: str = None) -> pd.DataFrame:
        """
        获取行情-打板数据
        
        Args:
            date: 日期，格式YYYY-MM-DD，默认当天
            
        Returns:
            DataFrame，包含打板股票列表
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        endpoint = API_ENDPOINTS.get("limit_up_board")
        
        params = {"date": date}
        
        try:
            response = self._request("GET", endpoint, params=params)
            
            # TODO: 根据实际响应格式解析数据
            records = []
            
            for stock in response.get("stocks", []):
                records.append({
                    "日期": date,
                    "股票代码": stock.get("code", ""),
                    "股票名称": stock.get("name", ""),
                    "涨停时间": stock.get("limit_time", ""),
                    "连板天数": stock.get("continue_days", ""),
                    "封单金额": stock.get("seal_amount", ""),
                    "成交额": stock.get("turnover", ""),
                    "流通市值": stock.get("float_market_cap", ""),
                    "涨停原因": stock.get("reason", ""),
                })
            
            return pd.DataFrame(records)
            
        except Exception as e:
            print(f"获取打板数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_market_overview(self, date: str = None) -> Dict[str, Any]:
        """
        获取市场概览数据（从行情-板块页面顶部）
        
        Args:
            date: 日期，格式YYYY-MM-DD，默认当天
            
        Returns:
            包含市场概览信息的字典
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # 这个数据可能和板块行情是同一个接口
        endpoint = API_ENDPOINTS.get("sector_quotes")
        
        params = {"date": date}
        
        try:
            response = self._request("GET", endpoint, params=params)
            
            # TODO: 根据实际响应格式解析数据
            return {
                "日期": date,
                "沪指": response.get("sh_index", ""),
                "深指": response.get("sz_index", ""),
                "创业板指": response.get("cy_index", ""),
                "沪深预测量能": response.get("predict_volume", ""),
                "量能增量": response.get("volume_increase", ""),
                "涨家数": response.get("up_count", ""),
                "跌家数": response.get("down_count", ""),
                "涨停数": response.get("limit_up_count", ""),
                "跌停数": response.get("limit_down_count", ""),
            }
            
        except Exception as e:
            print(f"获取市场概览数据失败: {str(e)}")
            return {}


# ============== 便捷函数（可直接调用）==============

# 创建全局爬虫实例
_crawler = None

def get_crawler() -> KaipanlaCrawler:
    """获取爬虫单例"""
    global _crawler
    if _crawler is None:
        _crawler = KaipanlaCrawler()
    return _crawler


def get_market_sentiment(date: str = None) -> pd.DataFrame:
    """获取市场情绪数据"""
    return get_crawler().get_market_sentiment(date)


def get_fupanla(date: str = None, category: str = "涨停原因") -> pd.DataFrame:
    """获取复盘啦数据"""
    return get_crawler().get_fupanla(date, category)


def get_theme_library(sort_by: str = "热度") -> pd.DataFrame:
    """获取题材库数据"""
    return get_crawler().get_theme_library(sort_by)


def get_100day_high(date: str = None) -> pd.DataFrame:
    """获取百日新高数据"""
    return get_crawler().get_100day_high(date)


def get_abnormal_alert(date: str = None) -> pd.DataFrame:
    """获取异动提醒数据"""
    return get_crawler().get_abnormal_alert(date)


def get_sector_quotes(category: str = "精选") -> pd.DataFrame:
    """获取行情-板块数据"""
    return get_crawler().get_sector_quotes(category)


def get_limit_up_board(date: str = None) -> pd.DataFrame:
    """获取行情-打板数据"""
    return get_crawler().get_limit_up_board(date)


if __name__ == "__main__":
    # 测试代码
    print("开盘啦爬虫模块已加载")
    print("\n可用函数:")
    print("  - get_market_sentiment(date)  # 市场情绪")
    print("  - get_fupanla(date, category)  # 复盘啦")
    print("  - get_theme_library(sort_by)  # 题材库")
    print("  - get_100day_high(date)  # 百日新高")
    print("  - get_abnormal_alert(date)  # 异动提醒")
    print("  - get_sector_quotes(category)  # 行情-板块")
    print("  - get_limit_up_board(date)  # 行情-打板")
    print("\n请先完成抓包，并在 kaipanla_config.py 中配置API信息")
