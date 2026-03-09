# Design Document: A股超短线题材锚定Agent

## Overview

A股超短线题材锚定Agent是一个智能市场分析系统，模拟资深游资操盘手的决策思维，通过四个核心分析维度（题材筛选、盘面联动、情绪周期、容量结构）对当日热点题材进行系统化解构。系统将部署在 `Ashare复盘multi-agents/Theme_repay_agent` 目录中，遵循现有项目的架构模式，使用Python实现，集成开盘啦API作为数据源。

## Architecture

系统采用模块化架构，分为以下核心层次：

### 1. 数据层 (Data Layer)
- **KaipanlaDataSource**: 封装开盘啦API调用，获取板块强度、分时数据、涨停数据等（主数据源）
- **AkshareDataSource**: 封装akshare接口，作为备用数据源补充缺失数据
- **DataSourceFallback**: 数据源降级管理器，主数据源失败时自动切换到备用数据源
- **HistoryTracker**: 管理板块历史排名数据的持久化存储（CSV格式）
- **DataValidator**: 验证和清洗API返回的数据

### 2. 分析层 (Analysis Layer)
- **SectorFilter**: 题材筛选与强度初筛模块
- **CorrelationAnalyzer**: 盘面联动与主动性分析模块
- **EmotionCycleDetector**: 情绪周期定性模块
- **CapacityProfiler**: 题材容量与结构画像模块

### 3. 业务逻辑层 (Business Logic Layer)
- **ThemeAnchorAgent**: 核心协调器，编排四个分析步骤的执行流程
- **AnalysisOrchestrator**: 管理分析流程的执行顺序和数据传递
- **LLMAnalyzer**: LLM分析引擎，负责调用大模型进行深度分析
- **PromptEngine**: 提示词引擎，管理和生成各类分析提示词
- **ContextBuilder**: 上下文构建器，为LLM准备结构化输入数据

### 4. 输出层 (Output Layer)
- **ReportGenerator**: 生成结构化分析报告（Markdown/JSON格式）
- **ReportExporter**: 导出报告为PDF或HTML格式（可选）

### 5. 接口层 (Interface Layer)
- **CLI**: 命令行接口，支持日期选择和参数配置
- **ConfigManager**: 管理配置文件（API密钥、阈值参数等）

## Components and Interfaces

### Component 1: KaipanlaDataSource

**职责**: 封装开盘啦API的所有数据获取操作

**接口**:
```python
class KaipanlaDataSource:
    def __init__(self):
        """初始化数据源，使用kaipanla_crawler"""
        
    def get_sector_strength_ndays(self, end_date: str, num_days: int = 7) -> pd.DataFrame:
        """获取N日板块强度数据
        
        Args:
            end_date: 结束日期，格式 'YYYY-MM-DD'
            num_days: 查询天数，默认7天
            
        Returns:
            DataFrame包含：
            - 日期: 交易日期
            - 板块代码: 板块代码
            - 板块名称: 板块名称
            - 涨停数: 该板块涨停股票数量
            - 涨停股票: 涨停股票列表
        """
        
    def get_intraday_data(self, target: str, date: str) -> IntradayData:
        """获取大盘或板块的分时数据
        
        Args:
            target: 目标代码（如 'SH000001' 为上证指数，或板块代码）
            date: 日期字符串
            
        Returns:
            分时数据，包含：
            - timestamps: 时间戳列表（分钟级）
            - prices: 价格列表
            - pct_changes: 涨跌幅列表
        """
        
    def get_limit_up_data(self, date: str) -> LimitUpData:
        """获取涨停相关数据
        
        Returns:
            涨停数据，包含：
            - limit_up_count: 全市场涨停家数
            - limit_down_count: 全市场跌停家数
            - blown_limit_up_rate: 全市场炸板率（%）
            - consecutive_boards: 连板数据（按板块分组）
            - yesterday_limit_up_performance: 昨日涨停今日表现（%）
        """
        
    def get_sector_turnover_data(self, sector_name: str, date: str) -> TurnoverData:
        """获取板块成交额和个股数据
        
        Returns:
            成交额数据，包含：
            - sector_turnover: 板块总成交额
            - top5_stocks: Top5个股及其成交额
            - stock_market_caps: 个股流通市值
        """
        
    def get_sector_ranking(self, date: str) -> Dict[str, Any]:
        """获取涨停原因板块数据
        
        Returns:
            板块排名数据，包含市场概况和各板块详情
        """
```

### Component 2: AkshareDataSource

**职责**: 封装akshare接口，作为备用数据源

**接口**:
```python
class AkshareDataSource:
    def __init__(self):
        """初始化akshare数据源"""
        
    def get_stock_hist(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取个股历史数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            包含价格、成交量等的DataFrame
        """
        
    def get_board_industry(self) -> pd.DataFrame:
        """获取行业板块列表"""
        
    def get_board_concept(self) -> pd.DataFrame:
        """获取概念板块列表"""
        
    def get_stock_minute(self, stock_code: str, period: str = "1") -> pd.DataFrame:
        """获取个股分时数据
        
        Args:
            stock_code: 股票代码
            period: 周期（1/5/15/30/60分钟）
            
        Returns:
            分时数据DataFrame
        """
```

### Component 3: DataSourceFallback

**职责**: 数据源降级管理，主数据源失败时自动切换

