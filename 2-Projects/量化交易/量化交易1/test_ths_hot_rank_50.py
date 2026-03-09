#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试获取同花顺热门股前50名
"""

import sys
import os

# 添加kaipanla_crawler到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'kaipanla_crawler'))

from kaipanla_crawler import KaipanlaCrawler
import pandas as pd
from datetime import datetime


def test_ths_hot_rank_50():
    """测试获取同花顺热门股前50名"""
    
    print('=' * 80)
    print('测试：获取同花顺热门股前50名')
    print('=' * 80)
    print()
    
    # 创建爬虫实例
    crawler = KaipanlaCrawler()
    
    print('开始获取同花顺热门股数据...')
    print('注意：首次运行需要安装selenium和chromedriver')
    print('这个过程可能需要几秒钟，请耐心等待...')
    print()
    
    try:
        # 获取前50名热门股
        # headless=False 可以看到浏览器操作过程
        # wait_time=5 等待页面加载5秒
        series = crawler.get_ths_hot_rank(
            headless=False,  # 显示浏览器窗口，方便调试
            wait_time=5,
            max_rank=50
        )
        
        if series.empty:
            print('❌ 失败：未获取到数据')
            return False
        
        # 显示结果
        print('✅ 成功获取数据！')
        print()
        print(f'获取到 {len(series)} 只热门股')
        print('=' * 80)
        print()
        
        # 显示前10名
        print('前10名热门股：')
        print('-' * 80)
        for rank, stock_name in series.head(10).items():
            print(f'  {rank:2d}. {stock_name}')
        print()
        
        # 显示41-50名
        if len(series) >= 50:
            print('第41-50名热门股：')
            print('-' * 80)
            for rank, stock_name in series.tail(10).items():
                print(f'  {rank:2d}. {stock_name}')
            print()
        
        # 显示完整列表
        print('完整列表：')
        print('=' * 80)
        print(series.to_string())
        print()
        
        # 保存到CSV文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'ths_hot_rank_50_{timestamp}.csv'
        series.to_csv(output_file, encoding='utf-8-sig', header=['股票名称'])
        print(f'✅ 数据已保存到: {output_file}')
        print()
        
        # 数据验证
        print('数据验证：')
        print('-' * 80)
        print(f'  期望数量: 50')
        print(f'  实际数量: {len(series)}')
        print(f'  数据类型: {type(series)}')
        print(f'  索引类型: {type(series.index)}')
        print(f'  索引范围: {series.index.min()} - {series.index.max()}')
        print()
        
        if len(series) == 50:
            print('✅ 测试通过：成功获取50只热门股')
            return True
        else:
            print(f'⚠️  警告：获取到{len(series)}只股票，少于预期的50只')
            print('   可能原因：')
            print('   1. 页面加载时间不够，可以增加wait_time参数')
            print('   2. 网页结构发生变化')
            print('   3. 当前市场热门股不足50只')
            return False
            
    except Exception as e:
        print(f'❌ 错误：{e}')
        print()
        print('可能的解决方案：')
        print('1. 确保已安装selenium: pip install selenium')
        print('2. 确保已安装chromedriver并配置到PATH')
        print('3. 检查网络连接')
        print('4. 增加wait_time参数值')
        return False


if __name__ == '__main__':
    print()
    print('同花顺热门股前50名获取测试')
    print('=' * 80)
    print()
    
    success = test_ths_hot_rank_50()
    
    print()
    print('=' * 80)
    if success:
        print('✅ 测试完成：功能正常')
    else:
        print('❌ 测试失败：请检查错误信息')
    print('=' * 80)
    print()
