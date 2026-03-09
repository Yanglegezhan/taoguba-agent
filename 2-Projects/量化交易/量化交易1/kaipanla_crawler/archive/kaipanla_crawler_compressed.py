# -*- coding: utf-8 -*-
import requests, pandas as pd, uuid, urllib3
from datetime import datetime, timedelta
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class KaipanlaCrawler:
    def __init__(self):
        self.base_url = "https://apphis.longhuvip.com/w1/api/index.php"
        self.headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736)", "Host": "apphis.longhuvip.com", "Connection": "Keep-Alive", "Accept-Encoding": "gzip"}
    
    def _request(self, data_params, date):
        params = {"apiv": "w42", "PhoneOSNew": "1", "VerSion": "5.21.0.2"}
        data = {"PhoneOSNew": "1", "DeviceID": str(uuid.uuid4()), "VerSion": "5.21.0.2", "apiv": "w42", "Day": date}
        data.update(data_params)
        try:
            response = requests.post(self.base_url, params=params, data=data, headers=self.headers, verify=False, proxies={'http': None, 'https': None}, timeout=30)
            response.raise_for_status()
            return response.json()
        except: return {}
    
    def _get_single_day_data(self, date):
        result1 = self._request({"a": "HisZhangFuDetail", "c": "HisHomeDingPan"}, date)
        info1 = result1.get("info", {}) if result1 else {}
        result2 = self._request({"a": "GetZsReal", "c": "StockL2History"}, date)
        stock_list = result2.get("StockList", []) if result2 else []
        sh_index = next((s for s in stock_list if s.get("StockID") == "SH000001"), None)
        result3 = self._request({"a": "ZhangTingExpression", "c": "HisHomeDingPan"}, date)
        info3 = result3.get("info", []) if result3 else []
        result4 = self._request({"a": "SharpWithdrawal", "c": "HisHomeDingPan"}, date)
        withdrawal_num = result4.get("num", 0) if result4 else 0
        return {"日期": result1.get("date", date) if result1 else date, "涨停数": int(info1.get("ZT", 0)), "实际涨停": int(info1.get("SJZT", 0)), "跌停数": int(info1.get("DT", 0)), "实际跌停": int(info1.get("SJDT", 0)), "上涨家数": int(info1.get("SZJS", 0)), "下跌家数": int(info1.get("XDJS", 0)), "平盘家数": int(info1.get("0", 0)), "上证指数": float(sh_index.get("last_px", 0)) if sh_index else 0, "最新价": float(sh_index.get("last_px", 0)) if sh_index else 0, "涨跌幅": sh_index.get("increase_rate", "") if sh_index else "", "成交额": int(sh_index.get("turnover", 0)) if sh_index else 0, "首板数量": info3[0] if len(info3) > 0 else 0, "2连板数量": info3[1] if len(info3) > 1 else 0, "3连板数量": info3[2] if len(info3) > 2 else 0, "4连板以上数量": info3[3] if len(info3) > 3 else 0, "连板率": round(info3[4], 2) if len(info3) > 4 else 0, "大幅回撤家数": withdrawal_num}
    
    def get_sector_ranking(self, date=None, order=1, zstype=7, limit=30):
        """
        获取板块排行数据
        
        Args:
            date: 日期，格式YYYY-MM-DD，默认今天
            order: 排序方式，1=涨幅，默认1
            zstype: 板块类型，7=精选板块，默认7
            limit: 返回数量，默认30
            
        Returns:
            DataFrame，包含板块排行数据
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        params = {"apiv": "w42", "PhoneOSNew": "1", "VerSion": "5.21.0.2"}
        data = {
            "Order": str(order),
            "a": "RealRankingInfo",
            "st": str(limit),
            "c": "ZhiShuRanking",
            "PhoneOSNew": "1",
            "DeviceID": str(uuid.uuid4()),
            "VerSion": "5.21.0.2",
            "Index": "0",
            "Date": date,
            "apiv": "w42",
            "Type": "1",
            "ZSType": str(zstype)
        }
        
        try:
            response = requests.post(self.base_url, params=params, data=data, headers=self.headers, verify=False, proxies={'http': None, 'https': None}, timeout=30)
            response.raise_for_status()
            result = response.json()
        except:
            return pd.DataFrame()
        
        sector_list = result.get("list", [])
        if not sector_list:
            return pd.DataFrame()
        
        records = []
        for sector in sector_list:
            if len(sector) >= 19:
                records.append({
                    "日期": date,
                    "板块代码": sector[0],
                    "板块名称": sector[1],
                    "强度": float(sector[2]),
                    "涨跌幅(%)": float(sector[3]),
                    "振幅(%)": float(sector[4]),
                    "成交额(元)": int(sector[5]),
                    "主力净流入(元)": int(sector[6]),
                    "主力流入(元)": int(sector[7]),
                    "主力流出(元)": int(sector[8]),
                    "主力净流入占比(%)": float(sector[9]),
                    "总市值(元)": int(sector[10]),
                    "涨跌幅排名(%)": float(sector[11]),
                    "机构增仓(元)": int(sector[12]),
                    "流通市值(元)": int(sector[13]),
                    "散户净流入(元)": int(sector[14]),
                    "2025年PE": float(sector[15]),
                    "2026年PE": float(sector[16]),
                })
        
        return pd.DataFrame(records)
    
    def get_daily_data(self, end_date, start_date=None):
        if start_date is None:
            data = self._get_single_day_data(end_date)
            return pd.Series(data)
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if start > end: start, end = end, start
        date_list = []
        current = start
        while current <= end:
            date_list.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        records = []
        for date in date_list:
            print(f"正在获取 {date} 的数据...")
            data = self._get_single_day_data(date)
            records.append(data)
        df = pd.DataFrame(records)
        df = df[df["涨停数"] > 0]
        return df
