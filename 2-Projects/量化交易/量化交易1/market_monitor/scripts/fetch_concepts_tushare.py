# -*- coding: utf-8 -*-
"""
使用 Tushare API 获取股票概念信息
Tushare 是专业的金融数据接口，数据质量高且稳定
"""

import pandas as pd
import tushare as ts
from tqdm import tqdm
import time


# 设置 Tushare token
TUSHARE_TOKEN = '5f4f5783867898c47ce50002876d52ca448b0cb9a29c202a7818bcd6'


def init_tushare():
    """初始化 Tushare"""
    try:
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        print("✓ Tushare API 初始化成功")
        return pro
    except Exception as e:
        print(f"✗ Tushare API 初始化失败: {e}")
        return None


def get_all_concepts(pro):
    """
    获取所有概念板块信息
    
    Returns:
        DataFrame: 概念板块列表
    """
    try:
        print("获取概念板块列表...")
        # 获取概念板块
        concepts = pro.concept(src='ts', fields='code,name')
        
        print(f"找到 {len(concepts)} 个概念板块")
        return concepts
    except Exception as e:
        print(f"获取概念板块失败: {e}")
        return pd.DataFrame()


def get_concept_stocks(pro, concept_code):
    """
    获取某个概念下的所有股票
    
    Args:
        pro: Tushare pro API
        concept_code: 概念代码
    
    Returns:
        list: 股票代码列表
    """
    try:
        # 获取概念成分股
        stocks = pro.concept_detail(id=concept_code, fields='ts_code,name')
        
        if stocks is not None and not stocks.empty:
            # 提取6位股票代码
            stock_codes = []
            for ts_code in stocks['ts_code']:
                # ts_code 格式如 '000001.SZ'，提取前6位
                code = ts_code.split('.')[0]
                stock_codes.append(code)
            return stock_codes
        return []
    except Exception as e:
        return []


def batch_get_concepts(pro):
    """
    批量获取所有股票的概念
    
    Returns:
        dict: {股票代码: [概念列表]}
    """
    print("\n开始批量获取股票概念...")
    
    # 获取所有概念板块
    concepts = get_all_concepts(pro)
    
    if concepts.empty:
        print("未获取到概念板块数据")
        return {}
    
    stock_concepts = {}  # {股票代码: [概念列表]}
    
    # 遍历每个概念板块
    for idx, row in tqdm(concepts.iterrows(), total=len(concepts), desc="获取概念成分股"):
        concept_code = row['code']
        concept_name = row['name']
        
        # 跳过不相关的概念
        if any(skip in concept_name for skip in ['昨日', '涨停', '连板', '破板', '破发']):
            continue
        
        # 获取该概念的成分股
        stock_codes = get_concept_stocks(pro, concept_code)
        
        for code in stock_codes:
            if code not in stock_concepts:
                stock_concepts[code] = []
            stock_concepts[code].append(concept_name)
        
        # 避免请求过快（Tushare 有频率限制）
        time.sleep(0.2)
    
    # 为每只股票选择前两个概念
    stock_concept_dict = {}
    for code, concepts_list in stock_concepts.items():
        if len(concepts_list) >= 2:
            stock_concept_dict[code] = f"{concepts_list[0]}+{concepts_list[1]}"
        elif len(concepts_list) == 1:
            stock_concept_dict[code] = concepts_list[0]
    
    return stock_concept_dict


def get_single_stock_concept(pro, stock_code):
    """
    获取单只股票的概念
    
    Args:
        pro: Tushare pro API
        stock_code: 股票代码（6位）
    
    Returns:
        str: 概念字符串，格式如 "概念1+概念2"
    """
    try:
        # 判断市场
        if stock_code.startswith('6'):
            ts_code = f"{stock_code}.SH"
        else:
            ts_code = f"{stock_code}.SZ"
        
        # 获取股票所属概念
        concepts = pro.concept_detail(ts_code=ts_code, fields='name')
        
        if concepts is not None and not concepts.empty:
            concept_list = concepts['name'].tolist()
            
            # 过滤不相关的概念
            concept_list = [c for c in concept_list 
                          if not any(skip in c for skip in ['昨日', '涨停', '连板', '破板', '破发'])]
            
            if len(concept_list) >= 2:
                return f"{concept_list[0]}+{concept_list[1]}"
            elif len(concept_list) == 1:
                return concept_list[0]
        
        return ''
    except Exception as e:
        return ''


def main():
    print("=" * 60)
    print("使用 Tushare API 获取股票概念信息")
    print("=" * 60)
    
    # 0. 初始化 Tushare
    print("\n0. 初始化 Tushare API...")
    pro = init_tushare()
    
    if pro is None:
        print("\n请检查：")
        print("1. 是否已安装 tushare: pip install tushare")
        print("2. Token 是否正确")
        print("3. 网络连接是否正常")
        return
    
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
        existing_concepts = dict(zip(
            concept_cache['股票代码'].astype(str).str.zfill(6), 
            concept_cache['概念']
        ))
        print(f"已有 {len(existing_concepts)} 只股票的概念")
    except:
        print("没有找到概念缓存文件")
    
    # 3. 批量获取概念
    print("\n2. 批量获取股票概念...")
    print("预计需要5-10分钟（取决于 Tushare 接口速度）...")
    new_concepts = batch_get_concepts(pro)
    print(f"\n批量获取到 {len(new_concepts)} 只股票的概念")
    
    # 4. 合并概念数据
    all_concepts = {**new_concepts, **existing_concepts}
    
    # 5. 对于仍然缺失的股票，逐个查询
    missing_stocks = [code for code in stocks_need_concept if code not in all_concepts]
    
    if missing_stocks:
        print(f"\n3. 逐个查询剩余 {len(missing_stocks)} 只股票...")
        for stock_code in tqdm(missing_stocks, desc="逐个查询"):
            concept = get_single_stock_concept(pro, stock_code)
            if concept:
                all_concepts[stock_code] = concept
            time.sleep(0.3)  # Tushare 有频率限制
    
    print(f"\n总计获取到 {len(all_concepts)} 只股票的概念")
    
    # 6. 保存到缓存
    if all_concepts:
        concept_df = pd.DataFrame({
            '股票代码': list(all_concepts.keys()),
            '概念': list(all_concepts.values())
        })
        concept_df.to_csv(concept_cache_file, index=False, encoding='utf-8-sig')
        print(f"\n已保存到: {concept_cache_file}")
    
    # 7. 统计覆盖率
    stocks_with_concept = set(all_concepts.keys())
    stocks_need_set = set(stocks_need_concept)
    coverage = len(stocks_with_concept & stocks_need_set) / len(stocks_need_set) * 100
    print(f"\n概念覆盖率: {coverage:.1f}%")
    print(f"有概念: {len(stocks_with_concept & stocks_need_set)} 只")
    print(f"无概念: {len(stocks_need_set - stocks_with_concept)} 只")
    
    if len(stocks_need_set - stocks_with_concept) > 0:
        print("\n无概念的股票（前10只）:")
        for code in list(stocks_need_set - stocks_with_concept)[:10]:
            stock_name = board_df[
                board_df['股票代码'].astype(str).str.zfill(6) == code
            ]['股票名称'].iloc[0]
            print(f"  {code} {stock_name}")
    
    print("\n" + "=" * 60)
    print("完成！现在可以运行 python premium_table_v3.py 生成表格")
    print("=" * 60)
    
    print("\n提示：")
    print("- Tushare 数据质量高，更新及时")
    print("- 如需补充缺失概念，可编辑 manual_concepts.py")
    print("- 详见：概念获取_完整指南.md")


if __name__ == "__main__":
    main()
