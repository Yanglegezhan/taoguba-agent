"""调试 pywencai 返回格式"""

import pywencai
import pandas as pd

def test_different_queries():
    """测试不同的查询语句"""
    queries = [
        "同花顺热度排名前10",
        "同花顺人气榜前10",
        "同花顺关注度排名前10",
        "热门股票前10",
        "今日热门股票",
    ]
    
    for query in queries:
        print("=" * 60)
        print(f"测试查询: {query}")
        print("=" * 60)
        
        try:
            result = pywencai.get(query=query, loop=True)
            
            if isinstance(result, dict):
                print(f"字典键: {list(result.keys())}")
                
                # 尝试找到包含股票数据的键
                for key, value in result.items():
                    if isinstance(value, pd.DataFrame) and not value.empty:
                        print(f"\n键 '{key}' 包含 DataFrame:")
                        print(f"  形状: {value.shape}")
                        print(f"  列名: {value.columns.tolist()}")
                        
                        # 检查是否包含股票相关列
                        stock_columns = [col for col in value.columns if any(
                            keyword in str(col) for keyword in ['股票', '代码', '名称', '简称', '证券']
                        )]
                        if stock_columns:
                            print(f"  股票相关列: {stock_columns}")
                            print(f"\n  前3行:")
                            print(value[stock_columns].head(3))
                        else:
                            print(f"\n  前3行:")
                            print(value.head(3))
            
            elif isinstance(result, pd.DataFrame):
                print(f"直接返回 DataFrame:")
                print(f"  形状: {result.shape}")
                print(f"  列名: {result.columns.tolist()}")
                print(f"\n  前5行:")
                print(result.head())
            
            print()
            
        except Exception as e:
            print(f"查询失败: {e}\n")

if __name__ == "__main__":
    test_different_queries()
