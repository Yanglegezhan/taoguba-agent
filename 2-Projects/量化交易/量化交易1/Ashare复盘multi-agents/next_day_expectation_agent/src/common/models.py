"""
数据模型定义

本模块定义了系统中使用的所有核心数据结构，包括：
- Stock: 个股基础信息
- TechnicalLevels: 技术位数据
- GenePool: 基因库
- BaselineExpectation: 基准预期
- AuctionData: 竞价数据
- ExpectationScore: 超预期分值
- AdditionalPool: 附加票池
- StatusScore: 地位分值
- SignalPlaybook: 信号剧本
- DecisionTree: 决策树
- NavigationReport: 决策导航报告
- MarketReport: 大盘分析报告
- EmotionReport: 情绪分析报告
- ThemeReport: 题材分析报告
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
import json


@dataclass
class TechnicalLevels:
    """技术位数据"""
    ma5: float                      # 5日均线
    ma10: float                     # 10日均线
    ma20: float                     # 20日均线
    previous_high: float            # 前期高点
    chip_zone_low: float            # 筹码密集区下沿
    chip_zone_high: float           # 筹码密集区上沿
    distance_to_ma5_pct: float      # 距离5日均线百分比
    distance_to_high_pct: float     # 距离前高百分比
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TechnicalLevels':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class Stock:
    """个股基础信息"""
    code: str                       # 股票代码
    name: str                       # 股票名称
    market_cap: float               # 流通市值（亿元）
    price: float                    # 当前价格
    change_pct: float               # 涨跌幅
    volume: float                   # 成交量
    amount: float                   # 成交额（万元）
    turnover_rate: float            # 换手率
    board_height: int               # 连板高度
    themes: List[str]               # 所属题材
    technical_levels: Optional[TechnicalLevels] = None  # 技术位
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        if self.technical_levels:
            data['technical_levels'] = self.technical_levels.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Stock':
        """从字典创建实例"""
        if 'technical_levels' in data and data['technical_levels']:
            data['technical_levels'] = TechnicalLevels.from_dict(data['technical_levels'])
        return cls(**data)


@dataclass
class GenePool:
    """基因库"""
    date: str                                   # 日期
    continuous_limit_up: List[Stock]            # 连板梯队
    failed_limit_up: List[Stock]                # 炸板股
    recognition_stocks: List[Stock]             # 辨识度个股
    trend_stocks: List[Stock]                   # 趋势股
    all_stocks: Dict[str, Stock] = field(default_factory=dict)  # 所有个股字典（code -> Stock）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'date': self.date,
            'continuous_limit_up': [stock.to_dict() for stock in self.continuous_limit_up],
            'failed_limit_up': [stock.to_dict() for stock in self.failed_limit_up],
            'recognition_stocks': [stock.to_dict() for stock in self.recognition_stocks],
            'trend_stocks': [stock.to_dict() for stock in self.trend_stocks],
            'all_stocks': {code: stock.to_dict() for code, stock in self.all_stocks.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GenePool':
        """从字典创建实例"""
        return cls(
            date=data['date'],
            continuous_limit_up=[Stock.from_dict(s) for s in data.get('continuous_limit_up', [])],
            failed_limit_up=[Stock.from_dict(s) for s in data.get('failed_limit_up', [])],
            recognition_stocks=[Stock.from_dict(s) for s in data.get('recognition_stocks', [])],
            trend_stocks=[Stock.from_dict(s) for s in data.get('trend_stocks', [])],
            all_stocks={code: Stock.from_dict(s) for code, s in data.get('all_stocks', {}).items()}
        )


@dataclass
class BaselineExpectation:
    """基准预期"""
    stock_code: str                 # 股票代码
    stock_name: str                 # 股票名称
    expected_open_min: float        # 预期开盘涨幅下限（%）
    expected_open_max: float        # 预期开盘涨幅上限（%）
    expected_amount_min: float      # 预期竞价金额下限（万元）
    logic: str                      # 计算逻辑说明
    confidence: float               # 置信度（0-1）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaselineExpectation':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class AuctionData:
    """竞价数据"""
    stock_code: str                 # 股票代码
    auction_low_price: float        # 竞价最低价
    auction_high_price: float       # 竞价最高价
    open_price: float               # 开盘价
    auction_volume: float           # 竞价成交量
    auction_amount: float           # 竞价成交额（万元）
    seal_amount: float              # 封单金额（万元，涨停时）
    withdrawal_detected: bool       # 是否检测到撤单
    trajectory_rating: str          # 轨迹评级（强/中/弱）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuctionData':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class ExpectationScore:
    """超预期分值"""
    stock_code: str                 # 股票代码
    volume_score: float             # 量能分值（0-100）
    price_score: float              # 价格分值（0-100）
    independence_score: float       # 独立性分值（0-100）
    total_score: float              # 总分（0-100）
    rating: str                     # 评级（优秀/良好/一般/较差）
    recommendation: str             # 操作建议（打板/低吸/观望/撤退）
    confidence: float               # 置信度（0-1）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExpectationScore':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class StatusScore:
    """地位分值"""
    stock_code: str                 # 股票代码
    theme_recognition: float        # 题材辨识度（0-100）
    urgency: float                  # 量价急迫性（0-100）
    emotion_hedge: float            # 情绪对冲力（0-100）
    total_score: float              # 总分（0-100）
    rank: int                       # 排名
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StatusScore':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class AdditionalPool:
    """附加票池"""
    date: str                               # 日期
    top_seals: List[Stock]                  # 顶级封单池
    rush_positioning: List[Stock]           # 急迫抢筹池
    energy_burst: List[Stock]               # 能量爆发池
    reverse_nuclear: List[Stock]            # 极端反核池
    sector_formation: List[Stock]           # 板块阵型池
    final_candidates: List[Stock]           # 最终候选（经过地位判定）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'date': self.date,
            'top_seals': [stock.to_dict() for stock in self.top_seals],
            'rush_positioning': [stock.to_dict() for stock in self.rush_positioning],
            'energy_burst': [stock.to_dict() for stock in self.energy_burst],
            'reverse_nuclear': [stock.to_dict() for stock in self.reverse_nuclear],
            'sector_formation': [stock.to_dict() for stock in self.sector_formation],
            'final_candidates': [stock.to_dict() for stock in self.final_candidates]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdditionalPool':
        """从字典创建实例"""
        return cls(
            date=data['date'],
            top_seals=[Stock.from_dict(s) for s in data.get('top_seals', [])],
            rush_positioning=[Stock.from_dict(s) for s in data.get('rush_positioning', [])],
            energy_burst=[Stock.from_dict(s) for s in data.get('energy_burst', [])],
            reverse_nuclear=[Stock.from_dict(s) for s in data.get('reverse_nuclear', [])],
            sector_formation=[Stock.from_dict(s) for s in data.get('sector_formation', [])],
            final_candidates=[Stock.from_dict(s) for s in data.get('final_candidates', [])]
        )


@dataclass
class SignalPlaybook:
    """信号剧本"""
    name: str                           # 剧本名称
    trigger_conditions: List[str]       # 触发条件
    status_judgment: str                # 地位判定
    strategy: str                       # 应对策略
    risk_level: str                     # 风险等级
    applicable_stocks: List[str]        # 适用个股代码
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SignalPlaybook':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class Scenario:
    """决策场景"""
    name: str                           # 场景名称
    trigger_condition: str              # 触发条件
    market_sentiment: str               # 盘感描述
    strategy: str                       # 具体策略
    risk_warning: str                   # 风险提示
    confidence: float                   # 置信度
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scenario':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class DecisionTree:
    """决策树"""
    scenarios: List[Scenario]           # 所有场景
    current_scenario: str               # 当前最可能的场景
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'scenarios': [scenario.to_dict() for scenario in self.scenarios],
            'current_scenario': self.current_scenario
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DecisionTree':
        """从字典创建实例"""
        return cls(
            scenarios=[Scenario.from_dict(s) for s in data.get('scenarios', [])],
            current_scenario=data.get('current_scenario', '')
        )


@dataclass
class NavigationReport:
    """决策导航报告"""
    date: str                                           # 日期
    generation_time: str                                # 生成时间
    baseline_table: Dict[str, BaselineExpectation]      # 及格线表
    signal_playbooks: List[SignalPlaybook]              # 信号剧本
    decision_tree: DecisionTree                         # 决策树
    market_summary: str                                 # 市场概况
    key_recommendations: List[str]                      # 关键建议
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'date': self.date,
            'generation_time': self.generation_time,
            'baseline_table': {code: exp.to_dict() for code, exp in self.baseline_table.items()},
            'signal_playbooks': [playbook.to_dict() for playbook in self.signal_playbooks],
            'decision_tree': self.decision_tree.to_dict(),
            'market_summary': self.market_summary,
            'key_recommendations': self.key_recommendations
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NavigationReport':
        """从字典创建实例"""
        return cls(
            date=data['date'],
            generation_time=data['generation_time'],
            baseline_table={
                code: BaselineExpectation.from_dict(exp) 
                for code, exp in data.get('baseline_table', {}).items()
            },
            signal_playbooks=[
                SignalPlaybook.from_dict(p) 
                for p in data.get('signal_playbooks', [])
            ],
            decision_tree=DecisionTree.from_dict(data.get('decision_tree', {})),
            market_summary=data.get('market_summary', ''),
            key_recommendations=data.get('key_recommendations', [])
        )



# JSON序列化和反序列化辅助函数

def save_to_json(obj: Any, filepath: str, indent: int = 2) -> None:
    """
    将数据对象保存为JSON文件
    
    Args:
        obj: 数据对象（必须有to_dict方法）
        filepath: 文件路径
        indent: JSON缩进空格数
    """
    import os
    
    # 确保目录存在
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # 转换为字典
    if hasattr(obj, 'to_dict'):
        data = obj.to_dict()
    else:
        data = obj
    
    # 写入文件
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def load_from_json(filepath: str, model_class: type) -> Any:
    """
    从JSON文件加载数据对象
    
    Args:
        filepath: 文件路径
        model_class: 数据模型类（必须有from_dict类方法）
    
    Returns:
        数据对象实例
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if hasattr(model_class, 'from_dict'):
        return model_class.from_dict(data)
    else:
        return data