**接口**:
```python
class DataSourceFallback:
    def __init__(
        self,
        primary_source: KaipanlaDataSource,
        fallback_source: AkshareDataSource
    ):
        """初始化数据源降级管理器
        
        Args:
            primary_source: 主数据源（kaipanla）
            fallback_source: 备用数据源（akshare）
        """
        
    def get_sector_strength_ndays(
        self,
        end_date: str,
        num_days: int = 7
    ) -> pd.DataFrame:
        """获取N日板块强度数据（带降级）
        
        优先使用kaipanla，失败时尝试从akshare构建
        """
        
    def get_intraday_data(
        self,
        target: str,
        date: str
    ) -> IntradayData:
        """获取分时数据（带降级）
        
        优先使用kaipanla，失败时使用akshare
        """
        
    def _convert_akshare_format(
        self,
        akshare_data: pd.DataFrame,
        target_format: str
    ) -> Any:
        """将akshare数据转换为系统标准格式"""
        
    def _log_source_usage(
        self,
        method: str,
        source: str,
        success: bool
    ) -> None:
        """记录数据源使用情况"""
```

### Component 4: HistoryTracker

**职责**: 管理板块历史排名数据的存储和查询

**接口**:
```python
class HistoryTracker:
    def __init__(self, storage_path: str):
        """初始化历史追踪器
        
        Args:
            storage_path: CSV文件存储路径
        """
        
    def save_daily_ranking(self, date: str, rankings: List[SectorRanking]) -> None:
        """保存当日板块排名
        
        Args:
            date: 日期字符串
            rankings: 板块排名列表（前7强）
        """
        
    def get_history(self, sector_name: str, days: int = 7) -> List[HistoryRecord]:
        """查询板块历史排名
        
        Args:
            sector_name: 板块名称
            days: 查询天数
            
        Returns:
            历史记录列表，每项包含：
            - date: 日期
            - rank: 排名（1-7，或None表示未进入前7）
            - strength_score: 强度分数
        """
        
    def is_new_face(self, sector_name: str, current_date: str) -> bool:
        """判断板块是否为新面孔
        
        Returns:
            True表示新面孔，False表示老面孔
        """
        
    def get_consecutive_days(self, sector_name: str, current_date: str) -> int:
        """获取板块连续进入前7的天数"""
```

### Component 3: SectorFilter

**职责**: 执行题材筛选与强度初筛逻辑

**接口**:
```python
class SectorFilter:
    def __init__(self, history_tracker: HistoryTracker):
        """初始化筛选器"""
        
    def filter_sectors(
        self, 
        ndays_data: pd.DataFrame,
        current_date: str,
        high_threshold: int = 8000,
        medium_threshold: int = 2000,
        target_count: int = 7
    ) -> FilterResult:
        """筛选目标板块集合
        
        Args:
            ndays_data: N日板块强度数据（来自get_sector_strength_ndays）
            current_date: 当前日期
            high_threshold: 高强度阈值（累计涨停数）
            medium_threshold: 中等强度阈值
            target_count: 目标板块数量
            
        Returns:
            筛选结果，包含：
            - target_sectors: 目标板块列表（7个）
            - new_faces: 新面孔板块列表
            - old_faces: 老面孔板块列表（含持续天数）
        """
        
    def _calculate_strength_score(self, ndays_data: pd.DataFrame, sector_name: str) -> int:
        """计算板块强度分数"""
        
    def _select_top_sectors(
        self, 
        sector_scores: List[Tuple[str, int]],
        high_threshold: int,
        medium_threshold: int,
        target_count: int
    ) -> List[str]:
        """选择前N强板块（按规则补齐）"""
```

### Component 4: CorrelationAnalyzer

**职责**: 分析板块与大盘的联动关系和主动性

**接口**:
```python
class CorrelationAnalyzer:
    def __init__(self):
        """初始化联动分析器"""
        
    def analyze_correlation(
        self,
        market_data: IntradayData,
        sector_data_list: List[Tuple[str, IntradayData]]
    ) -> CorrelationResult:
        """分析盘面联动关系
        
        Args:
            market_data: 大盘分时数据
            sector_data_list: 板块分时数据列表（板块名, 数据）
            
        Returns:
            联动分析结果，包含：
            - resonance_points: 识别的共振点列表
            - leading_sectors: 先锋板块列表（含时差）
            - resonance_sectors: 强度共振板块列表（含弹性系数）
            - divergence_sectors: 分离板块列表
            - seesaw_effects: 跷跷板效应列表（资金来源-目标对）
        """
        
    def _find_resonance_points(self, market_data: IntradayData) -> List[ResonancePoint]:
        """识别大盘关键变盘节点
        
        Returns:
            共振点列表，每项包含：
            - timestamp: 时间戳
            - point_type: 类型（急跌低点/V型反转/突破点）
            - price_change: 价格变化幅度
        """
        
    def _calculate_time_lag(
        self,
        market_point: ResonancePoint,
        sector_data: IntradayData
    ) -> Optional[int]:
        """计算板块与大盘的时差（分钟）"""
        
    def _calculate_elasticity(
        self,
        market_change: float,
        sector_change: float
    ) -> float:
        """计算弹性系数（板块涨幅/大盘涨幅）"""
```

### Component 5: EmotionCycleDetector (已移除 - 由LLM替代)

**说明**: 原本的EmotionCycleDetector组件已被移除，情绪周期判定现在完全由LLM完成。系统将收集必要的市场数据（涨停数、连板梯队、炸板率、分时走势等），通过PromptEngine构建专门的情绪周期分析提示词，然后调用LLMAnalyzer进行判定。

**数据准备**: ContextBuilder负责将原始市场数据格式化为LLM易理解的结构化文本。

### Component 6: CapacityProfiler

**职责**: 分析题材容量和结构健康度

