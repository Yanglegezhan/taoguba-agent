"""
核心个股复盘数据模型

定义Pydantic数据模型，用于个股分析、连板分析、趋势分析等
"""
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class StockBasicInfo(BaseModel):
    """个股基本信息"""

    stock_code: str = Field(..., description="股票代码，如 605398")
    stock_name: str = Field(..., description="股票名称，如 浙文互联")
    market: Literal["sh", "sz"] = Field(..., description="市场：sh上海, sz深圳")
    ipo_date: Optional[str] = Field(None, description="上市日期")
    circulating_market_cap: Optional[float] = Field(None, description="流通市值（亿元）")
    total_market_cap: Optional[float] = Field(None, description="总市值（亿元）")
    concepts: List[str] = Field(default_factory=list, description="所属概念/题材")
    industry: Optional[str] = Field(None, description="所属行业")


class LadderInfo(BaseModel):
    """连板梯队信息"""

    consecutive_days: int = Field(..., description="连板天数")
    stocks: List[str] = Field(default_factory=list, description="该连板天数的股票代码列表")
    stock_details: List[StockBasicInfo] = Field(default_factory=list, description="该连板天数的股票详情")


class ConsecutiveLimitUpData(BaseModel):
    """连板梯队数据"""

    date: str = Field(..., description="分析日期")
    ladder: Dict[int, List[str]] = Field(default_factory=dict, description="连板梯队：{板数: [股票代码列表]}")
    ladder_details: Dict[int, List[StockBasicInfo]] = Field(default_factory=dict, description="连板梯队详情")
    max_consecutive: int = Field(default=0, description="最高连板天数")
    max_consecutive_stocks: List[str] = Field(default_factory=list, description="最高连板股票代码列表")
    max_consecutive_concepts: List[str] = Field(default_factory=list, description="最高连板股票所属概念")


class RealtimeBoardStock(BaseModel):
    """实时涨停板个股"""

    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    turnover: float = Field(..., description="成交额（亿元）")
    circulating_market_cap: float = Field(..., description="流通市值（亿元）")
    main_net_inflow: float = Field(..., description="主力净流入（万元）")
    concepts: List[str] = Field(default_factory=list, description="所属概念")
    consecutive_days: int = Field(default=1, description="连板天数")
    open_price: Optional[float] = Field(None, description="开盘价")
    close_price: Optional[float] = Field(None, description="收盘价")
    high_price: Optional[float] = Field(None, description="最高价")
    low_price: Optional[float] = Field(None, description="最低价")
    volume: Optional[int] = Field(None, description="成交量（手）")
    turnover_rate: Optional[float] = Field(None, description="换手率（%）")


class StockIntradayData(BaseModel):
    """个股分时数据"""

    DataFrame: Any = Field(..., description="分时数据DataFrame")
    columns: List[str] = Field(default_factory=lambda: ["time", "price", "avg_price", "volume", "main_net_inflow"])

    # 时间: str
    # price: float
    # avg_price: float
    # volume: int
    # main_net_inflow: float


class IndexIntradayData(BaseModel):
    """大盘指数分时数据"""

    index_code: str = Field(..., description="指数代码")
    index_name: str = Field(..., description="指数名称")
    DataFrame: Any = Field(..., description="分时数据DataFrame")
    columns: List[str] = Field(default_factory=lambda: ["time", "price", "pct_change", "trend"])

    # time: str
    # price: float
    # pct_change: float
    # trend: str  # up, down, flat


class SpecialAction(BaseModel):
    """特殊动作检测结果"""

    action_type: Literal["leading", "reverse_fall", "anti_nuclear", "none"] = Field(
        ..., description="动作类型：领涨/逆跌/反核/无"
    )
    detected: bool = Field(default=False, description="是否检测到该动作")
    timestamp: Optional[str] = Field(None, description="检测时间点")
    price: Optional[float] = Field(None, description="检测时刻价格")
    volume: Optional[int] = Field(None, description="检测时刻成交量")
    main_net_inflow: Optional[float] = Field(None, description="检测时刻主力净流入")
    description: str = Field(default="", description="动作描述")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="置信度")


class SectorPremiumAnalysis(BaseModel):
    """同题材溢价分析"""

    sector: str = Field(..., description="题材名称")
    same_concept_stocks: List[StockBasicInfo] = Field(default_factory=list, description="同题材股票列表")
    target_premium: Literal["高开", "平开", "低开", "未开盘"] = Field(default="未开盘", description="目标个股次日溢价")
    target_premium_value: Optional[float] = Field(None, description="目标个股次日溢价百分比")
    sector_avg_premium: Literal["高开", "平开", "低开", "未开盘"] = Field(default="未开盘", description="同题材平均溢价")
    sector_avg_premium_value: Optional[float] = Field(None, description="同题材平均溢价百分比")
    premium_level: Literal["优于", "持平", "弱于"] = Field(default="持平", description="溢价水平对比")
    is_leader: bool = Field(default=False, description="是否为题材龙头（头狼）")