def serialize_to_json_string(obj: Any, indent: int = 2) -> str:
    """
    将数据对象序列化为JSON字符串
    
    Args:
        obj: 数据对象（必须有to_dict方法）
        indent: JSON缩进空格数
    
    Returns:
        JSON字符串
    """
    if hasattr(obj, 'to_dict'):
        data = obj.to_dict()
    else:
        data = obj
    
    return json.dumps(data, ensure_ascii=False, indent=indent)


def deserialize_from_json_string(json_string: str, model_class: type) -> Any:
    """
    从JSON字符串反序列化数据对象
    
    Args:
        json_string: JSON字符串
        model_class: 数据模型类（必须有from_dict类方法）
    
    Returns:
        数据对象实例
    """
    data = json.loads(json_string)
    
    if hasattr(model_class, 'from_dict'):
        return model_class.from_dict(data)
    else:
        return data


# 批量序列化辅助函数

def save_gene_pool(gene_pool: GenePool, output_dir: str) -> str:
    """
    保存基因池到JSON文件
    
    Args:
        gene_pool: 基因池对象
        output_dir: 输出目录
    
    Returns:
        保存的文件路径
    """
    import os
    filepath = os.path.join(output_dir, f"gene_pool_{gene_pool.date}.json")
    save_to_json(gene_pool, filepath)
    return filepath