**接口**:
```python
class CapacityProfiler:
    def __init__(self):
        """初始化容量分析器"""
        
    def profile_capacity(
        self,
        sector_name: str,
        turnover_data: TurnoverData,
        consecutive_boards: Dict[int, List[str]]
    ) -> CapacityProfile:
        """分析板块容量和结构
        
        Args:
            sector_name: 板块名称
            turnover_data: 成交额数据
            consecutive_boards: 连板数据（板数 -> 股票列表）
            
        Returns:
            容量画像，包含：
            - capacity_type: 容量类型（大容量主线/小众投机题材）
            - sector_turnover: 板块总成交额
            - leading_stock_turnover: 核心中军成交额
            - pyramid_structure: 金字塔结构
            - structure_health: 结构健康度（0-1）
            - sustainability_score: 持续性评分（0-100）
        """
        
    def _classify_capacity(self, turnover_data: TurnoverData) -> str:
        """分类容量类型"""
        
    def _build_pyramid(
        self,
        consecutive_boards: Dict[int, List[str]]
    ) -> PyramidStructure:
        """构建连板梯队金字塔
        
        Returns:
            金字塔结构，包含：
            - board_5_count: 5板个股数量
            - board_3_count: 3板个股数量
            - board_1_count: 1板个股数量
            - gaps: 断层列表（缺失的板数）
        """
        
    def _calculate_health_score(self, pyramid: PyramidStructure) -> float:
        """计算结构健康度（断层越少分数越高）"""
```

### Component 7: ThemeAnchorAgent

**职责**: 核心协调器，编排整个分析流程

**接口**:
```python
class ThemeAnchorAgent:
    def __init__(
        self,
        data_source: KaipanlaDataSource,
        history_tracker: HistoryTracker,
        config: AgentConfig
    ):
        """初始化题材锚定Agent
        
        Args:
            data_source: 数据源
            history_tracker: 历史追踪器
            config: 配置对象
        """
        
    def analyze(self, date: str) -> AnalysisReport:
        """执行完整分析流程
        
        Args:
            date: 分析日期
            
        Returns:
            综合分析报告
        """
        
    def _step1_filter_sectors(self, date: str) -> FilterResult:
        """步骤1: 题材筛选"""
        
    def _step2_analyze_correlation(
        self,
        target_sectors: List[str],
        date: str
    ) -> CorrelationResult:
        """步骤2: 盘面联动分析"""
        
    def _step3_detect_emotion_cycles(
        self,
        target_sectors: List[str],
        date: str
    ) -> Dict[str, EmotionCycle]:
        """步骤3: 情绪周期检测"""
        
    def _step4_profile_capacity(
        self,
        target_sectors: List[str],
        date: str
    ) -> Dict[str, CapacityProfile]:
        """步骤4: 容量结构分析"""
```

### Component 7: ThemeAnchorAgent

**职责**: 核心协调器，编排整个分析流程，集成LLM进行深度分析

**接口**:
```python
class ThemeAnchorAgent:
    def __init__(
        self,
        data_source: KaipanlaDataSource,
        history_tracker: HistoryTracker,
        llm_analyzer: LLMAnalyzer,
        config: AgentConfig
    ):
        """初始化题材锚定Agent
        
        Args:
            data_source: 数据源
            history_tracker: 历史追踪器
            llm_analyzer: LLM分析引擎
            config: 配置对象
        """
        
    def analyze(self, date: str) -> AnalysisReport:
        """执行完整分析流程
        
        Args:
            date: 分析日期
            
        Returns:
            综合分析报告
        """
        
    def _step1_filter_sectors(self, date: str) -> FilterResult:
        """步骤1: 题材筛选"""
        
    def _step2_analyze_correlation(
        self,
        target_sectors: List[str],
        date: str
    ) -> CorrelationResult:
        """步骤2: 盘面联动分析"""
        
    def _step3_detect_emotion_cycles(
        self,
        target_sectors: List[str],
        date: str
    ) -> Dict[str, EmotionCycleAnalysis]:
        """步骤3: 情绪周期检测（通过LLM）
        
        收集板块涨停数据、连板梯队、炸板率、分时走势等信息，
        调用LLM进行情绪周期判定
        """
        
    def _step4_profile_capacity(
        self,
        target_sectors: List[str],
        date: str
    ) -> Dict[str, CapacityProfile]:
        """步骤4: 容量结构分析"""
        
    def _step5_llm_deep_analysis(
        self,
        filter_result: FilterResult,
        correlation_result: CorrelationResult,
        emotion_cycles: Dict[str, EmotionCycleAnalysis],
        capacity_profiles: Dict[str, CapacityProfile]
    ) -> LLMAnalysisResult:
        """步骤5: LLM深度分析
        
        整合前四步的数据，调用LLM进行：
        - 资金意图还原
        - 题材持续性判断
        - 风险机会评估
        - 操作建议生成
        """
```

### Component 8: LLMAnalyzer

**职责**: LLM分析引擎，负责调用大模型进行深度分析

**接口**:
```python
class LLMAnalyzer:
    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4",
        prompt_engine: PromptEngine = None
    ):
        """初始化LLM分析器
        
        Args:
            api_key: LLM API密钥
            model_name: 模型名称
            prompt_engine: 提示词引擎
        """
        
    def analyze_market_intent(
        self,
        context: AnalysisContext
    ) -> MarketIntentAnalysis:
        """分析市场资金意图
        
        Args:
            context: 分析上下文（包含所有数据）
            
        Returns:
            资金意图分析结果：
            - main_capital_flow: 主力资金流向
            - sector_rotation: 板块轮动分析
            - market_sentiment: 市场情绪判断
            - key_drivers: 关键驱动因素
        """
        
    def analyze_emotion_cycle(
        self,
        sector_name: str,
        context: AnalysisContext
    ) -> EmotionCycleAnalysis:
        """分析板块情绪周期（新增方法）
        
        Args:
            sector_name: 板块名称
            context: 分析上下文（包含涨停数据、连板梯队、炸板率、分时走势等）
            
        Returns:
            情绪周期分析结果：
            - stage: 周期阶段（启动期/高潮期/分化期/修复期/退潮期）
            - confidence: 判定置信度（0-1）
            - reasoning: 判定理由
            - key_indicators: 关键指标说明
            - risk_level: 风险等级（Low/Medium/High）
            - opportunity_level: 机会等级（Low/Medium/High）
        """
    
    def evaluate_sustainability(
        self,
        sector_name: str,
        context: AnalysisContext
    ) -> SustainabilityEvaluation:
        """评估题材持续性
        
        Returns:
            持续性评估：
            - sustainability_score: 持续性评分（0-100）
            - time_horizon: 预期持续时间
            - risk_factors: 风险因素
            - support_factors: 支撑因素
        """
        
    def generate_trading_advice(
        self,
        sector_name: str,
        context: AnalysisContext
    ) -> TradingAdvice:
        """生成操作建议
        
        Returns:
            操作建议：
            - action: 操作方向（观望/低吸/追涨/减仓）
            - entry_timing: 入场时机
            - exit_strategy: 出场策略
            - position_sizing: 仓位建议
            - risk_warning: 风险提示
        """
        
    def _call_llm(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """调用LLM API"""
```

