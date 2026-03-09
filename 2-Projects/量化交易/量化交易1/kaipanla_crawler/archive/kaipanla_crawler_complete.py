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
