# -*- coding: utf-8 -*-
"""
调试风向标接口，查看原始返回数据
"""

import sys
sys.path.append('kaipanla_crawler')

from kaipanla_crawler import KaipanlaCrawler
import json

def main():
    """测试风向标接口"""
    crawler = KaipanlaCrawler()
    date = "2026-02-12"
    
    # 先获取板块数据
    print("获取板块数据...")
    sector_data = crawler.get_sector_ranking(date=date)
    
    if not sector_data or not sector_data.get('sectors'):
        print("未获取到板块数据")
        return
    
    # 选择一个有较多股票的板块进行测试
    test_sector = None
    for sector in sector_data['sectors']:
        if len(sector['stocks']) >= 5:  # 选择至少有5只股票的板块
            test_sector = sector
            break
    
    if not test_sector:
        print("未找到合适的测试板块")
        return
    
    sector_code = test_sector['sector_code']
    sector_name = test_sector['sector_name']
    stocks = test_sector['stocks']
    stock_codes = [stock['股票代码'] for stock in stocks]
    
    print(f"\n测试板块: {sector_name} ({sector_code})")
    print(f"股票数量: {len(stock_codes)}")
    print(f"股票代码: {stock_codes}")
    
    # 调用风向标接口
    print("\n调用风向标接口...")
    
    import requests
    import uuid
    
    stocks_str = ",".join(stock_codes)
    data = {
        "a": "PlateIntroduction_Info",
        "c": "ZhiShuRanking",
        "PhoneOSNew": "1",
        "Stocks": stocks_str,
        "DeviceID": str(uuid.uuid4()),
        "VerSion": "5.21.0.2",
        "apiv": "w42",
        "PlateID": sector_code
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736)",
        "Host": "apphwhq.longhuvip.com",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
    }
    
    response = requests.post(
        "https://apphwhq.longhuvip.com/w1/api/index.php",
        data=data,
        headers=headers,
        verify=False,
        proxies={'http': None, 'https': None}
    )
    
    result = response.json()
    
    print("\n原始返回数据:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 解析List字段
    if result.get("List"):
        print("\n解析后的股票列表:")
        for i, item in enumerate(result["List"], 1):
            print(f"{i}. {item}")

if __name__ == "__main__":
    main()