### Component 9: PromptEngine

**职责**: 提示词引擎，管理和生成各类分析提示词

**接口**:
```python
class PromptEngine:
    def __init__(self, template_dir: str = "prompts/"):
        """初始化提示词引擎
        
        Args:
            template_dir: 提示词模板目录
        """
        
    def build_market_intent_prompt(
        self,
        context: AnalysisContext
    ) -> str:
        """构建资金意图分析提示词
        
        提示词结构：
        1. 角色设定：十年经验游资操盘手
        2. 任务描述：分析市场资金真实意图
        3. 数据输入：结构化的市场数据
        4. 分析维度：资金流向、板块轮动、情绪判断
        5. 输出格式：JSON结构化输出
        """
        
    def build_emotion_cycle_prompt(
        self,
        sector_name: str,
        context: AnalysisContext
    ) -> str:
        """构建情绪周期分析提示词（新增方法）
        
        提示词结构：
        1. 角色设定：资深情绪周期分析师
        2. 任务描述：判定板块所处的情绪周期阶段
        3. 理论背景：情绪周期理论（启动期、高潮期、分化期、修复期、退潮期）
        4. 数据输入：板块涨停数据、连板梯队、炸板率、分时走势、历史表现
        5. 分析维度：涨停家数变化、连板高度、市场情绪、资金参与度
        6. 输出格式：JSON结构化输出（阶段、置信度、理由、风险机会等级）
        """
    
    def build_sustainability_prompt(
        self,
        sector_name: str,
        context: AnalysisContext
    ) -> str:
        """构建题材持续性评估提示词
        
        提示词结构：
        1. 角色设定：资深题材研究员
        2. 任务描述：评估题材持续性
        3. 数据输入：板块详细数据
        4. 分析维度：情绪周期、容量结构、历史表现
        5. 输出格式：评分+理由
        """
        
    def build_trading_advice_prompt(
        self,
        sector_name: str,
        context: AnalysisContext
    ) -> str:
        """构建操作建议生成提示词
        
        提示词结构：
        1. 角色设定：实战派交易员
        2. 任务描述：给出具体操作建议
        3. 数据输入：综合分析结果
        4. 分析维度：风险收益比、时机选择、仓位管理
        5. 输出格式：结构化建议
        """
        
    def load_template(self, template_name: str) -> str:
        """加载提示词模板"""
        
    def render_template(
        self,
        template: str,
        variables: Dict[str, Any]
    ) -> str:
        """渲染提示词模板（填充变量）"""
```

### Component 10: ContextBuilder

**职责**: 上下文构建器，为LLM准备结构化输入数据

**接口**:
```python
class ContextBuilder:
    def __init__(self):
        """初始化上下文构建器"""
        
    def build_analysis_context(
        self,
        date: str,
        filter_result: FilterResult,
        correlation_result: CorrelationResult,
        emotion_cycles: Dict[str, EmotionCycle],
        capacity_profiles: Dict[str, CapacityProfile]
    ) -> AnalysisContext:
        """构建完整分析上下文
        
        Returns:
            AnalysisContext对象，包含：
            - date: 分析日期
            - market_overview: 市场概览
            - target_sectors: 目标板块详情
            - sector_relationships: 板块关系图
            - historical_context: 历史上下文
        """
        
    def format_for_llm(
        self,
        context: AnalysisContext,
        focus_sector: Optional[str] = None
    ) -> str:
        """格式化上下文为LLM友好的文本
        
        将结构化数据转换为清晰的文本描述：
        - 使用表格展示数值数据
        - 使用列表展示关键发现
        - 突出重要信息
        - 控制总长度（避免超过token限制）
        """
        
    def _summarize_sector_data(
        self,
        sector_name: str,
        context: AnalysisContext
    ) -> str:
        """总结单个板块的关键数据"""
        
    def _build_market_snapshot(
        self,
        context: AnalysisContext
    ) -> str:
        """构建市场快照"""
```

### Component 11: ReportGenerator

**职责**: 生成结构化分析报告

**接口**:
```python
class ReportGenerator:
    def __init__(self):
        """初始化报告生成器"""
        
    def generate_report(
        self,
        date: str,
        filter_result: FilterResult,
        correlation_result: CorrelationResult,
        emotion_cycles: Dict[str, EmotionCycle],
        capacity_profiles: Dict[str, CapacityProfile]
    ) -> AnalysisReport:
        """生成综合分析报告
        
        Returns:
            分析报告对象，包含：
            - date: 分析日期
            - summary: 执行摘要
            - target_sectors: 目标板块详情列表
            - market_overview: 市场概览
            - risk_warnings: 风险提示列表
        """
        
    def export_markdown(self, report: AnalysisReport, output_path: str) -> None:
        """导出为Markdown格式"""
        
    def export_json(self, report: AnalysisReport, output_path: str) -> None:
        """导出为JSON格式"""
```

## Data Models

