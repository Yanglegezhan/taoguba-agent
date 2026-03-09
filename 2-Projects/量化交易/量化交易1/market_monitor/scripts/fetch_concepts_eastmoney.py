# -*- coding: utf-8 -*-
"""
从东方财富网爬取股票概念信息
比API方式更快速可靠
"""

import pandas as pd
import requests
import time
from tqdm import tqdm
import json


def get_stock_concept_eastmoney(stock_code):
    """
    从东方财富网获取单只股票的概念
    
    Args:
        stock_code: 股票代码（6位字符串）
    
    Returns:
        str: 概念字符串，格式如 "概念1+概念2"
    """
    try:
        # 判断市场代码
        if stock_code.startswith('6'):
            secid = f"1.{stock_code}"  # 上海
        else:
            secid = f"0.{stock_code}"  # 深圳
        
        # 东方财富概念API
        url = f"https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            'secid': secid,
            'fields': 'f62,f184,f86',  # f184是概念字段
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and 'data' in data and data['data']:
                # f184 是概念字段
                concept_str = data['data'].get('f184', '')
                
                # 处理各种异常类型
                if concept_str is None or concept_str == '' or concept_str == '-':
                    return ''
                
                # 如果是数字类型（float/int），直接返回空
                if isinstance(concept_str, (float, int)):
                    return ''
                
                # 确保是字符串类型
                concept_str = str(concept_str)
                
                # 概念可能是用分号或逗号分隔的
                concepts = concept_str.replace('；', ';').replace('，', ';').split(';')
                concepts = [c.strip() for c in concepts if c.strip()]
                
                # 返回前两个概念
                if len(concepts) >= 2:
                    return f"{concepts[0]}+{concepts[1]}"
                elif len(concepts) == 1:
                    return concepts[0]
        
        return ''
        
    except Exception as e:
        print(f"\n获取 {stock_code} 概念失败: {e}")
        return ''


def get_concepts_from_board_page():
    """
    从东方财富概念板块页面批量获取
    这种方法最快
    """
    print("从东方财富概念板块页面批量获取...")
    
    stock_concepts = {}  # {股票代码: [概念列表]}
    
    try:
        # 获取概念板块列表
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': '1',
            'pz': '2000',  # 获取前2000个概念
            'po': '1',
            'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2',
            'invt': '2',
            'fid': 'f3',
            'fs': 'm:90+t:3',  # 概念板块
            'fields': 'f12,f14',
            '_': str(int(time.time() * 1000))
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/center/gridlist.html'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"获取概念板块列表失败: {response.status_code}")
            return {}
        
        data = response.json()
        if not data or 'data' not in data or not data['data'] or 'diff' not in data['data']:
            print("概念板块数据为空")
            return {}
        
        concept_list = data['data']['diff']
        print(f"找到 {len(concept_list)} 个概念板块")
        
        # 遍历每个概念板块
        for concept_item in tqdm(concept_list, desc="获取概念成分股"):
            concept_code = concept_item['f12']
            concept_name = concept_item['f14']
            
            # 跳过不相关的概念
            if any(skip in concept_name for skip in ['昨日', '涨停', '连板', '破板']):
                continue
            
            try:
                # 获取该概念的成分股
                stock_url = "https://push2.eastmoney.com/api/qt/clist/get"
                stock_params = {
                    'pn': '1',
                    'pz': '1000',
                    'po': '1',
                    'np': '1',
                    'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                    'fltt': '2',
                    'invt': '2',
                    'fid': 'f3',
                    'fs': f'b:{concept_code}+f:!50',
                    'fields': 'f12',
                    '_': str(int(time.time() * 1000))
                }
                
                stock_response = requests.get(stock_url, params=stock_params, headers=headers, timeout=10)
                
                if stock_response.status_code == 200:
                    stock_data = stock_response.json()
                    if stock_data and 'data' in stock_data and stock_data['data'] and 'diff' in stock_data['data']:
                        stocks = stock_data['data']['diff']
                        
                        for stock in stocks:
                            stock_code = str(stock['f12']).zfill(6)
                            
                            if stock_code not in stock_concepts:
                                stock_concepts[stock_code] = []
                            
                            stock_concepts[stock_code].append(concept_name)
                
                # 避免请求过快
                time.sleep(0.05)
                
            except Exception as e:
                print(f"\n获取概念 {concept_name} 成分股失败: {e}")
                continue
        
        # 为每只股票选择前两个概念
        stock_concept_dict = {}
        for code, concepts in stock_concepts.items():
            if len(concepts) >= 2:
                stock_concept_dict[code] = f"{concepts[0]}+{concepts[1]}"
            elif len(concepts) == 1:
                stock_concept_dict[code] = concepts[0]
        
        return stock_concept_dict
        
    except Exception as e:
        print(f"批量获取失败: {e}")
        return {}