class RoleType(BaseModel):
    """个股在梯队中的角色"""

    role: Literal["头狼", "中军", "先锋", "补涨", "羊群", "跟风"] = Field(
        ...,
        description="角色类型：头狼/中军/先锋/补涨/羊群/跟风",
    )
    role_description: str = Field(default="", description="角色描述")


class ConsecutiveBoardAnalysis(BaseModel):
    """连板分析结果"""

    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    analysis_date: str = Field(..., description="分析日期")
    consecutive_days: int = Field(..., description="连板天数")

    role: RoleType = Field(..., description="梯队角色分析")

    # 成交量与资金分析
    turnover_analysis: Dict[str, Any] = Field(default_factory=dict, description="成交额分析")
    fund_analysis: Dict[str, Any] = Field(default_factory=dict, description="资金流向分析")
    board_strength: Optional[float] = Field(None, description="板强度（成交额/流通市值）")

    # 特殊动作
    special_actions: Dict[str, SpecialAction] = Field(
        default_factory=dict,
        description="特殊动作：{leading, reverse_fall, anti_nuclear}",
    )

    # 同题材对比
    sector_premium: Optional[SectorPremiumAnalysis] = Field(None, description="同题材溢价分析")

    # 板块带动板块
    sector_impact: Dict[str, Any] = Field(default_factory=dict, description="板块带动效应分析")

    # 风险与机会
    risk_assessment: str = Field(default="", description="风险评估")
    opportunity_judgment: str = Field(default="", description="机会判断")

    confidence: Literal["高", "中", "低"] = Field(default="中", description="分析置信度")
    reasoning: str = Field(default="", description="分析推理过程")

    # 元数据
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")


class TrendPattern(BaseModel):
    """趋势形态"""

    pattern_type: Literal["主升浪", "反弹", "震荡", "筑底", "下跌"] = Field(..., description="趋势形态类型")
    stage: str = Field(default="", description="当前阶段：初期/中期/后期")
    duration_days: int = Field(default=0, description="持续天数")
    strength: float = Field(default=0.0, description="趋势强度")


class VolumePriceAnalysis(BaseModel):
    """量价关系分析"""

    relationship: Literal["量价齐升", "量价背离", "缩量上涨", "放量下跌", "无规律"] = Field(
        ..., description="量价关系类型"
    )
    description: str = Field(default="", description="量价关系描述")
    volume_trend: Literal["放量", "缩量", "平稳"] = Field(default="平稳", description="成交量趋势")
    price_trend: Literal["上涨", "下跌", "震荡"] = Field(default="震荡", description="价格趋势")


class MovingAverageAnalysis(BaseModel):
    """均线系统分析"""

    ma5: Optional[float] = Field(None, description="5日均线")
    ma10: Optional[float] = Field(None, description="10日均线")
    ma20: Optional[float] = Field(None, description="20日均线")
    ma60: Optional[float] = Field(None, description="60日均线")

    ma5_bias: Optional[float] = Field(None, description="5日均线乖离率")
    ma20_bias: Optional[float] = Field(None, description="20日均线乖离率")

    alignment: Literal["多头排列", "空头排列", "缠绕", "发散"] = Field(default="缠绕", description="均线排列状态")
    support_level: Optional[float] = Field(None, description="支撑位")
    resistance_level: Optional[float] = Field(None, description="压力位")


class BreakthroughPoint(BaseModel):
    """突破/回踩点"""

    point_type: Literal["突破", "回踩", "破位"] = Field(..., description="点位类型")
    level: Optional[float] = Field(None, description="点位价格")
    level_type: Literal["阻力位", "支撑位", "前高", "前低", "均线"] = Field(..., description="点位类型")
    timestamp: Optional[str] = Field(None, description="发生时间")
    volume: Optional[int] = Field(None, description="成交量")
    valid: bool = Field(default=True, description="是否有效")


class TrendStockAnalysis(BaseModel):
    """趋势股分析结果"""

    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    analysis_date: str = Field(..., description="分析日期")

    # 趋势形态
    trend_pattern: TrendPattern = Field(..., description="趋势形态")

    # 量价关系
    volume_price: VolumePriceAnalysis = Field(..., description="量价关系分析")

    # 均线系统
    moving_average: MovingAverageAnalysis = Field(..., description="均线系统分析")

    # 突破/回踩点
    breakthrough_points: List[BreakthroughPoint] = Field(default_factory=list, description="突破/回踩点列表")

    # 相对强度
    relative_strength: float = Field(default=0.0, description="相对强度（相对大盘）")
    relative_index: Optional[str] = Field(None, description="对比的指数代码")

    # 持续性预判
    sustainability: Literal["强", "中", "弱"] = Field(default="中", description="趋势持续性")
    sustainability_reason: str = Field(default="", description="持续性判断理由")

    # 风险与机会
    risk_level: Literal["高", "中", "低"] = Field(default="中", description="风险等级")
    key_risk_points: List[str] = Field(default_factory=list, description="关键风险点")

    opportunity_level: Literal["高", "中", "低"] = Field(default="中", description="机会等级")
    entry_point: Optional[float] = Field(None, description="建议入场点")
    target_price: Optional[float] = Field(None, description="目标价格")
    stop_loss: Optional[float] = Field(None, description="止损位")

    confidence: Literal["高", "中", "低"] = Field(default="中", description="分析置信度")
    reasoning: str = Field(default="", description="分析推理过程")

    # 元数据
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")