### SectorStrength
```python
@dataclass
class SectorStrength:
    sector_name: str          # 板块名称
    sector_code: str          # 板块代码
    strength_score: int       # 强度分数（N日累计涨停数）
    ndays_limit_up: int       # N日涨停数
    rank: Optional[int]       # 排名
```

### IntradayData
```python
@dataclass
class IntradayData:
    target: str                    # 目标代码
    date: str                      # 日期
    timestamps: List[datetime]     # 时间戳列表
    prices: List[float]            # 价格列表
    pct_changes: List[float]       # 涨跌幅列表（相对开盘）
```

### ResonancePoint
```python
@dataclass
class ResonancePoint:
    timestamp: datetime        # 时间戳
    point_type: str           # 类型（DIP/V_REVERSAL/BREAKTHROUGH）
    price_change: float       # 价格变化幅度
    index: int                # 在时间序列中的索引
```

### CorrelationResult
```python
@dataclass
class CorrelationResult:
    resonance_points: List[ResonancePoint]
    leading_sectors: List[LeadingSector]        # 先锋板块
    resonance_sectors: List[ResonanceSector]    # 共振板块
    divergence_sectors: List[str]               # 分离板块
    seesaw_effects: List[SeesawEffect]          # 跷跷板效应

@dataclass
class LeadingSector:
    sector_name: str
    time_lag: int             # 时差（分钟，负数表示领先）
    resonance_point: ResonancePoint

@dataclass
class ResonanceSector:
    sector_name: str
    elasticity: float         # 弹性系数
    market_change: float      # 大盘涨幅
    sector_change: float      # 板块涨幅

@dataclass
class SeesawEffect:
    rising_sector: str        # 上涨板块
    falling_sector: str       # 下跌板块
    timestamp: datetime       # 发生时间
```

### EmotionCycle
```python
@dataclass
class EmotionCycle:
    stage: str                # 阶段（STARTUP/CLIMAX/DIVERGENCE/RESTORATION/DECLINE）
    confidence: float         # 置信度（0-1）
    indicators: Dict[str, Any]  # 关键指标
    risk_level: str           # 风险等级（LOW/MEDIUM/HIGH）
    opportunity_level: str    # 机会等级（LOW/MEDIUM/HIGH）
    description: str          # 阶段描述
```

### PyramidStructure
```python
@dataclass
class PyramidStructure:
    board_5_plus: int         # 5板及以上个股数量
    board_3_to_4: int         # 3-4板个股数量
    board_1_to_2: int         # 1-2板个股数量
    gaps: List[int]           # 断层（缺失的板数）
    total_stocks: int         # 总个股数
```

### CapacityProfile
```python
@dataclass
class CapacityProfile:
    capacity_type: str        # 容量类型（LARGE_CAP/SMALL_CAP）
    sector_turnover: float    # 板块总成交额（亿元）
    leading_stock_turnover: float  # 核心中军成交额（亿元）
    pyramid_structure: PyramidStructure
    structure_health: float   # 结构健康度（0-1）
    sustainability_score: float  # 持续性评分（0-100）
```

### AnalysisReport
```python
@dataclass
class AnalysisReport:
    date: str
    executive_summary: str    # 执行摘要（LLM生成）
    market_intent: MarketIntentAnalysis  # 资金意图分析
    target_sectors: List[SectorAnalysis]
    trading_recommendations: List[TradingAdvice]  # 操作建议
    risk_warnings: List[str]
    
@dataclass
class SectorAnalysis:
    sector_name: str
    rank: int
    strength_score: int
    is_new_face: bool
    consecutive_days: int
    correlation_analysis: Optional[CorrelationAnalysis]
    emotion_cycle: EmotionCycle
    capacity_profile: CapacityProfile
    sustainability: SustainabilityEvaluation  # LLM评估
    trading_advice: TradingAdvice  # LLM建议
```

### LLM Analysis Models

