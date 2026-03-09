# -*- coding: utf-8 -*-
"""
从同花顺获取股票概念信息 - V2版本
使用你提供的headers
"""

import requests
import pandas as pd
import time
from tqdm import tqdm
import json


def get_concept_list():
    """获取所有概念板块列表"""
    try:
        url = "http://q.10jqka.com.cn/gn/"
        
        headers = {
            'Host': 'q.10jqka.com.cn',
            'Referer': 'http://q.10jqka.com.cn/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:105.0) Gecko/20100101 Firefox/105.0',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cookie': 'v=AzCSZkisIBam9fwSniGPJndtB_-HeRW6Nl9qaSqB_nJczN4r0onkU4ZtOEN5; __bid_n=18484da3254140db6d4207; Hm_lvt_78c58f01938e4d85eaf619eae71b4ed1=1680163246; FPTOKEN=E5SR2waOvFusCzMCQVA/i0npfLNEl6RajFMppa8aoQmLTnIl68wGldxUBmPM57Q9yOCUCB1aiKbuSjFdBzV5SnHNhe0uSYQIfJ9t5YdBrYTHtRO06p0Kjf3ck0dxo587GXZ/Lln6kY2EoiWCZBlXHLfwWq6d/uLzQfq+BnkeN8y5zWt6kJAzY84fZaTCNQPf4Vae5qHOYpskzus+szaS5Qm2VNc/Q/t/0U7QQADRzNRLfYf6A/407ZMdD6+1sGvCQhh959iGl+DRavRasWH2ISY3G/osl/olB61tXSIxNI+IL+rAu7u5TvknHHwVtcigMY4jsgE8qBkN2HU4wDvH5QMv+0E89L5jACYIF+BoMaBNN6VkPt9Pksg8+K6O4K9rwElcjiWRuyzNy25YO13lYQ==|sPeLn4kqSDrmYnpF7Wn94V4caIa/qNc5YWTtvQFK+ac=|10|2bc6aba78093d71b50d1b70dd20ef09d; Hm_lpvt_78c58f01938e4d85eaf619eae71b4ed1=1680163469',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'gbk'
        
        print(f"状态码: {response.status_code}")
        print(f"响应长度: {len(response.text)}")
        print(f"前500字符:\n{response.text[:500]}")
        
        # 尝试解析HTML获取概念列表
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找概念板块
        concepts = []
        # 尝试不同的选择器
        for selector in ['.board-list a', '.cate_items a', 'a[href*="/gn/detail/"]']:
            items = soup.select(selector)
            if items:
                print(f"找到 {len(items)} 个概念 (选择器: {selector})")
                for item in items:
                    concept_name = item.get_text(strip=True)
                    concept_url = item.get('href', '')
                    if concept_name and concept_url:
                        concepts.append({
                            'name': concept_name,
                            'url': concept_url
                        })
                break
        
        return concepts
        
    except Exception as e:
        print(f"获取概念列表失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_concept_stocks(concept_code, concept_name):
    """获取某个概念下的股票"""
    try:
        url = f"http://q.10jqka.com.cn/gn/detail/code/{concept_code}/"
        
        headers = {
            'Host': 'q.10jqka.com.cn',
            'Referer': 'http://q.10jqka.com.cn/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:105.0) Gecko/20100101 Firefox/105.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'gbk'
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找股票列表
        stocks = []
        
        # 尝试多种方式查找表格
        table = soup.find('table', {'class': 'table-board'})
        if not table:
            table = soup.find('table', {'class': 'm-table'})
        if not table:
            table = soup.find('tbody')
        
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    # 尝试获取股票代码
                    stock_code = None
                    stock_name = None
                    
                    # 第一列通常是序号,第二列是代码
                    for i, col in enumerate(cols):
                        text = col.get_text(strip=True)
                        # 判断是否是股票代码(6位数字)
                        if text.isdigit() and len(text) == 6:
                            stock_code = text
                            # 下一列通常是股票名称
                            if i + 1 < len(cols):
                                stock_name = cols[i + 1].get_text(strip=True)
                            break
                    
                    if stock_code:
                        stocks.append({
                            'code': stock_code,
                            'name': stock_name or ''
                        })
        
        return stocks
        
    except Exception as e:
        return []


def batch_get_concepts():
    """批量获取所有股票的概念"""
    print("\n开始批量获取股票概念...")
    
    # 获取所有概念板块
    concepts = get_concept_list()
    
    if not concepts:
        print("未获取到概念板块数据")
        return {}
    
    print(f"找到 {len(concepts)} 个概念板块")
    
    stock_concepts = {}  # {股票代码: [概念列表]}
    
    # 遍历每个概念板块
    for concept in tqdm(concepts, desc="获取概念成分股"):
        concept_name = concept['name']
        concept_url = concept['url']
        
        # 从URL中提取概念代码
        import re
        match = re.search(r'/code/(\d+)/', concept_url)
        if not match:
            continue
        
        concept_code = match.group(1)
        
        # 跳过不相关的概念
        if any(skip in concept_name for skip in ['昨日', '涨停', '连板', '破板', '破发']):
            continue
        
        # 获取该概念的成分股
        stocks = get_concept_stocks(concept_code, concept_name)
        
        for stock in stocks:
            stock_code = stock['code']
            if stock_code not in stock_concepts:
                stock_concepts[stock_code] = []
            stock_concepts[stock_code].append(concept_name)
        
        # 避免请求过快
        time.sleep(0.1)
    
    # 为每只股票选择前两个概念
    stock_concept_dict = {}
    for code, concepts_list in stock_concepts.items():
        if len(concepts_list) >= 2:
            stock_concept_dict[code] = f"{concepts_list[0]}+{concepts_list[1]}"
        elif len(concepts_list) == 1:
            stock_concept_dict[code] = concepts_list[0]
    
    return stock_concept_dict


def main():
    print("=" * 60)
    print("从同花顺获取股票概念信息 - V2版本")
    print("=" * 60)
    
    # 1. 加载连板数据
    print("\n1. 加载连板数据...")
    try:
        board_df = pd.read_csv('output/board_analysis.csv', encoding='utf-8-sig')
        stocks_with_boards = board_df[board_df['连板数'] >= 2]['股票代码'].unique()
        stocks_need_concept = [str(code).zfill(6) for code in stocks_with_boards]
        print(f"需要获取 {len(stocks_need_concept)} 只股票的概念")
    except:
        print("未找到连板数据文件,将获取所有概念")
        stocks_need_concept = []
    
    # 2. 检查已有的概念
    concept_cache_file = 'output/concept_cache.csv'
    existing_concepts = {}
    try:
        concept_cache = pd.read_csv(concept_cache_file, encoding='utf-8-sig')
        existing_concepts = dict(zip(
            concept_cache['股票代码'].astype(str).str.zfill(6), 
            concept_cache['概念']
        ))
        print(f"已有 {len(existing_concepts)} 只股票的概念")
    except:
        print("没有找到概念缓存文件")
    
    # 3. 批量获取概念
    print("\n2. 批量获取股票概念...")
    print("预计需要5-10分钟...")
    new_concepts = batch_get_concepts()
    print(f"\n批量获取到 {len(new_concepts)} 只股票的概念")
    
    # 4. 合并概念数据
    all_concepts = {**new_concepts, **existing_concepts}
    
    print(f"\n总计获取到 {len(all_concepts)} 只股票的概念")
    
    # 5. 保存到缓存
    if all_concepts:
        concept_df = pd.DataFrame({
            '股票代码': list(all_concepts.keys()),
            '概念': list(all_concepts.values())
        })
        concept_df.to_csv(concept_cache_file, index=False, encoding='utf-8-sig')
        print(f"\n已保存到: {concept_cache_file}")
    
    # 6. 统计覆盖率
    if stocks_need_concept:
        stocks_with_concept = set(all_concepts.keys())
        stocks_need_set = set(stocks_need_concept)
        coverage = len(stocks_with_concept & stocks_need_set) / len(stocks_need_set) * 100
        print(f"\n概念覆盖率: {coverage:.1f}%")
        print(f"有概念: {len(stocks_with_concept & stocks_need_set)} 只")
        print(f"无概念: {len(stocks_need_set - stocks_with_concept)} 只")
        
        if len(stocks_need_set - stocks_with_concept) > 0:
            print("\n无概念的股票（前10只）:")
            for code in list(stocks_need_set - stocks_with_concept)[:10]:
                try:
                    stock_name = board_df[
                        board_df['股票代码'].astype(str).str.zfill(6) == code
                    ]['股票名称'].iloc[0]
                    print(f"  {code} {stock_name}")
                except:
                    print(f"  {code}")
    
    print("\n" + "=" * 60)
    print("完成！现在可以运行 python premium_table_v3.py 生成表格")
    print("=" * 60)


if __name__ == "__main__":
    main()
