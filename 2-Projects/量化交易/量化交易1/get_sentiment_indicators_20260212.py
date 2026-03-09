# -*- coding: utf-8 -*-
"""
获取2026年2月12日的所有风向标数据
"""

import sys
sys.path.append('kaipanla_crawler')

from kaipanla_crawler import KaipanlaCrawler
import json

def main():
    """获取2026-02-12的所有风向标"""
    crawler = KaipanlaCrawler()
    date = "2026-02-12"
    
    print("=" * 80)
    print(f"获取 {date} 的所有风向标数据")
    print("=" * 80)
    
    # 1. 获取板块排名数据
    print(f"\n正在获取板块排名数据...")
    sector_data = crawler.get_sector_ranking(date=date)
    
    if not sector_data or not sector_data.get('sectors'):
        print(f"未获取到 {date} 的板块数据")
        return
    
    sectors = sector_data['sectors']
    print(f"共获取到 {len(sectors)} 个板块")
    
    # 2. 对每个板块获取风向标
    all_sentiment_indicators = []
    
    for i, sector in enumerate(sectors, 1):
        sector_code = sector['sector_code']
        sector_name = sector['sector_name']
        stocks = sector['stocks']
        
        if not stocks:
            print(f"\n[{i}/{len(sectors)}] {sector_name} ({sector_code}): 无涨停股票，跳过")
            continue
        
        # 提取股票代码列表
        stock_codes = [stock['股票代码'] for stock in stocks]
        
        print(f"\n[{i}/{len(sectors)}] {sector_name} ({sector_code})")
        print(f"  涨停股票数: {len(stock_codes)}")
        
        # 获取风向标
        sentiment_data = crawler.get_sentiment_indicator(
            plate_id=sector_code,
            stocks=stock_codes
        )
        
        if sentiment_data == '未找到风向标':
            print(f"  ⚠️ 未找到风向标")
            continue
        
        # 整合数据
        result = {
            "板块代码": sector_code,
            "板块名称": sector_name,
            "涨停数量": len(stock_codes),
            "多头风向标": sentiment_data.get('bullish_codes', []),
            "空头风向标": sentiment_data.get('bearish_codes', []),
            "所有股票": sentiment_data.get('all_stocks', [])
        }
        
        all_sentiment_indicators.append(result)
        
        print(f"  ✅ 多头风向标: {', '.join(result['多头风向标'][:3])}")
        print(f"  ✅ 空头风向标: {', '.join(result['空头风向标'][:3])}")
    
    # 3. 保存结果
    output_file = f"风向标数据_{date.replace('-', '')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_sentiment_indicators, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 80)
    print(f"✅ 完成！共获取 {len(all_sentiment_indicators)} 个板块的风向标数据")
    print(f"结果已保存到: {output_file}")
    print("=" * 80)
    
    # 4. 打印汇总
    print("\n【汇总】")
    for item in all_sentiment_indicators:
        print(f"\n{item['板块名称']} ({item['板块代码']})")
        print(f"  涨停数: {item['涨停数量']}")
        if item['多头风向标']:
            print(f"  多头: {', '.join(item['多头风向标'][:3])}")
        if item['空头风向标']:
            print(f"  空头: {', '.join(item['空头风向标'][:3])}")

if __name__ == "__main__":
    main()