```python
@dataclass
class AnalysisContext:
    """LLM分析上下文"""
    date: str
    market_overview: MarketOverview
    target_sectors: List[SectorAnalysis]
    sector_relationships: Dict[str, Any]
    historical_context: Dict[str, Any]
    
@dataclass
class MarketIntentAnalysis:
    """市场资金意图分析"""
    main_capital_flow: str        # 主力资金流向描述
    sector_rotation: str          # 板块轮动分析
    market_sentiment: str         # 市场情绪判断
    key_drivers: List[str]        # 关键驱动因素
    confidence: float             # 分析置信度

@dataclass
class EmotionCycleAnalysis:
    """情绪周期分析（新增）"""
    stage: str                    # 周期阶段（启动期/高潮期/分化期/修复期/退潮期）
    confidence: float             # 判定置信度（0-1）
    reasoning: str                # 判定理由
    key_indicators: List[str]     # 关键指标说明
    risk_level: str               # 风险等级（Low/Medium/High）
    opportunity_level: str        # 机会等级（Low/Medium/High）
    
@dataclass
class SustainabilityEvaluation:
    """题材持续性评估"""
    sustainability_score: float   # 持续性评分（0-100）
    time_horizon: str             # 预期持续时间
    risk_factors: List[str]       # 风险因素
    support_factors: List[str]    # 支撑因素
    reasoning: str                # 评估理由
    
@dataclass
class TradingAdvice:
    """操作建议"""
    action: str                   # 操作方向（观望/低吸/追涨/减仓）
    entry_timing: str             # 入场时机
    exit_strategy: str            # 出场策略
    position_sizing: str          # 仓位建议
    risk_warning: str             # 风险提示
    reasoning: str                # 建议理由
    
@dataclass
class LLMAnalysisResult:
    """LLM分析结果汇总"""
    market_intent: MarketIntentAnalysis
    emotion_cycles: Dict[str, EmotionCycleAnalysis]  # 板块名 -> 情绪周期分析
    sector_evaluations: Dict[str, SustainabilityEvaluation]
    trading_advices: Dict[str, TradingAdvice]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, several properties can be consolidated:
- Properties 1.3 and 1.4 both test sector filtering logic and can be combined
- Properties 6.2-6.5 all test report completeness and can be combined into one comprehensive property
- Properties 7.3 and 7.4 both test new/old face marking and can be combined
- Properties 3.2-3.6 all test emotion cycle detection for different stages - these are distinct and should remain separate

### Core Correctness Properties

**Property 1: Target sector set size invariant**
*For any* list of sector strength scores, after applying the filtering and补齐 logic, the resulting target sector set should always contain exactly 7 sectors.
**Validates: Requirements 1.1, 1.2**

**Property 2: High-strength sector inclusion**
*For any* N-day sector strength data, all sectors with cumulative limit-up count > 8000 should be included in the target sector set (up to 7 sectors).
**Validates: Requirements 1.1**

**Property 3: New/old face marking completeness**
*For any* target sector set and historical data, every sector should have exactly one marking: either "新面孔" or "老面孔" with consecutive days count.
**Validates: Requirements 1.5, 1.6, 7.3, 7.4**

**Property 4: Resonance point identification**
*For any* market intraday data containing clear patterns (sharp dips, V-reversals, breakthroughs), the system should identify at least one resonance point of the appropriate type.
**Validates: Requirements 2.1**

**Property 6: Time lag calculation consistency**
*For any* resonance point and sector intraday data, if the sector shows a similar pattern, the calculated time lag should be consistent with the actual time difference between the market and sector movements.
**Validates: Requirements 2.2**

**Property 7: Leading sector identification**
*For any* sector with time lag between -10 and -5 minutes (leading the market by 5-10 minutes), the sector should be marked as "先锋" (Leading).
**Validates: Requirements 2.3**

**Property 8: Resonance sector identification**
*For any* market movement of +1% and sector movement of +3% or more during the same period, the sector should be marked as "强度共振" (Resonance) with elasticity ≥ 3.0.
**Validates: Requirements 2.4**

**Property 9: Divergence sector identification**
*For any* market decline and sector that remains flat or rises during the same period, the sector should be marked as "分离" (Divergence).
**Validates: Requirements 2.5**

**Property 10: Seesaw effect detection**
*For any* pair of sectors where one rises significantly while another falls significantly at the same time, the system should identify and record a seesaw effect between them.
**Validates: Requirements 2.6**

**Property 11: Emotion cycle LLM analysis**
*For any* valid limit-up data, intraday data, and market context, the LLM should return a valid emotion cycle analysis containing stage label, confidence score, and reasoning.
**Validates: Requirements 3.1, 3.2, 3.3**

**Property 12: Emotion cycle stage validation**
*For any* LLM emotion cycle response, the stage label should be one of the five valid stages: 启动期(Startup), 高潮期(Climax), 分化期(Divergence), 修复期(Restoration), or 退潮期(Decline).
**Validates: Requirements 3.1**

**Property 13: Capacity classification**
*For any* turnover data, the system should classify the sector as either "大容量主线" (Large-cap mainline) or "小众投机题材" (Small-cap speculative) based on leading stock turnover and market cap distribution.
**Validates: Requirements 4.1, 4.2, 4.3**

**Property 14: Pyramid structure construction**
*For any* consecutive board data, the system should construct a pyramid structure that accurately counts stocks at each board level (5+, 3-4, 1-2 boards).
**Validates: Requirements 4.4, 4.5**

**Property 15: Structure health scoring**
*For any* pyramid structure with fewer gaps (missing board levels), the health score should be higher than structures with more gaps.
**Validates: Requirements 4.6**

**Property 16: Error handling robustness**
*For any* API failure or data anomaly, the system should log the error, return a clear error message, and continue processing available data without crashing.
**Validates: Requirements 5.5, 5.6**

**Property 17: Report completeness**
*For any* complete analysis results, the generated report should contain all required sections: sector filtering results, new/old markings, strength scores, correlation analysis, emotion cycles, risk warnings, capacity classification, and structure health assessments.
**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

**Property 18: Report sorting consistency**
*For any* analysis report, sectors should be sorted in descending order by either strength score or comprehensive score, maintaining consistent ordering.
**Validates: Requirements 6.6**

**Property 19: Historical data persistence**
*For any* daily ranking data saved to storage, querying the same date should return the exact same ranking data (round-trip property).
**Validates: Requirements 7.1, 7.2**



## Error Handling

### API Communication Errors
- **Network Failures**: Implement retry logic with exponential backoff (max 3 retries)
- **Timeout Handling**: Set reasonable timeouts (30s for data fetching)
- **Rate Limiting**: Respect API rate limits, implement request throttling
- **Invalid Responses**: Validate API response structure, log malformed data

### Data Quality Issues
- **Missing Data**: Mark fields as unavailable, continue with partial analysis
- **Anomalous Values**: Flag outliers (e.g., negative prices, impossible percentages)
- **Incomplete Time Series**: Interpolate missing time points or skip affected analysis
- **Empty Datasets**: Return clear error messages, suggest data availability checks

### Analysis Failures
- **Insufficient Data**: Require minimum data points for analysis (e.g., ≥30 minutes of intraday data)
- **Ambiguous Patterns**: When multiple emotion cycle stages match, return highest confidence stage
- **Division by Zero**: Handle zero market movements gracefully in elasticity calculations
- **Historical Data Unavailable**: Initialize with empty history, mark all sectors as "new face"

### Storage Errors
- **File I/O Failures**: Log errors, attempt alternative storage locations
- **Corrupted Data**: Validate on read, rebuild from backup if available
- **Disk Space**: Check available space before writing, clean old data if needed

### Error Reporting
- All errors should include:
  - Timestamp
  - Error type and code
  - Contextual information (date, sector name, etc.)
  - Suggested remediation steps
- Critical errors should halt execution
- Non-critical errors should be logged and allow graceful degradation

## Testing Strategy

### Dual Testing Approach

This system requires both **unit tests** and **property-based tests** for comprehensive validation:

**Unit Tests** focus on:
- Specific examples of sector filtering (e.g., exactly 7 high-strength sectors)
- Edge cases (empty data, single sector, boundary values)
- Error conditions (API failures, malformed data)
- Integration points (API mocking, file I/O)

**Property-Based Tests** focus on:
- Universal properties across all inputs (see Correctness Properties section)
- Comprehensive input coverage through randomization
- Invariants that must hold regardless of data values

### Property-Based Testing Configuration

**Framework**: Use `hypothesis` library for Python
- Minimum 100 iterations per property test
- Each test must reference its design document property number
- Tag format: `# Feature: theme-anchor-agent, Property {N}: {property_text}`

