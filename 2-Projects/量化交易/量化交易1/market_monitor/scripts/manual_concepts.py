# -*- coding: utf-8 -*-
"""
手动维护的股票概念映射
用于快速生成连板溢价表，避免每次都从API获取
"""

# 手动维护的概念字典
# 格式：'股票代码': '概念1+概念2'
MANUAL_CONCEPTS = {
    # 12月热门股票概念（示例）
    '002792': '卫星互联网+商业航天',  # 通宇通讯
    '003018': 'AI+算力',  # 金富科技
    '002653': '医药+医疗器械',  # 海思科（假设）
    '000078': '食品+预制菜',  # 海欣食品
    '000963': '医药+中药',  # 华东医药（假设）
    
    # 可以继续添加更多股票...
    # 建议：运行一次后，查看output/连板溢价表_最终版.csv
    # 找出没有概念的股票，手动添加到这里
}


def get_manual_concept(stock_code):
    """
    获取手动维护的概念
    
    Args:
        stock_code: 股票代码（字符串）
    
    Returns:
        str: 概念字符串，如 "概念1+概念2"，如果没有则返回空字符串
    """
    return MANUAL_CONCEPTS.get(str(stock_code), '')


def add_concept(stock_code, concept):
    """
    添加概念到字典（运行时添加，不会保存到文件）
    
    Args:
        stock_code: 股票代码
        concept: 概念字符串，格式如 "概念1+概念2"
    """
    MANUAL_CONCEPTS[str(stock_code)] = concept


def get_all_concepts():
    """获取所有手动维护的概念"""
    return MANUAL_CONCEPTS.copy()


if __name__ == "__main__":
    # 测试
    print("手动维护的概念数量:", len(MANUAL_CONCEPTS))
    print("\n示例概念:")
    for code, concept in list(MANUAL_CONCEPTS.items())[:5]:
        print(f"  {code}: {concept}")
