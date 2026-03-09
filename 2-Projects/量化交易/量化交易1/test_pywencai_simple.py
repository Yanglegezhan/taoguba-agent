"""简单测试 pywencai 获取同花顺热门股"""

import pywencai
import pandas as pd

def test_basic_query():
    """测试基础查询"""
    print("=" * 60)
    print("测试1: 基础查询 - 同花顺热度排名前20")
    print("=" * 60)
    
    try:
        # 查询同花顺热度排名前20
        query = "同花顺热度排名前20"
        print(f"查询语句: {query}")
        print("正在查询...")
        
        result = pywencai.get(query=query, loop=True)
        
        # 检查返回类型
        if result is None:
            print("✗ 查询返回 None")
            return False
        
        # 如果是字典，转换为 DataFrame
        if isinstance(result, dict):
            print(f"返回类型: dict，键: {list(result.keys())}")
            # 尝试从字典中提取 DataFrame
            if 'data' in result:
                df = pd.DataFrame(result['data'])
            else:
                df = pd.DataFrame(result)
        else:
            df = result
        
        if df.empty:
            print("✗ 查询返回空数据")
            return False
        
        print(f"✓ 成功获取 {len(df)} 条数据")
        print(f"\n列名: {df.columns.tolist()}")
        
        # 尝试找到股票名称列
        name_column = None
        for col in ['股票名称', '股票简称', '名称', 'name', '证券简称']:
            if col in df.columns:
                name_column = col
                break
        
        if name_column:
            print(f"\n前10名热门股（列名: {name_column}）:")
            for i, name in enumerate(df[name_column].head(10), 1):
                print(f"  {i}. {name}")
        else:
            print("\n前5行数据:")
            print(df.head())
        
        return True
        
    except Exception as e:
        print(f"✗ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_date():
    """测试带日期的查询"""
    print("\n" + "=" * 60)
    print("测试2: 带日期查询 - 2026-02-13的热门股")
    print("=" * 60)
    
    try:
        # 查询指定日期的热门股
        query = "2026-02-13，同花顺热度排名前10"
        print(f"查询语句: {query}")
        print("正在查询...")
        
        result = pywencai.get(query=query, loop=True)
        
        if result is None:
            print("✗ 查询返回 None")
            return False
        
        # 如果是字典，转换为 DataFrame
        if isinstance(result, dict):
            if 'data' in result:
                df = pd.DataFrame(result['data'])
            else:
                df = pd.DataFrame(result)
        else:
            df = result
        
        if df.empty:
            print("✗ 查询返回空数据（可能是未来日期）")
            return False
        
        print(f"✓ 成功获取 {len(df)} 条数据")
        
        # 尝试找到股票名称列
        name_column = None
        for col in ['股票名称', '股票简称', '名称', 'name', '证券简称']:
            if col in df.columns:
                name_column = col
                break
        
        if name_column:
            print(f"\n热门股列表:")
            for i, name in enumerate(df[name_column], 1):
                print(f"  {i}. {name}")
        
        return True
        
    except Exception as e:
        print(f"✗ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_stock_codes():
    """测试获取股票代码"""
    print("\n" + "=" * 60)
    print("测试3: 获取股票代码")
    print("=" * 60)
    
    try:
        query = "同花顺热度排名前10"
        print(f"查询语句: {query}")
        print("正在查询...")
        
        result = pywencai.get(query=query, loop=True)
        
        if result is None:
            print("✗ 查询返回 None")
            return False
        
        # 如果是字典，转换为 DataFrame
        if isinstance(result, dict):
            if 'data' in result:
                df = pd.DataFrame(result['data'])
            else:
                df = pd.DataFrame(result)
        else:
            df = result
        
        if df.empty:
            print("✗ 查询返回空数据")
            return False
        
        # 查找代码列
        code_column = None
        for col in ['股票代码', '代码', 'code', 'stock_code', '证券代码']:
            if col in df.columns:
                code_column = col
                break
        
        # 查找名称列
        name_column = None
        for col in ['股票名称', '股票简称', '名称', 'name', '证券简称']:
            if col in df.columns:
                name_column = col
                break
        
        if code_column and name_column:
            print(f"✓ 成功获取股票代码和名称")
            print(f"\n代码列: {code_column}, 名称列: {name_column}")
            print("\n热门股列表:")
            for i, (code, name) in enumerate(zip(df[code_column], df[name_column]), 1):
                print(f"  {i}. {code} - {name}")
        elif name_column:
            print(f"✓ 获取到名称，但没有代码列")
            print(f"\n可用列: {df.columns.tolist()}")
        else:
            print("✗ 无法识别股票名称列")
            print(f"\n可用列: {df.columns.tolist()}")
        
        return True
        
    except Exception as e:
        print(f"✗ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有测试"""
    print("开始测试 pywencai 功能\n")
    
    # 测试1: 基础查询
    success1 = test_basic_query()
    
    # 测试2: 带日期查询
    success2 = test_with_date()
    
    # 测试3: 获取股票代码
    success3 = test_stock_codes()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"基础查询: {'✓ 通过' if success1 else '✗ 失败'}")
    print(f"带日期查询: {'✓ 通过' if success2 else '✗ 失败'}")
    print(f"获取代码: {'✓ 通过' if success3 else '✗ 失败'}")
    
    if success1:
        print("\n✓ pywencai 可以正常使用！")
    else:
        print("\n✗ pywencai 存在问题，请检查网络连接")

if __name__ == "__main__":
    main()
