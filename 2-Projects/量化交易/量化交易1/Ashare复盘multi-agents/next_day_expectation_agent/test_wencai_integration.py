"""测试 wencai 集成到基因池构建器"""

import sys
from pathlib import Path

# 添加 src 到路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from stage1.gene_pool_builder import GenePoolBuilder

def test_get_hot_stocks():
    """测试获取热门股"""
    print("=" * 60)
    print("测试1: 使用 wencai 获取热门股")
    print("=" * 60)
    
    try:
        # 创建配置 - 使用 wencai
        config = {
            'use_wencai': True,
            'wencai_fallback': True
        }
        
        print("\n配置:")
        print(f"  use_wencai: {config['use_wencai']}")
        print(f"  wencai_fallback: {config['wencai_fallback']}")
        
        # 创建基因池构建器
        print("\n正在初始化基因池构建器...")
        builder = GenePoolBuilder(config=config)
        
        # 测试获取热门股
        print("\n正在获取热门股前20...")
        hot_stocks = builder._get_hot_stocks(max_rank=20)
        
        if hot_stocks.empty:
            print("✗ 获取热门股失败")
            return False
        
        print(f"✓ 成功获取 {len(hot_stocks)} 只热门股")
        print("\n前10名:")
        for rank, name in list(hot_stocks.items())[:10]:
            print(f"  {rank}. {name}")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_identify_recognition_stocks():
    """测试识别辨识度个股"""
    print("\n" + "=" * 60)
    print("测试2: 识别辨识度个股（使用 wencai）")
    print("=" * 60)
    
    try:
        # 创建配置
        config = {
            'use_wencai': True,
            'wencai_fallback': True
        }
        
        # 创建基因池构建器
        print("\n正在初始化基因池构建器...")
        builder = GenePoolBuilder(config=config)
        
        # 识别辨识度个股
        print("\n正在识别辨识度个股...")
        date = "2026-02-16"
        recognition_stocks = builder.identify_recognition_stocks(date=date)
        
        if not recognition_stocks:
            print("✗ 未识别到辨识度个股")
            return False
        
        print(f"✓ 成功识别 {len(recognition_stocks)} 只辨识度个股")
        print("\n前10名:")
        for stock in recognition_stocks[:10]:
            print(f"  {stock.hot_rank}. {stock.name}")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行所有测试"""
    print("开始测试 wencai 集成到基因池构建器\n")
    
    success1 = test_get_hot_stocks()
    success2 = test_identify_recognition_stocks()
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"获取热门股: {'✓ 通过' if success1 else '✗ 失败'}")
    print(f"识别辨识度个股: {'✓ 通过' if success2 else '✗ 失败'}")
    
    if success1 and success2:
        print("\n✓ 所有测试通过！")
        print("\n基因池构建器已成功集成 pywencai")
        print("获取同花顺热门股时会优先使用问财（速度更快）")
    else:
        print("\n✗ 部分测试失败")

if __name__ == "__main__":
    main()
