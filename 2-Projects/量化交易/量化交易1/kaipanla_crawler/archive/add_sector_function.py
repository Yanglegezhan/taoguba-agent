# -*- coding: utf-8 -*-
"""
添加板块数据获取函数
"""

# 读取现有代码
with open('kaipanla_crawler.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 在类定义中添加新方法（在get_daily_data方法之前）
new_method = '''
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
            response = requests.post(
                self.base_url,
                params=params,
                data=data,
                headers=self.headers,
                verify=False,
                proxies={'http': None, 'https': None},
                timeout=30
            )
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
                    "最新价": float(sector[2]),
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
'''

# 找到get_daily_data方法的位置，在它之前插入
insert_pos = code.find('    def get_daily_data(')
if insert_pos > 0:
    new_code = code[:insert_pos] + new_method + '\n' + code[insert_pos:]
    
    with open('kaipanla_crawler.py', 'w', encoding='utf-8') as f:
        f.write(new_code)
    
    print("✅ 板块数据获取函数已添加")
else:
    print("❌ 未找到插入位置")
