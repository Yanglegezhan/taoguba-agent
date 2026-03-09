"""测试使用 pywencai 获取同花顺热门股"""

import sys
import os
import importlib.util

# 添加项目路径
project_dir = os.path.dirname(os.path.abspath(__file__))
wencai_client_path = os.path.join(
    project_dir, 
    "Ashare复盘multi-agents", 
    "next_day_expectation_agent", 
    "src", 
    "data_sources", 
    "wencai_client.py"
)

def test_wencai_import():
    """测试 pywencai 是否已安装"""
    print("=" * 60)
    print("测试1: 检查 pywencai 是否已安装")
    print("=" * 60)
    
    try:
        import pywencai
        print("✓ pywencai 已安装")
        print(f"  版本: {pywencai.__version__ if hasattr(pywencai, '__version__') else '未知'}")
        return True
    except ImportError:
        print("✗ pywencai 未安装")
        print("  请运行: pip install pywencai")
        return False

def test_wencai_client():
    """测试 WencaiClient 初始化"""
    print("\n" + "=" * 60)
    print("测试2: 初始化 WencaiClient")
    print("=" * 60)
    
    try:
        # 动态导入 wencai_client 模块
        spec = importlib.util.spec_from_file_location("wencai_client", wencai_client_path)
        wencai_module = importlib.util.module_from_spec(spec)
        
        # 先导入依赖的 logger 模块
        logger_path = os.path.join(
            project_dir,
            "Ashare复盘multi-agents",
            "next_day_expectation_agent",
            "src",
            "common",
            "logger.py"
        )
        logger_spec = importlib.util.spec_from_file_location("logger", logger_path)
        logger_module = importlib.util.module_from_spec(logger_spec)
        sys.modules['logger'] = logger_module
        logger_spec.loader.exec_module(logger_module)
        
        # 执行模块
        spec.loader.exec_module(wencai_module)
        
        WencaiClient = wencai_module.WencaiClient
        client = WencaiClient()
        print("✓ WencaiClient 初始化成功")
        return client
    except Exception as e:
        print(f"✗ WencaiClient 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_get_hot_stocks(client):
    """测试获取热门股"""
    print("\n" + "=" * 60)
    print("测试3: 获取同花顺热门股前20")
    print("=" * 60)
    
    try:
        # 测试获取热门股（简化版）
        hot_stocks = client.get_hot_stocks_simple(max_rank=20)
        
        if hot_stocks.empty:
            print("✗ 返回数据为空")
            return False
        
        print(f"✓ 成功获取 {len(hot_stocks)} 只热门股")
        print("\n前10名热门股:")
        for rank, name in list(hot_stocks.items())[:10]:
            print(f"  {rank}. {name}")
        
        return True
        
    except Exception as e:
        print(f"✗ 获取热门股失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_get_hot_stocks_with_codes(client):
    """测试获取带股票代码的热门股"""
    print("\n" + "=" * 60)
    print("测试4: 获取带股票代码的热门股")
    print("=" * 60)
    
    try:
        # 测试获取完整数据
        df = client.get_hot_stocks_with_codes(max_rank=20)
        
        if df.empty:
            print("✗ 返回数据为空")
            return False
        
        print(f"✓ 成功获取 {len(df)} 只热门股（含代码）")
        print(f"\n列名: {df.columns.tolist()}")
        print("\n前5名热门股:")
        print(df.head().to_string(index=False))
        
        return True
        
    except Exception as e:
        print(f"✗ 获取热门股失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有测试"""
    print("开始测试 pywencai 获取同花顺热门股功能")
    print()
    
    # 测试1: 检查安装
    if not test_wencai_import():
        print("\n请先安装 pywencai: pip install pywencai")
        return
    
    # 测试2: 初始化客户端
    client = test_wencai_client()
    if not client:
        return
    
    # 测试3: 获取热门股（简化版）
    test_get_hot_stocks(client)
    
    # 测试4: 获取热门股（含代码）
    test_get_hot_stocks_with_codes(client)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
