#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复同花顺热门股获取 - 添加滚动功能以加载更多数据
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'kaipanla_crawler'))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
import time


def get_ths_hot_rank_with_scroll(headless=True, wait_time=5, timeout=300, max_rank=50):
    """获取同花顺热榜个股数据（带滚动功能）
    
    Args:
        headless: 是否使用无头模式
        wait_time: 页面加载后等待时间（秒）
        timeout: 操作超时时间（秒）
        max_rank: 最大获取排名数，默认50
    
    Returns:
        pd.Series: index为排名，values为个股名字
    """
    url = "https://eq.10jqka.com.cn/frontend/thsTopRank/index.html#/"
    
    # 配置Chrome选项
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = None
    try:
        # 初始化浏览器
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(timeout)
        
        print(f"访问同花顺热门股页面...")
        driver.get(url)
        
        # 等待页面加载
        print(f"等待页面加载 ({wait_time} 秒)...")
        time.sleep(wait_time)
        
        result = {}
        last_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 10  # 最多滚动10次
        
        print(f"\n开始获取数据，目标: {max_rank} 只股票")
        print("=" * 80)
        
        while len(result) < max_rank and scroll_attempts < max_scroll_attempts:
            # 尝试获取当前可见的所有数据
            for rank in range(1, max_rank + 1):
                if rank in result:
                    continue  # 已经获取过的跳过
                
                try:
                    rank_xpath = f'/html/body/div[1]/div/div[3]/div/div[1]/div/div[2]/div[1]/div/div[{rank}]/div[1]/div[1]/div'
                    name_xpath = f'/html/body/div[1]/div/div[3]/div/div[1]/div/div[2]/div[1]/div/div[{rank}]/div[1]/div[2]/span'
                    
                    # 获取排名
                    rank_element = driver.find_element(By.XPATH, rank_xpath)
                    rank_value = rank_element.text.strip()
                    
                    # 获取名字
                    name_element = driver.find_element(By.XPATH, name_xpath)
                    name_value = name_element.text.strip()
                    
                    result[rank] = name_value
                    
                    if len(result) % 10 == 0:
                        print(f"已获取 {len(result)} 只股票...")
                    
                except (NoSuchElementException, Exception):
                    # 找不到元素，说明需要滚动
                    break
            
            # 检查是否有新数据
            if len(result) == last_count:
                # 没有新数据，尝试滚动页面
                print(f"\n滚动页面以加载更多数据 (尝试 {scroll_attempts + 1}/{max_scroll_attempts})...")
                
                # 找到列表容器并滚动
                try:
                    # 方法1: 滚动到页面底部
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)  # 等待加载
                    
                    # 方法2: 尝试找到列表容器并滚动
                    try:
                        list_container = driver.find_element(By.XPATH, '/html/body/div[1]/div/div[3]/div/div[1]/div/div[2]/div[1]/div')
                        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", list_container)
                        time.sleep(2)  # 等待加载
                    except:
                        pass
                    
                except Exception as e:
                    print(f"滚动失败: {e}")
                
                scroll_attempts += 1
            else:
                last_count = len(result)
                scroll_attempts = 0  # 重置滚动计数
            
            # 如果已经获取到足够的数据，退出
            if len(result) >= max_rank:
                break
        
        # 关闭浏览器
        driver.quit()
        
        if not result:
            print("\n未获取到数据")
            return pd.Series()
        
        # 转换为Series
        series = pd.Series(result)
        series.index.name = 'Rank'
        series.name = 'Stock Name'
        
        print(f"\n总共获取: {len(series)} 只股票")
        return series
        
    except Exception as e:
        print(f"\n爬取失败: {e}")
        if driver:
            driver.quit()
        return pd.Series()


def test_with_scroll():
    """测试带滚动功能的获取"""
    print('=' * 80)
    print('测试：获取同花顺热门股前50名（带滚动功能）')
    print('=' * 80)
    print()
    
    series = get_ths_hot_rank_with_scroll(
        headless=False,  # 显示浏览器，方便观察
        wait_time=5,
        max_rank=50
    )
    
    if series.empty:
        print('\n❌ 失败：未获取到数据')
        return False
    
    print('\n' + '=' * 80)
    print(f'✅ 成功获取 {len(series)} 只热门股')
    print('=' * 80)
    print()
    
    # 显示前10名
    print('前10名：')
    print('-' * 80)
    for rank, name in series.head(10).items():
        print(f'  {rank:2d}. {name}')
    print()
    
    # 如果获取到40+，显示最后10名
    if len(series) >= 40:
        print(f'第{len(series)-9}-{len(series)}名：')
        print('-' * 80)
        for rank, name in series.tail(10).items():
            print(f'  {rank:2d}. {name}')
        print()
    
    # 保存结果
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ths_hot_rank_scroll_{timestamp}.csv'
    series.to_csv(output_file, encoding='utf-8-sig', header=['股票名称'])
    print(f'✅ 数据已保存到: {output_file}')
    print()
    
    # 验证
    print('数据验证：')
    print('-' * 80)
    print(f'  期望数量: 50')
    print(f'  实际数量: {len(series)}')
    print(f'  完成度: {len(series)/50*100:.1f}%')
    print()
    
    if len(series) >= 50:
        print('✅ 测试通过：成功获取50只热门股')
        return True
    elif len(series) >= 40:
        print('⚠️  部分成功：获取到40+只股票，接近目标')
        return True
    else:
        print(f'❌ 测试失败：只获取到{len(series)}只股票')
        return False


if __name__ == '__main__':
    print()
    print('同花顺热门股前50名获取测试（改进版）')
    print('=' * 80)
    print()
    
    success = test_with_scroll()
    
    print()
    print('=' * 80)
    if success:
        print('✅ 测试完成')
    else:
        print('❌ 测试失败')
    print('=' * 80)
    print()
