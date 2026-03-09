# -*- coding: utf-8 -*-
"""
开盘啦APP数据爬虫 V2 - 简化版

直接使用test_api_final.py中验证成功的方法
"""

import requests
import pandas as pd
from datetime import datetime
import uuid
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class KaipanlaCrawler:
    """开盘啦数据爬虫"""
    
    def __init__(self):
        """初始化爬虫"""
        self.base_url = "https://apphwhq.longhuvip.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Safari/537.36;kaipanla 5.21.0.2",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate",
            "Origin": "https://apppage.longhuvip.com",
            "X-Requested-With": "com.aiyu.kaipanla",
            "Referer": "https://apppage.longhuvip.com/",
        }
    
    def get_market_sentiment(self, date: str = None) -> pd.DataFrame:
        """
        获取市场情绪数据
        
        Args:
            date: 日期，格式YYYY-MM-DD，默认当天
            
        Returns:
            DataFrame，包含市场情绪各项指标
        """
        url = f"{self.base_url}/w1/api/index.php"
        
        params = {
            "apiv": "w42",
            "PhoneOSNew": "1",
            "VerSion": "5.21.0.2"
        }
        
        data = {
            "c": "Index",
            "a": "GetInfo",
            "View": "4,5,11",
            "DeviceID": str(uuid.uuid4())
        }
        
        try:
            # 直接使用test_api_final.py中的方法
            response = requests.post(
                url, 
                params=params,
                data=data,
                headers=self.headers,
                verify=False,
                proxies={'http': None, 'https': None},
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 解析响应数据
            daban_list = result.get("DaBanList", {})
            day = result.get("Day", date or datetime.now().strftime("%Y-%m-%d"))
            
            # 构建DataFrame
            data = {
                "日期": [day],
                "实际涨停": [daban_list.get("tZhangTing", 0)],
                "昨日涨停": [daban_list.get("lZhangTing", 0)],
                "实际跌停": [daban_list.get("tDieTing", 0)],
                "昨日跌停": [daban_list.get("lDieTing", 0)],
                "涨家数": [daban_list.get("SZJS", 0)],
                "跌家数": [daban_list.get("XDJS", 0)],
                "平盘家数": [daban_list.get("PPJS", 0)],
                "实际量能_深圳(万元)": [daban_list.get("szln", 0)],
                "预测量能_全市场(万元)": [daban_list.get("qscln", 0)],
                "今日涨停封板率(%)": [round(daban_list.get("tFengBan", 0), 2)],
                "昨日涨停封板率(%)": [round(daban_list.get("lFengBan", 0), 2)],
                "综合强度": [daban_list.get("ZHQD", 0)],
                "昨日涨停今表现(%)": [round(daban_list.get("ZRZTJ", 0), 2)],
                "昨日连板今表现(%)": [round(daban_list.get("ZRLBJ", 0), 2)],
                "深圳昨日成交额(万元)": [daban_list.get("s_zrcs", 0)],
                "全市场昨日成交额(万元)": [daban_list.get("q_zrcs", 0)],
            }
            
            df = pd.DataFrame(data)
            
            # 添加计算字段
            df["今日涨停破板率(%)"] = round(100 - df["今日涨停封板率(%)"], 2)
            df["涨跌比"] = round(df["涨家数"] / (df["跌家数"] + 1), 2)
            df["涨停率(%)"] = round((df["实际涨停"] / (df["涨家数"] + df["跌家数"] + df["平盘家数"])) * 100, 2)
            
            return df
            
        except Exception as e:
            print(f"获取市场情绪数据失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()


if __name__ == "__main__":
    print("测试爬虫V2...")
    crawler = KaipanlaCrawler()
    df = crawler.get_market_sentiment()
    
    if not df.empty:
        print("✅ 成功！")
        print(df.T.to_string())
    else:
        print("❌ 失败")

    
    def get_market_index(self, date: str = None) -> pd.DataFrame:
        """
        获取大盘指数数据
        
        Args:
            date: 日期，格式YYYY-MM-DD，默认当天
            
        Returns:
            DataFrame，包含上证、深证、创业板等指数数据
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        url = "https://apphis.longhuvip.com/w1/api/index.php"
        
        params = {
            "apiv": "w42",
            "PhoneOSNew": "1",
            "VerSion": "5.21.0.2"
        }
        
        data = {
            "a": "GetZsReal",
            "c": "StockL2History",
            "PhoneOSNew": "1",
            "DeviceID": str(uuid.uuid4()),
            "VerSion": "5.21.0.2",
            "apiv": "w42",
            "Day": date
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736)",
            "Host": "apphis.longhuvip.com",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
        }
        
        try:
            response = requests.post(
                url, 
                params=params,
                data=data,
                headers=headers,
                verify=False,
                proxies={'http': None, 'https': None},
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 解析响应数据
            stock_list = result.get("StockList", [])
            
            records = []
            for stock in stock_list:
                records.append({
                    "日期": date,
                    "指数代码": stock.get("StockID", ""),
                    "指数名称": stock.get("prod_name", ""),
                    "最新价": float(stock.get("last_px", 0)),
                    "涨跌额": float(stock.get("increase_amount", 0)),
                    "涨跌幅": stock.get("increase_rate", ""),
                    "成交额(元)": int(stock.get("turnover", 0)),
                })
            
            return pd.DataFrame(records)
            
        except Exception as e:
            print(f"获取大盘指数数据失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def get_limit_up_ladder(self, date: str = None) -> pd.DataFrame:
        """
        获取连板梯队数据
        
        Args:
            date: 日期，格式YYYY-MM-DD，默认当天
            
        Returns:
            DataFrame，包含连板梯队统计信息
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        url = "https://apphis.longhuvip.com/w1/api/index.php"
        
        params = {
            "apiv": "w42",
            "PhoneOSNew": "1",
            "VerSion": "5.21.0.2"
        }
        
        data = {
            "a": "ZhangTingExpression",
            "c": "HisHomeDingPan",
            "PhoneOSNew": "1",
            "DeviceID": str(uuid.uuid4()),
            "VerSion": "5.21.0.2",
            "apiv": "w42",
            "Day": date
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736)",
            "Host": "apphis.longhuvip.com",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
        }
        
        try:
            response = requests.post(
                url, 
                params=params,
                data=data,
                headers=headers,
                verify=False,
                proxies={'http': None, 'https': None},
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 解析响应数据
            info = result.get("info", [])
            
            if len(info) >= 12:
                data = {
                    "日期": [date],
                    "首板数量": [info[0]],
                    "2连板数量": [info[1]],
                    "3连板数量": [info[2]],
                    "4连板及以上数量": [info[3]],
                    "连板率(%)": [round(info[4], 2)],
                    "昨日首板今表现_上涨": [info[5]],
                    "昨日首板今表现_下跌": [info[6]],
                    "昨日首板今表现_上涨率(%)": [round(info[7], 2)],
                    "昨日2连板今表现(%)": [round(info[8], 2)],
                    "昨日3连板今表现(%)": [round(info[9], 2)],
                    "昨日4连板及以上今表现(%)": [round(info[10], 2)],
                    "市场评价": [info[11]],
                }
                
                return pd.DataFrame(data)
            else:
                print("连板梯队数据格式异常")
                return pd.DataFrame()
            
        except Exception as e:
            print(f"获取连板梯队数据失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def get_sharp_withdrawal(self, date: str = None) -> pd.DataFrame:
        """
        获取大幅回撤股票数据
        
        Args:
            date: 日期，格式YYYY-MM-DD，默认当天
            
        Returns:
            DataFrame，包含大幅回撤的股票列表
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        url = "https://apphis.longhuvip.com/w1/api/index.php"
        
        params = {
            "apiv": "w42",
            "PhoneOSNew": "1",
            "VerSion": "5.21.0.2"
        }
        
        data = {
            "a": "SharpWithdrawal",
            "c": "HisHomeDingPan",
            "PhoneOSNew": "1",
            "DeviceID": str(uuid.uuid4()),
            "VerSion": "5.21.0.2",
            "apiv": "w42",
            "Day": date
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736)",
            "Host": "apphis.longhuvip.com",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
        }
        
        try:
            response = requests.post(
                url, 
                params=params,
                data=data,
                headers=headers,
                verify=False,
                proxies={'http': None, 'https': None},
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 解析响应数据
            info_list = result.get("info", [])
            total_num = result.get("num", 0)
            result_date = result.get("date", date)
            
            records = []
            for info in info_list:
                if len(info) >= 5:
                    records.append({
                        "日期": result_date,
                        "股票代码": info[0],
                        "股票名称": info[1],
                        "当日涨跌幅(%)": round(info[2], 2),
                        "回撤幅度(%)": round(info[3], 2),
                        "最新价": round(info[4], 2),
                    })
            
            df = pd.DataFrame(records)
            
            if not df.empty:
                print(f"大幅回撤股票总数: {total_num}")
            
            return df
            
        except Exception as e:
            print(f"获取大幅回撤数据失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()


# ============== 便捷函数 ==============

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


def get_market_index(date: str = None) -> pd.DataFrame:
    """获取大盘指数数据"""
    return get_crawler().get_market_index(date)


def get_limit_up_ladder(date: str = None) -> pd.DataFrame:
    """获取连板梯队数据"""
    return get_crawler().get_limit_up_ladder(date)


def get_sharp_withdrawal(date: str = None) -> pd.DataFrame:
    """获取大幅回撤股票数据"""
    return get_crawler().get_sharp_withdrawal(date)
