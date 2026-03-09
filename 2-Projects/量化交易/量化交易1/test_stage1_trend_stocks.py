"""测试Stage1 Agent的趋势股识别功能"""

import sys
import os
import importlib.util

# 添加项目路径
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# 动态导入模块
agent_path = os.path.join(project_dir, "Ashare复盘multi-agents", "next_day_expectation_agent", "src", "stage1", "stage1_agent.py")
spec = importlib.util.spec_from_file_location("stage1_agent", agent_path)
stage1_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage1_module)

Stage1Agent = stage1_module.Stage1Agent

def main():
    """运行Stage1 Agent测试"""
    date = "2026-02-13"
    
    print(f"开始运行Stage1 Agent: {date}")
    print("=" * 60)
    
    # 创建Stage1 Agent实例
    agent = Stage1Agent()
    
    # 运行分析
    result = agent.run(date)
    
    # 输出结果
    print("\n基因池统计:")
    print(f"连板股: {len(result['gene_pool']['continuous_limit_up'])} 只")
    print(f"炸板股: {len(result['gene_pool']['failed_limit_up'])} 只")
    print(f"辨识度个股: {len(result['gene_pool']['recognition_stocks'])} 只")
    print(f"趋势股: {len(result['gene_pool']['trend_stocks'])} 只")
    print(f"总计: {len(result['gene_pool']['all_stocks'])} 只")
    
    # 输出趋势股详情
    if result['gene_pool']['trend_stocks']:
        print("\n趋势股详情:")
        for stock in result['gene_pool']['trend_stocks']:
            print(f"  {stock['code']} {stock['name']}: "
                  f"价格={stock['price']:.2f}, "
                  f"MA5距离={stock['technical_levels']['distance_to_ma5_pct']:.2f}%")
    else:
        print("\n未识别到趋势股")
        print("\n连板股技术位分析:")
        for stock in result['gene_pool']['continuous_limit_up'][:3]:  # 只显示前3只
            tl = stock['technical_levels']
            print(f"  {stock['code']} {stock['name']}: "
                  f"价格={stock['price']:.2f}, "
                  f"MA5距离={tl['distance_to_ma5_pct']:.2f}%, "
                  f"MA5={tl['ma5']:.2f}, MA10={tl['ma10']:.2f}, MA20={tl['ma20']:.2f}")
    
    print("\n" + "=" * 60)
    print("测试完成")

if __name__ == "__main__":
    main()
