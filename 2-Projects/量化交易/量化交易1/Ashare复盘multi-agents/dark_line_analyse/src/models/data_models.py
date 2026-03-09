# -*- coding: utf-8 -*-
"""
涨停题材暗线挖掘智能体数据模型

定义所有数据结构（使用 Pydantic 进行验证）
"""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# ============ 基础枚举类型 ============

class OwnershipType(str, Enum):
    """企业性质"""
    CENTRAL = "央企"           # 中央国有企业
    LOCAL_STATE = "国企"        # 地方国有企业
    PRIVATE = "民企"           # 民营企业
    MIXED = "混合所有制"        # 混合所有制
    FOREIGN = "外资"           # 外资企业
    UNKNOWN = "未知"           # 未知性质


class PriceRange(str, Enum):
    """股价区间"""
    LOW = "低价股(<10元)"          # 低价股
    MEDIUM = "中价股(10-30元)"    # 中价股
    HIGH = "高价股(>30元)"         # 高价股
    UNKNOWN = "未知"                 # 未知


class MarketCapRange(str, Enum):
    """市值区间"""
    MICRO = "小市值(<50亿)"         # 小市值
    SMALL = "小市值(50-100亿)"     # 小市值
    MEDIUM = "中市值(100-1000亿)"  # 中市值
    LARGE = "大市值(>1000亿)"      # 大市值
    UNKNOWN = "未知"                 # 未知


class DarkLineType(str, Enum):
    """暗线类型"""
    REGIONAL_CLUSTER = "地域集聚"          # 某地域股票显著聚集
    OWNERSHIP_THEME = "企业性质主题"        # 特定企业性质(如央企)主导
    PB_VALUE_THEME = "PB价值主题"            # 低价/破净股为主
    NAMING_PATTERN = "命名模式"              # 特定命名模式(如东方系、数字股)
    CONCEPT_CLUSTER = "概念聚集"              # 特定概念聚集
    TECHNICAL_PATTERN = "技术形态"            # 特定技术形态
    UNKNOWN = "未知暗线"                 # 未知类型


# ============ 输入数据模型 ============

class LimitUpStockBasic(BaseModel):
    """涨停个股基础属性"""
    stock_code: str = Field(..., description="股票代码 (如 '600000.SH')")
    stock_name: str = Field(..., description="股票简称")
    listing_date: Optional[date] = Field(None, description="上市日期")
    registration_location: Optional[str] = Field(None, description="注册地")
    province: Optional[str] = Field(None, description="所属省份")
    ownership: OwnershipType = Field(OwnershipType.UNKNOWN, description="企业性质")
    industry: Optional[str] = Field(None, description="所属行业")
    concepts: List[str] = Field(default_factory=list, description="概念标签列表")

    # 财务属性
    pb_ratio: Optional[float] = Field(None, description="市净率 PB")
    pe_ratio: Optional[float] = Field(None, description="市盈率 PE")
    total_market_cap: Optional[float] = Field(None, description="总市值（亿元）")
    circulating_market_cap: Optional[float] = Field(None, description="流通市值（亿元）")
    price: Optional[float] = Field(None, description="当前股价")
    price_range: PriceRange = Field(PriceRange.UNKNOWN, description="股价区间")
    market_cap_range: MarketCapRange = Field(MarketCapRange.UNKNOWN, description="市值区间")
    is_broken_net: bool = Field(False, description="是否破净 (PB<1)")

    # 盘面属性
    limit_up_time: Optional[str] = Field(None, description="涨停时间 (如 '09:45')")
    consecutive_days: int = Field(0, description="连板高度")
    has_convertible_bond: bool = Field(False, description="是否有转债")
    is_margin_trading: bool = Field(False, description="是否融资融券标的")
    turnover_amount: Optional[float] = Field(None, description="成交额（亿元）")
    limit_up_reason: Optional[str] = Field(None, description="涨停原因")

    # 技术属性
    high_250d_distance: Optional[float] = Field(None, description="近250日最高价距离（%）")
    ma_deviation: Optional[Dict[str, float]] = Field(None, description="均线偏离度 {周期: 偏离度%}")
    has_recent_limit_up: bool = Field(False, description="前期(20日)是否有过涨停")