def load_gene_pool(filepath: str) -> GenePool:
    """
    从JSON文件加载基因池
    
    Args:
        filepath: 文件路径
    
    Returns:
        基因池对象
    """
    return load_from_json(filepath, GenePool)


def save_baseline_expectations(
    expectations: Dict[str, BaselineExpectation], 
    date: str, 
    output_dir: str
) -> str:
    """
    保存基准预期到JSON文件
    
    Args:
        expectations: 基准预期字典（stock_code -> BaselineExpectation）
        date: 日期
        output_dir: 输出目录
    
    Returns:
        保存的文件路径
    """
    import os
    data = {
        'date': date,
        'expectations': {code: exp.to_dict() for code, exp in expectations.items()}
    }
    filepath = os.path.join(output_dir, f"baseline_expectation_{date}.json")
    save_to_json(data, filepath)
    return filepath


def load_baseline_expectations(filepath: str) -> Dict[str, BaselineExpectation]:
    """
    从JSON文件加载基准预期
    
    Args:
        filepath: 文件路径
    
    Returns:
        基准预期字典（stock_code -> BaselineExpectation）
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return {
        code: BaselineExpectation.from_dict(exp) 
        for code, exp in data.get('expectations', {}).items()
    }


def save_navigation_report(report: NavigationReport, output_dir: str) -> str:
    """
    保存决策导航报告到JSON文件
    
    Args:
        report: 决策导航报告对象
        output_dir: 输出目录
    
    Returns:
        保存的文件路径
    """
    import os
    filepath = os.path.join(output_dir, f"decision_navigation_{report.date}.json")
    save_to_json(report, filepath)
    return filepath


def load_navigation_report(filepath: str) -> NavigationReport:
    """
    从JSON文件加载决策导航报告
    
    Args:
        filepath: 文件路径
    
    Returns:
        决策导航报告对象
    """
    return load_from_json(filepath, NavigationReport)


def save_additional_pool(pool: AdditionalPool, output_dir: str) -> str:
    """
    保存附加票池到JSON文件
    
    Args:
        pool: 附加票池对象
        output_dir: 输出目录
    
    Returns:
        保存的文件路径
    """
    import os
    filepath = os.path.join(output_dir, f"additional_pool_{pool.date}.json")
    save_to_json(pool, filepath)
    return filepath


def load_additional_pool(filepath: str) -> AdditionalPool:
    """
    从JSON文件加载附加票池
    
    Args:
        filepath: 文件路径
    
    Returns:
        附加票池对象
    """
    return load_from_json(filepath, AdditionalPool)



@dataclass
class MarketReport:
    """大盘分析报告
    
    包含大盘的技术分析、支撑压力位、短期和长期预期等信息
    """
    date: str                                   # 分析日期
    current_price: float                        # 当前价格
    change_pct: float                           # 涨跌幅
    support_levels: List[Dict[str, Any]]        # 支撑位列表
    resistance_levels: List[Dict[str, Any]]     # 压力位列表
    short_term_scenario: str                    # 短期场景
    short_term_target: List[float]              # 短期目标区间
    long_term_trend: str                        # 长期趋势
    raw_data: Dict[str, Any] = field(default_factory=dict)  # 原始数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketReport':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class EmotionReport:
    """情绪分析报告
    
    包含市场情绪指标、周期节点、赚钱效应评分等信息
    """
    date: str                                   # 分析日期
    market_coefficient: float                   # 大盘系数
    ultra_short_emotion: float                  # 超短情绪
    loss_effect: float                          # 亏钱效应
    cycle_node: str                             # 周期节点
    profit_score: int                           # 赚钱效应评分（0-100）
    position_suggestion: str                    # 仓位建议
    raw_data: Dict[str, Any] = field(default_factory=dict)  # 原始数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmotionReport':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class ThemeReport:
    """题材分析报告
    
    包含热门题材、题材强度、周期阶段、龙头股等信息
    """
    date: str                                   # 分析日期
    hot_themes: List[Dict[str, Any]]            # 热门题材列表
    market_summary: str                         # 市场概况
    raw_data: Dict[str, Any] = field(default_factory=dict)  # 原始数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThemeReport':
        """从字典创建实例"""
        return cls(**data)