### Test Organization

```
tests/
├── unit/
│   ├── test_sector_filter.py
│   ├── test_correlation_analyzer.py
│   ├── test_emotion_cycle_detector.py
│   ├── test_capacity_profiler.py
│   ├── test_history_tracker.py
│   └── test_report_generator.py
├── property/
│   ├── test_properties_filtering.py      # Properties 1-4
│   ├── test_properties_correlation.py    # Properties 5-10
│   ├── test_properties_emotion.py        # Properties 11-16
│   ├── test_properties_capacity.py       # Properties 17-19
│   └── test_properties_system.py         # Properties 20-23
├── integration/
│   ├── test_kaipanla_integration.py
│   ├── test_end_to_end.py
│   └── test_cli.py
└── conftest.py
```

### Test Data Strategy

**Generators for Property Tests**:
- `gen_sector_scores()`: Generate random sector strength scores with configurable distributions
- `gen_intraday_data()`: Generate realistic intraday price movements with patterns
- `gen_limit_up_data()`: Generate limit-up statistics with various scenarios
- `gen_turnover_data()`: Generate turnover and market cap data
- `gen_history_data()`: Generate historical ranking data with various patterns

**Fixtures for Unit Tests**:
- Sample API responses (mocked)
- Pre-computed analysis results
- Edge case datasets (empty, single item, boundary values)

### Coverage Goals
- Line coverage: ≥85%
- Branch coverage: ≥80%
- All correctness properties: 100% implemented and passing

### Continuous Testing
- Run unit tests on every commit
- Run property tests (with reduced iterations) on every commit
- Run full property test suite (100+ iterations) nightly
- Run integration tests before releases

## Implementation Notes

### Technology Stack
- **Language**: Python 3.9+
- **Data Processing**: pandas, numpy
- **API Client**: requests with retry logic
- **Testing**: pytest, hypothesis
- **Configuration**: YAML files
- **Logging**: Python logging module with structured logs
- **CLI**: argparse or click

### Project Structure
```
Ashare复盘multi-agents/Theme_repay_agent/
├── src/
│   ├── __init__.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── kaipanla_source.py
│   │   ├── akshare_source.py
│   │   ├── data_source_fallback.py
│   │   ├── history_tracker.py
│   │   └── validators.py
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── sector_filter.py
│   │   ├── correlation_analyzer.py
│   │   ├── emotion_cycle_detector.py
│   │   └── capacity_profiler.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── llm_analyzer.py
│   │   ├── prompt_engine.py
│   │   └── context_builder.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── theme_anchor_agent.py
│   │   └── orchestrator.py
│   └── output/
│       ├── __init__.py
│       ├── report_generator.py
│       └── exporters.py
├── tests/
│   ├── unit/
│   ├── property/
│   └── integration/
├── config/
│   ├── config.yaml
│   └── config.example.yaml
├── prompts/
│   ├── market_intent.md
│   ├── sustainability.md
│   └── trading_advice.md
├── data/
│   └── history/
│       └── sector_rankings.csv
├── output/
│   └── reports/
├── examples/
│   ├── example_basic_analysis.py
│   └── example_custom_config.py
├── docs/
│   └── README.md
├── theme_cli.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

### Configuration Parameters

Key configurable parameters in `config.yaml`:
```yaml
api:
  kaipanla_api_key: "your_api_key"
  timeout: 30
  max_retries: 3

llm:
  provider: "openai"  # openai, zhipu, qwen, etc.
  api_key: "your_llm_api_key"
  model_name: "gpt-4"
  temperature: 0.7
  max_tokens: 2000
  timeout: 60

filtering:
  high_strength_threshold: 8000  # 高强度阈值（N日累计涨停数）
  medium_strength_min: 2000      # 中等强度最小值
  target_sector_count: 7         # 目标板块数量
  ndays_lookback: 7              # N日回溯天数

correlation:
  leading_time_lag_min: 5
  leading_time_lag_max: 10
  resonance_elasticity_threshold: 3.0
  divergence_threshold: 0.5

emotion:
  climax_limit_up_threshold: 10
  divergence_pullback_threshold: 5.0
  attack_angle_threshold: 40
  decline_drop_threshold: 5.0
  decline_decrease_threshold: 50.0
  climax_blown_rate_threshold: 20.0  # 高潮期炸板率阈值（%）
  divergence_blown_rate_threshold: 30.0  # 分化期炸板率阈值（%）

capacity:
  large_cap_turnover_threshold: 30  # 亿元
  health_score_gap_penalty: 0.2

history:
  lookback_days: 7
  storage_path: "data/history/sector_rankings.csv"

prompts:
  template_dir: "prompts/"
  context_max_tokens: 8000

output:
  report_format: "markdown"  # markdown, json, both
  output_dir: "output/reports"