class StockConceptInfo(BaseModel):
    """股票概念信息"""
    stock_code: str = Field(..., description="股票代码")
    concepts: List[str] = Field(default_factory=list, description="概念标签列表")
    industries: List[str] = Field(default_factory=list, description="行业标签列表")


class NamingAnalysis(BaseModel):
    """命名语义分析结果"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票简称")

    # 命名特征
    has_dongfang: bool = Field(False, description="是否包含'东方'")
    has_chinese_num: bool = Field(False, description="是否包含中文数字(一二三...)")
    has_arabic_num: bool = Field(False, description="是否包含阿拉伯数字(123...)")
    has_long: bool = Field(False, description="是否包含'龙'")
    has_phoenix: bool = Field(False, description="是否包含'凤'")
    has_rising: bool = Field(False, description="是否包含'升/涨/腾'")
    has_holy: bool = Field(False, description="是否包含'圣/神/仙'")
    has_prefix: bool = Field(False, description="是否包含'中/国/华'")

    # 相似度分析
    similar_names: List[str] = Field(default_factory=list, description="高相似度股票名称列表")
    similarity_scores: List[float] = Field(default_factory=list, description="相似度分数列表")


class NamingAnalysisSummary(BaseModel):
    """命名分析汇总"""
    feature_summary: Dict[str, int] = Field(default_factory=dict, description="命名特征计数")
    feature_ratio: Dict[str, float] = Field(default_factory=dict, description="命名特征占比 (%)")
    similar_names: List[Dict[str, Any]] = Field(default_factory=list, description="相似名称对列表")
    prefix_patterns: Dict[str, List[str]] = Field(default_factory=dict, description="前缀模式")


# ============ 统计分析结果模型 ============

class FrequencyAnalysis(BaseModel):
    """频率分析结果"""
    category: str = Field(..., description="分类维度 (如 '地域', 'PB', '市值')")
    items_in_pool: Dict[str, int] = Field(default_factory=dict, description="涨停池中各项目出现次数")
    total_in_pool: int = Field(0, description="涨停池总数")
    pool_frequency: Dict[str, float] = Field(default_factory=dict, description="涨停池中频率 (%)")

    items_in_market: Dict[str, int] = Field(default_factory=dict, description="全市场基准各项目数量")
    total_in_market: int = Field(0, description="全市场总数")
    market_frequency: Dict[str, float] = Field(default_factory=dict, description="全市场频率 (%)")

    lift_ratio: Dict[str, float] = Field(default_factory=dict, description="提升倍数 (池内频率/市场频率)")
    significant_items: List[str] = Field(default_factory=list, description="显著高发项目 (提升倍数>2)")


class StatisticalAnalysis(BaseModel):
    """统计学对比分析结果"""
    analysis_date: str = Field(..., description="分析日期")
    limit_up_count: int = Field(..., description="涨停个股数量")

    # 各维度频率分析
    province_analysis: FrequencyAnalysis = Field(default_factory=FrequencyAnalysis, description="地域(省份)分析")
    ownership_analysis: FrequencyAnalysis = Field(default_factory=FrequencyAnalysis, description="企业性质分析")
    pb_analysis: FrequencyAnalysis = Field(default_factory=FrequencyAnalysis, description="市净率分析")
    market_cap_analysis: FrequencyAnalysis = Field(default_factory=FrequencyAnalysis, description="市值分析")
    price_range_analysis: FrequencyAnalysis = Field(default_factory=FrequencyAnalysis, description="股价区间分析")
    broken_net_ratio: float = Field(0.0, description="破净比例 (%)")

    # 盘面特征分析
    consecutive_days_analysis: FrequencyAnalysis = Field(default_factory=FrequencyAnalysis, description="连板高度分析")
    margin_trading_ratio: float = Field(0.0, description="融资融券比例 (%)")
    convertible_bond_ratio: float = Field(0.0, description="有转债比例 (%)")

    # 技术特征分析
    avg_high_250d_distance: float = Field(0.0, description="平均近250日最高价距离 (%)")
    recent_limit_up_ratio: float = Field(0.0, description="前期有过涨停比例 (%)")

    # 命名特征汇总
    naming_feature_summary: Dict[str, int] = Field(default_factory=dict, description="命名特征统计 {'东方': n, '数字': n, ...}")
    naming_feature_ratio: Dict[str, float] = Field(default_factory=dict, description="命名特征占比 (%)")


# ============ 暗线识别结果模型 ============

class DarkLineEvidence(BaseModel):
    """暗线证据"""
    evidence_type: str = Field(..., description="证据类型")
    description: str = Field(..., description="证据描述")
    strength: float = Field(..., ge=0, le=1, description="证据强度 (0-1)")
    data: Dict[str, Any] = Field(default_factory=dict, description="支撑数据")


class DarkLine(BaseModel):
    """暗线识别结果"""
    dark_line_type: DarkLineType = Field(..., description="暗线类型")
    title: str = Field(..., description="暗线标题")
    description: str = Field(..., description="暗线描述")
    confidence: float = Field(..., ge=0, le=1, description="置信度 (0-1)")

    # 相关股票
    related_stocks: List[str] = Field(default_factory=list, description="相关股票代码列表")
    stock_count: int = Field(0, description="涉及股票数量")

    # 证据链
    evidences: List[DarkLineEvidence] = Field(default_factory=list, description="证据列表")

    # 统计支撑
    statistical_support: Optional[Dict[str, Any]] = Field(None, description="统计学支撑数据")

    # 是否为偶然因素
    is_accidental: bool = Field(False, description="是否为偶然因素(样本量小)")


class DarkLineDetection(BaseModel):
    """暗线检测结果"""
    analysis_date: str = Field(..., description="分析日期")
    limit_up_count: int = Field(..., description="涨停个股数量")

    # 统计分析
    statistical_analysis: StatisticalAnalysis = Field(default_factory=StatisticalAnalysis, description="统计学分析结果")

    # 命名分析
    naming_analyses: List[NamingAnalysis] = Field(default_factory=list, description="命名分析结果列表")

    # 识别出的暗线
    dark_lines: List[DarkLine] = Field(default_factory=list, description="识别出的暗线列表")
    primary_dark_line: Optional[DarkLine] = Field(None, description="主要暗线(置信度最高)")

    # LLM解读
    llm_interpretation: Optional['LLMInterpretation'] = Field(None, description="LLM深度解读")

    # 总体评估
    overall_theme: str = Field("", description="总体题材主题")
    theme_strength: str = Field("弱", description="题材强度 (弱/中/强)")
    risk_assessment: str = Field("", description="风险评估")


# ============ LLM分析结果模型 ============

class LLMInterpretation(BaseModel):
    """LLM暗线解读"""
    interpretation_type: str = Field(..., description="解读类型")
    theme_nature: str = Field(..., description="题材性质 (事件驱动/政策驱动/情绪驱动/资金驱动)")
    sustainability: str = Field(..., description="持续性判断 (短期/中期/长期)")
    key_drivers: List[str] = Field(default_factory=list, description="关键驱动因素")
    risks: List[str] = Field(default_factory=list, description="主要风险")
    recommendations: List[str] = Field(default_factory=list, description="操作建议")
    confidence: float = Field(..., ge=0, le=1, description="解读置信度 (0-1)")
    reasoning: str = Field(..., description="推理过程")


# ============ 最终输出模型 ============

class DarkLineAnalysisOutput(BaseModel):
    """暗线分析最终输出（LLM-ready JSON）"""
    meta: Dict[str, Any] = Field(default_factory=dict, description="元数据 {date, limit_up_count, generated_at}")

    # 统计汇总
    statistical_summary: Dict[str, Any] = Field(default_factory={dict}, description="统计学汇总")

    # 命名特征
    naming_features: Dict[str, Any] = Field(default_factory=dict, description="命名特征汇总")

    # 暗线列表
    dark_lines: List[Dict[str, Any]] = Field(default_factory=list, description="暗线列表(序列化)")

    # LLM解读
    llm_interpretation: Optional[Dict[str, Any]] = Field(None, description="LLM解读结果")

    # 涨停个股详情
    stock_details: List[Dict[str, Any]] = Field(default_factory=list, description="涨停个股详情(序列化)")

    def model_dump_for_llm(self) -> Dict[str, Any]:
        """导出为适合LLM的JSON格式"""
        return self.model_dump(exclude_none=True, exclude={'meta': {'generated_at'}})


# ============ Agent配置模型 ============

class DataSourceConfig(BaseModel):
    """数据源配置"""
    kaipanla_timeout: int = Field(60, description="开盘啦超时时间(秒)")
    kaipanla_max_retries: int = Field(3, description="开盘啦最大重试次数")
    tushare_token: str = Field(..., description="TuShare API Token")
    tushare_timeout: int = Field(30, description="TuShare超时时间(秒)")
    akshare_timeout: int = Field(30, description="AkShare超时时间(秒)")


class AnalysisConfig(BaseModel):
    """分析参数配置"""
    # 统计学分析参数
    lift_ratio_threshold: float = Field(2.0, description="提升倍数阈值(>此值视为显著)")
    min_sample_size: int = Field(3, description="最小样本量(低于此值标记为偶然因素)")

    # 命名分析参数
    naming_similarity_threshold: float = Field(0.7, description="命名相似度阈值")

    # 技术分析参数
    ma_periods: List[int] = Field(default_factory=lambda: [5, 10, 20, 60], description="均线周期列表")
    lookback_days: int = Field(250, description="技术指标回溯天数")
    recent_limit_up_window: int = Field(20, description="近期涨停检测窗口(交易日)")

    # 分类阈值
    pb_break_threshold: float = Field(1.0, description="破净阈值")
    price_ranges: List[float] = Field(default_factory=lambda: [10, 30], description="股价区间分割点")
    market_cap_ranges: List[float] = Field(default_factory=lambda: [50, 100, 1000], description="市值区间分割点(亿元)")


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: str = Field("zhipu", description="LLM提供商 (zhipu/openai/deepseek)")
    api_key: str = Field(..., description="LLM API Key")
    model_name: str = Field("glm-4.7-flash", description="模型名称")
    temperature: float = Field(0.7, description="温度参数")
    max_tokens: Optional[int] = Field(None, description="最大token数")
    timeout: Optional[int] = Field(None, description="超时时间(秒)")


class OutputConfig(BaseModel):
    """输出配置"""
    report_dir: str = Field("output/reports", description="输出目录")
    format: List[str] = Field(default_factory=lambda: ["markdown", "json"], description="输出格式")
    include_stock_details: bool = Field(True, description="是否包含个股详情")


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = Field("INFO", description="日志级别")
    file: str = Field("logs/dark_line_agent.log", description="日志文件路径")
    max_bytes: int = Field(10485760, description="日志文件最大字节数(10MB)")
    backup_count: int = Field(5, description="日志备份数量")
    console_output: bool = Field(True, description="是否输出到控制台")


class AgentConfig(BaseModel):
    """Agent总配置"""
    data_source: DataSourceConfig = Field(..., description="数据源配置")
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig, description="分析参数")
    llm: LLMConfig = Field(..., description="LLM配置")
    output: OutputConfig = Field(default_factory=OutputConfig, description="输出配置")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="日志配置")