class CriticEvaluation(BaseModel):
    """Critic评估结果"""

    agent_type: Literal["consecutive_board", "trend_stock"] = Field(..., description="被评估的Agent类型")
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    evaluation_date: str = Field(..., description="评估日期")

    # 逻辑一致性
    logic_consistency: float = Field(default=0.0, ge=0.0, le=1.0, description="逻辑一致性得分")
    consistency_feedback: str = Field(default="", description="一致性反馈")

    # 数据充分性
    data_sufficiency: float = Field(default=0.0, ge=0.0, le=1.0, description="数据充分性得分")
    missing_data: List[str] = Field(default_factory=list, description="缺失数据")

    # 结论合理性
    conclusion_validity: float = Field(default=0.0, ge=0.0, le=1.0, description="结论合理性得分")
    validity_feedback: str = Field(default="", description="合理性反馈")

    # 漏洞识别
    identified_issues: List[str] = Field(default_factory=list, description="识别出的问题")
    issue_severity: List[Literal["low", "medium", "high"]] = Field(default_factory=list, description="问题严重程度")

    # 改进建议
    improvement_suggestions: List[str] = Field(default_factory=list, description="改进建议")

    # 总体评估
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0, description="总体得分")
    accepted: bool = Field(default=True, description="是否接受原分析")
    rejection_reason: str = Field(default="", description="拒绝原因")

    # 元数据
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")


class SynthesisReport(BaseModel):
    """综合复盘报告"""

    report_date: str = Field(..., description="报告日期")
    report_title: str = Field(default="核心个股复盘报告", description="报告标题")

    # 分析的股票列表
    consecutive_board_stocks: List[ConsecutiveBoardAnalysis] = Field(default_factory=list, description="连板个股分析")
    trend_stocks: List[TrendStockAnalysis] = Field(default_factory=list, description="趋势个股分析")

    # Critic评估
    critic_evaluations: List[CriticEvaluation] = Field(default_factory=list, description="Critic评估结果")

    # 综合摘要
    summary: str = Field(default="", description="综合摘要")

    # 一致性分析
    consistent_conclusions: List[str] = Field(default_factory=list, description="一致性结论")
    contradictions: List[Dict[str, Any]] = Field(default_factory=list, description="矛盾点列表")

    # 题材分析
    sector_analysis: Dict[str, Any] = Field(default_factory=dict, description="题材综合分析")

    # 操作建议
    overall_recommendation: Literal["积极", "中性", "谨慎", "回避"] = Field(
        default="中性", description="整体操作建议"
    )
    specific_recommendations: List[Dict[str, Any]] = Field(default_factory=list, description="具体操作建议")

    # 外部报告集成
    external_context: Dict[str, Any] = Field(default_factory=dict, description="外部报告上下文")

    # 元数据
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")
    generated_by: str = Field(default="StockSynthesisAgent", description="生成Agent")


class AnalysisRequest(BaseModel):
    """分析请求"""

    date: str = Field(..., description="分析日期，格式 YYYY-MM-DD")
    stock_codes: Optional[List[str]] = Field(None, description="指定分析的股票代码列表")
    analysis_types: List[Literal["consecutive_board", "trend_stock"]] = Field(
        default_factory=lambda: ["consecutive_board", "trend_stock"], description="分析类型"
    )
    enable_critic: bool = Field(default=True, description="是否启用Critic评估")
    output_format: List[Literal["markdown", "json"]] = Field(
        default_factory=lambda: ["markdown", "json"], description="输出格式"
    )
    include_synthesis: bool = Field(default=True, description="是否生成综合报告")


class AnalysisResponse(BaseModel):
    """分析响应"""

    request: AnalysisRequest = Field(..., description="分析请求")
    success: bool = Field(default=True, description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")

    consecutive_board_analysis: List[ConsecutiveBoardAnalysis] = Field(default_factory=list, description="连板分析结果")
    trend_analysis: List[TrendStockAnalysis] = Field(default_factory=list, description="趋势分析结果")
    critic_evaluations: List[CriticEvaluation] = Field(default_factory=list, description="Critic评估")
    synthesis_report: Optional[SynthesisReport] = Field(None, description="综合报告")

    # 输出文件
    markdown_report_path: Optional[str] = Field(None, description="Markdown报告路径")
    json_report_path: Optional[str] = Field(None, description="JSON报告路径")

    # 元数据
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")