```

### Performance Considerations
- Cache API responses for repeated queries within same session
- Batch API requests where possible
- Use vectorized operations (numpy/pandas) for data processing
- Lazy load historical data (only when needed)
- Limit memory usage by processing sectors sequentially

### Prompt Templates

系统使用模板化的提示词，存储在 `prompts/` 目录：

**1. 资金意图分析模板** (`prompts/market_intent.md`):
```markdown
# 角色设定
你是一位拥有十年经验的A股游资操盘手，精通"龙头战法"与"情绪周期论"。

# 任务
分析{{date}}的市场资金真实意图，从数据中还原主力资金的流向和意图。

# 市场数据
{{market_data}}

# 分析维度
1. 主力资金流向：哪些板块在吸引资金？
2. 板块轮动：资金从哪里流出，流向哪里？
3. 市场情绪：当前处于什么情绪阶段？
4. 关键驱动：是什么在驱动当前的资金流动？

# 输出格式
请以JSON格式输出，包含：
- main_capital_flow: 主力资金流向描述
- sector_rotation: 板块轮动分析
- market_sentiment: 市场情绪判断
- key_drivers: 关键驱动因素列表
- confidence: 分析置信度（0-1）
```

**2. 情绪周期分析模板** (`prompts/emotion_cycle.md`):
```markdown
# 角色设定
你是一位资深的A股情绪周期分析师，精通"情绪周期论"，能够准确判断板块所处的情绪周期阶段。

# 情绪周期理论
情绪周期分为五个阶段：
1. **启动期**：首板数量激增，出现破局个股（一字板或秒板），分时图呈45度攻击角
2. **高潮期**：涨停家数>10只，全市场炸板率低（<20%），跟风股纷纷涨停，市场情绪高涨
3. **分化期**：仅前排1-2只龙头涨停，中后排回撤>5%，全市场炸板率飙升（>30%），资金开始分化
4. **修复期**：经历分歧后核心中军或龙头反包，板块指数收复昨日失地，情绪修复
5. **退潮期**：龙头跌停或断板大跌（跌幅>5%），板块整体涨停数骤减（相比前一日减少>50%），情绪退潮

# 任务
分析{{sector_name}}板块在{{date}}的情绪周期阶段。

# 板块数据
{{sector_data}}

# 分析维度
1. 涨停家数变化：当前涨停数、与前一日对比
2. 连板高度：最高连板、连板梯队分布
3. 市场情绪：全市场炸板率、昨日涨停今日表现
4. 资金参与度：板块成交额、龙头股表现
5. 分时走势：板块分时图形态、攻击角度

# 输出格式
请以JSON格式输出，包含：
- stage: 周期阶段（启动期/高潮期/分化期/修复期/退潮期）
- confidence: 判定置信度（0-1）
- reasoning: 判定理由（详细说明为什么判定为该阶段）
- key_indicators: 关键指标列表（支持判定的关键数据）
- risk_level: 风险等级（Low/Medium/High）
- opportunity_level: 机会等级（Low/Medium/High）
```

**3. 题材持续性评估模板** (`prompts/sustainability.md`):
```markdown
# 角色设定
你是一位资深的A股题材研究员，擅长判断题材的生命周期和持续性。

# 任务
评估{{sector_name}}板块的持续性，判断该题材还能走多远。

# 板块数据
{{sector_data}}

# 分析维度
1. 情绪周期：当前处于什么阶段？
2. 容量结构：资金容量是否充足？梯队是否健康？
3. 历史表现：过去的表现如何？
4. 催化剂：是否有持续的催化剂？

# 输出格式
请以JSON格式输出，包含：
- sustainability_score: 持续性评分（0-100）
- time_horizon: 预期持续时间（如"1-2天"、"3-5天"、"一周以上"）
- risk_factors: 风险因素列表
- support_factors: 支撑因素列表
- reasoning: 评估理由
```

**4. 操作建议生成模板** (`prompts/trading_advice.md`):
```markdown
# 角色设定
你是一位实战派短线交易员，擅长把握买卖时机和风险控制。

# 任务
针对{{sector_name}}板块，给出具体的操作建议。

# 综合分析
{{analysis_summary}}

# 分析维度
1. 风险收益比：当前介入的风险和收益如何？
2. 时机选择：什么时候介入最合适？
3. 仓位管理：应该用多大仓位？
4. 出场策略：什么情况下应该离场？

# 输出格式
请以JSON格式输出，包含：
- action: 操作方向（观望/低吸/追涨/减仓）
- entry_timing: 入场时机描述
- exit_strategy: 出场策略描述
- position_sizing: 仓位建议（如"轻仓试探"、"半仓"、"重仓"）
- risk_warning: 风险提示
- reasoning: 建议理由
```

### Context Management

**上下文长度控制**:
- 单次LLM调用的上下文限制在8000 tokens以内
- 优先级排序：当前日数据 > 近3日数据 > 历史统计
- 使用摘要技术压缩历史数据

**数据格式化策略**:
- 数值数据使用表格展示
- 关键发现使用列表突出
- 复杂关系使用文字描述
- 避免冗余信息

**示例上下文格式**:
```
## 市场概览（2026-01-20）
- 涨停数：45只
- 跌停数：8只
- 涨跌比：1.35
- 最高连板：6连板（博菲电气）

## 目标板块（前7强）
| 排名 | 板块名称 | 强度分数 | 涨停数 | 新旧 |
|------|---------|---------|--------|------|
| 1    | 低空经济 | 12500   | 8      | 新   |
| 2    | 固态电池 | 10800   | 6      | 老3天 |
...

## 盘面联动分析
- 先锋板块：低空经济（领先大盘8分钟触底反弹）
- 共振板块：固态电池（弹性系数3.2）
- 分离板块：无
- 跷跷板：低空经济↑ vs 锂电池↓

## 情绪周期
- 低空经济：启动期（首板激增，45度攻击波）
- 固态电池：高潮期（涨停10只，炸板率低）
...
```