def main():
    print("=" * 60)
    print("从东方财富网获取股票概念信息")
    print("=" * 60)
    
    # 1. 加载连板数据
    print("\n1. 加载连板数据...")
    board_df = pd.read_csv('output/board_analysis.csv', encoding='utf-8-sig')
    stocks_with_boards = board_df[board_df['连板数'] >= 2]['股票代码'].unique()
    stocks_need_concept = [str(code).zfill(6) for code in stocks_with_boards]
    print(f"需要获取 {len(stocks_need_concept)} 只股票的概念")
    
    # 2. 检查已有的概念
    concept_cache_file = 'output/concept_cache.csv'
    existing_concepts = {}
    try:
        concept_cache = pd.read_csv(concept_cache_file, encoding='utf-8-sig')
        existing_concepts = dict(zip(concept_cache['股票代码'].astype(str).str.zfill(6), concept_cache['概念']))
        print(f"已有 {len(existing_concepts)} 只股票的概念")
    except:
        print("没有找到概念缓存文件")
    
    # 3. 方法1：从概念板块批量获取（推荐，最快）
    print("\n2. 从东方财富概念板块批量获取...")
    print("预计需要3-5分钟...")
    new_concepts = get_concepts_from_board_page()
    print(f"\n批量获取到 {len(new_concepts)} 只股票的概念")
    
    # 4. 方法2：对于没有获取到的股票，逐个查询
    all_concepts = {**new_concepts, **existing_concepts}
    missing_stocks = [code for code in stocks_need_concept if code not in all_concepts]
    
    if missing_stocks:
        print(f"\n3. 逐个查询剩余 {len(missing_stocks)} 只股票...")
        for stock_code in tqdm(missing_stocks, desc="逐个查询"):
            concept = get_stock_concept_eastmoney(stock_code)
            if concept:
                all_concepts[stock_code] = concept
            time.sleep(0.1)  # 避免请求过快
    
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
    stocks_with_concept = set(all_concepts.keys())
    stocks_need_set = set(stocks_need_concept)
    coverage = len(stocks_with_concept & stocks_need_set) / len(stocks_need_set) * 100
    print(f"\n概念覆盖率: {coverage:.1f}%")
    print(f"有概念: {len(stocks_with_concept & stocks_need_set)} 只")
    print(f"无概念: {len(stocks_need_set - stocks_with_concept)} 只")
    
    if len(stocks_need_set - stocks_with_concept) > 0:
        print("\n无概念的股票（前10只）:")
        for code in list(stocks_need_set - stocks_with_concept)[:10]:
            stock_name = board_df[board_df['股票代码'].astype(str).str.zfill(6) == code]['股票名称'].iloc[0]
            print(f"  {code} {stock_name}")
    
    print("\n" + "=" * 60)
    print("完成！现在可以运行 python premium_table_v3.py 生成表格")
    print("=" * 60)


if __name__ == "__main__":
    main()
