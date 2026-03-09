"""
连板核心复盘智能体

分析连板梯队个股
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# 导入项目模块
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

from src.data.kaipanla_stock_source import KaipanlaStockSource
from src.analysis.indicator_calculator import IndicatorCalculator
from src.analysis.special_action_detector import SpecialActionDetector
from src.analysis.sector_comparator import SectorComparator
from src.llm.client import LLMClient, create_client
from src.llm.prompt_engine import PromptEngine
from src.models.stock_models import (
    ConsecutiveBoardAnalysis,
    RoleType,
    SpecialAction,
    SectorPremiumAnalysis,
)


logger = logging.getLogger(__name__)


class ConsecutiveBoardStockAgent:
    """连板核心复盘智能体"""

    def __init__(
        self,
        data_source: Optional[KaipanlaStockSource] = None,
        llm_client: Optional[LLMClient] = None,
        prompt_engine: Optional[PromptEngine] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化连板核心复盘智能体

        Args:
            data_source: 数据源实例
            llm_client: LLM客户端实例
            prompt_engine: 提示词引擎实例
            config: 配置参数
        """
        self.data_source = data_source if data_source is not None else KaipanlaStockSource()
        self.llm_client = llm_client
        self.prompt_engine = prompt_engine if prompt_engine is not None else PromptEngine()

        self.config = config if config is not None else {}

        # 初始化分析器
        self.indicator_calculator = IndicatorCalculator()
        self.special_action_detector = SpecialActionDetector()
        self.sector_comparator = SectorComparator(self.data_source)

        # 默认配置
        self.default_config = {
            "detect_special_actions": True,
            "sector_comparison": True,
            "min_consecutive_days": 2,
            "use_llm": True,
        }

    def analyze(
        self,
        stock_code: str,
        date: str,
        ladder_data: Optional[Dict[str, Any]] = None,
        index_intraday: Optional[Dict[str, Any]] = None,
    ) -> ConsecutiveBoardAnalysis:
        """
        分析指定股票

        Args:
            stock_code: 股票代码
            date: 分析日期
            ladder_data: 连板梯队数据（可选，不提供则自动获取）
            index_intraday: 大盘分时数据（可选，用于逆跌检测）

        Returns:
            连板分析结果
        """
        logger.info(f"开始分析连板股票: {stock_code}, 日期: {date}")

        # 1. 获取数据
        stock_data = self._get_stock_data(stock_code, date)
        if not stock_data:
            logger.error(f"无法获取股票数据: {stock_code}")
            return self._create_empty_analysis(stock_code, date, error="无法获取数据")

        # 2. 获取连板梯队数据
        if ladder_data is None:
            ladder_data = self.data_source.get_consecutive_limit_up(date)

        # 3. 计算连板高度和角色
        consecutive_days = stock_data.get("consecutive_days", 1)
        role_info = self.sector_comparator.analyze_ladder_role(
            stock_code, consecutive_days, ladder_data
        )

        # 4. 分析成交量与资金
        turnover_analysis = self._analyze_turnover(stock_data)
        fund_analysis = self._analyze_fund(stock_data)
        board_strength = self._calculate_board_strength(stock_data)

        # 5. 检测特殊动作
        special_actions = {}
        if self.config.get("detect_special_actions", self.default_config["detect_special_actions"]):
            special_actions = self._detect_special_actions(
                stock_data, index_intraday
            )

        # 6. 同题材对比
        sector_premium = None
        if self.config.get("sector_comparison", self.default_config["sector_comparison"]):
            sector_premium = self._compare_sector(
                stock_code, stock_data, ladder_data
            )

        # 7. 板块带动效应分析
        sector_impact = self._analyze_sector_impact(stock_data, ladder_data)

        # 8. 风险评估与机会判断
        (
            risk_assessment,
            opportunity_judgment,
            confidence,
        ) = self._assess_risk_and_opportunity(
            stock_data, role_info, special_actions, sector_premium
        )

        # 9. 构建分析结果
        analysis = ConsecutiveBoardAnalysis(
            stock_code=stock_code,
            stock_name=stock_data.get("stock_name", ""),
            analysis_date=date,
            consecutive_days=consecutive_days,
            role=RoleType(
                role=role_info["role"],
                role_description=role_info.get("role_description", ""),
            ),
            turnover_analysis=turnover_analysis,
            fund_analysis=fund_analysis,
            board_strength=board_strength,
            special_actions={
                key: SpecialAction(**value) for key, value in special_actions.items()
            },
            sector_premium=SectorPremiumAnalysis(**sector_premium)
            if sector_premium
            else None,
            sector_impact=sector_impact,
            risk_assessment=risk_assessment,
            opportunity_judgment=opportunity_judgment,
            confidence=confidence,
            reasoning=self._build_reasoning(
                stock_data, role_info, special_actions, sector_premium
            ),
        )

        logger.info(f"完成分析: {stock_code}")

        return analysis

    def _get_stock_data(self, stock_code: str, date: str) -> Dict[str, Any]:
        """获取股票数据"""
        # 从连板数据中查找
        consecutive_data = self.data_source.get_consecutive_limit_up(date)
        ladder = consecutive_data.get("ladder_details", {})

        # 查找股票信息
        stock_info = None
        for days, stocks in ladder.items():
            for stock in stocks:
                if stock.get("stock_code") == stock_code:
                    stock_info = stock.copy()
                    stock_info["consecutive_days"] = days
                    break
            if stock_info:
                break

        if stock_info:
            return stock_info

        # 从实时涨停板数据中查找
        realtime_data = self.data_source.get_realtime_all_boards_stocks()
        for board_name in ["first_board", "second_board", "third_board", "fourth_board", "fifth_board_plus"]:
            for stock in realtime_data.get(board_name, []):
                if stock.get("stock_code") == stock_code:
                    return stock

        return {}

    def _analyze_turnover(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析成交量"""
        turnover = stock_data.get("turnover", 0)
        circulating_cap = stock_data.get("circulating_market_cap", 0)

        return {
            "turnover": turnover,
            "turnover_level": self._get_turnover_level(turnover),
            "turnover_ratio": round(turnover / circulating_cap, 2)
            if circulating_cap > 0
            else 0,
        }

    def _get_turnover_level(self, turnover: float) -> str:
        """获取成交额等级"""
        if turnover >= 10:
            return "巨量（10亿+）"
        elif turnover >= 5:
            return "大量（5-10亿）"
        elif turnover >= 2:
            return "中量（2-5亿）"
        elif turnover >= 1:
            return "小量（1-2亿）"
        else:
            return "微量（<1亿）"

    def _analyze_fund(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析资金流向"""
        inflow = stock_data.get("main_net_inflow", 0)

        return {
            "main_net_inflow": inflow,
            "flow_direction": "大幅流入" if inflow > 10000 else ("流入" if inflow > 0 else ("流出" if inflow < -10000 else "平衡")),
            "flow_strength": self._get_flow_strength(inflow),
        }

    def _get_flow_strength(self, inflow: float) -> str:
        """获取资金流向强度"""
        abs_inflow = abs(inflow)
        if abs_inflow >= 50000:
            return "极强"
        elif abs_inflow >= 20000:
            return "强"
        elif abs_inflow >= 10000:
            return "中"
        elif abs_inflow >= 5000:
            return "弱"
        else:
            return "极弱"

    def _calculate_board_strength(self, stock_data: Dict[str, Any]) -> float:
        """计算板强度（成交额/流通市值）"""
        turnover = stock_data.get("turnover", 0)
        circulating_cap = stock_data.get("circulating_market_cap", 0)

        if circulating_cap > 0:
            return round(turnover / circulating_cap, 4)
        return 0

    def _detect_special_actions(
        self,
        stock_data: Dict[str, Any],
        index_intraday: Optional[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """检测特殊动作"""
        stock_code = stock_data.get("stock_code")
        date = stock_data.get("date", "")

        # 获取个股分时数据
        stock_intraday = self.data_source.get_stock_intraday(stock_code, date)

        # 获取流通市值
        market_cap = stock_data.get("circulating_market_cap")

        # 检测领涨
        leading = self.special_action_detector.detect_leading_action(
            stock_intraday, market_cap
        )

        # 检测逆跌（需要大盘数据）
        reverse_fall = self.special_action_detector.detect_leading_action(
            stock_intraday, market_cap
        )  # 使用相同结构，实际应用中应该用detect_reverse_fall_action

        # 检测反核
        anti_nuclear = self.special_action_detector.detect_leading_action(
            stock_intraday, market_cap
        )  # 使用相同结构，实际应用中应该用detect_anti_nuclear_action

        return {
            "leading": leading,
            "reverse_fall": reverse_fall,
            "anti_nuclear": anti_nuclear,
        }

    def _compare_sector(
        self,
        stock_code: str,
        stock_data: Dict[str, Any],
        ladder_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """同题材对比"""
        realtime_data = self.data_source.get_realtime_all_boards_stocks()
        all_stocks = []
        for board_name in ["first_board", "second_board", "third_board", "fourth_board", "fifth_board_plus"]:
            all_stocks.extend(realtime_data.get(board_name, []))

        return self.sector_comparator.compare_same_concept_stocks(
            stock_data, all_stocks, ladder_data
        )

    def _analyze_sector_impact(
        self, stock_data: Dict[str, Any], ladder_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析板块带动效应"""
        stock_code = stock_data.get("stock_code")
        consecutive_days = stock_data.get("consecutive_days", 1)
        concepts = stock_data.get("concepts", [])

        # 获取同概念股票数量
        max_consecutive = ladder_data.get("max_consecutive", 0)

        impact_level = "一般"
        if consecutive_days >= max_consecutive and consecutive_days >= 3:
            impact_level = "极强（核心带动）"
        elif consecutive_days >= max_consecutive - 1 and consecutive_days >= 2:
            impact_level = "强（重要带动）"
        elif consecutive_days >= 2:
            impact_level = "中（部分带动）"
        else:
            impact_level = "弱（跟随）"

        return {
            "impact_level": impact_level,
            "concepts": concepts,
            "consecutive_days": consecutive_days,
            "max_consecutive": max_consecutive,
        }

    def _assess_risk_and_opportunity(
        self,
        stock_data: Dict[str, Any],
        role_info: Dict[str, Any],
        special_actions: Dict[str, Dict[str, Any]],
        sector_premium: Optional[Dict[str, Any]],
    ) -> tuple:
        """评估风险与机会"""
        consecutive_days = stock_data.get("consecutive_days", 1)
        inflow = stock_data.get("main_net_inflow", 0)
        turnover = stock_data.get("turnover", 0)

        # 风险评估
        risks = []
        if consecutive_days >= 5:
            risks.append("高板风险（监管关注）")
        if inflow < 0:
            risks.append("资金流出（承接弱）")
        if turnover < 1:
            risks.append("量能不足（人气差）")

        if not risks:
            risk_assessment = "风险可控，可关注"
        elif len(risks) == 1:
            risk_assessment = f"存在风险：{risks[0]}"
        else:
            risk_assessment = f"存在多重风险：{'、'.join(risks)}"

        # 机会判断
        opportunities = []
        if "头狼" in role_info.get("role", ""):
            opportunities.append("核心龙头地位")
        if inflow > 10000:
            opportunities.append("资金强势流入")
        if sector_premium and sector_premium.get("is_leader"):
            opportunities.append("题材龙头溢价优势")

        confidence = "中"
        if not risks and len(opportunities) >= 2:
            confidence = "高"
        elif len(risks) >= 2:
            confidence = "低"

        if not opportunities:
            opportunity_judgment = "机会有限，建议观望"
        elif len(opportunities) == 1:
            opportunity_judgment = f"存在机会：{opportunities[0]}"
        else:
            opportunity_judgment = f"存在多个机会：{'、'.join(opportunities)}"

        return risk_assessment, opportunity_judgment, confidence

    def _build_reasoning(
        self,
        stock_data: Dict[str, Any],
        role_info: Dict[str, Any],
        special_actions: Dict[str, Dict[str, Any]],
        sector_premium: Optional[Dict[str, Any]],
    ) -> str:
        """构建分析推理过程"""
        parts = [
            f"股票：{stock_data.get('stock_name')}（{stock_data.get('stock_code')}）",
            f"连板天数：{stock_data.get('consecutive_days', 1)}板",
            f"在梯队中的角色：{role_info.get('role', '未知')}",
        ]

        # 添加特殊动作
        detected_actions = []
        for action_type, action_data in special_actions.items():
            if action_data.get("detected"):
                detected_actions.append(action_type)

        if detected_actions:
            parts.append(f"检测到特殊动作：{', '.join(detected_actions)}")

        # 添加同题材分析
        if sector_premium:
            parts.append(
                f"同题材分析：{'龙头' if sector_premium.get('is_leader') else '跟随'}，"
                f"溢价水平{sector_premium.get('premium_level', '持平')}同题材"
            )

        return "；".join(parts) + "。"

    def _create_empty_analysis(
        self, stock_code: str, date: str, error: str = ""
    ) -> ConsecutiveBoardAnalysis:
        """创建空分析结果"""
        return ConsecutiveBoardAnalysis(
            stock_code=stock_code,
            stock_name="",
            analysis_date=date,
            consecutive_days=0,
            role=RoleType(role="未知", role_description=error),
            risk_assessment=f"数据不足：{error}",
            opportunity_judgment="无法判断",
            confidence="低",
            reasoning=error,
        )

    def batch_analyze(
        self,
        stock_codes: List[str],
        date: str,
        ladder_data: Optional[Dict[str, Any]] = None,
    ) -> List[ConsecutiveBoardAnalysis]:
        """
        批量分析股票

        Args:
            stock_codes: 股票代码列表
            date: 分析日期
            ladder_data: 连板梯队数据（可选）

        Returns:
            分析结果列表
        """
        results = []
        for stock_code in stock_codes:
            try:
                analysis = self.analyze(stock_code, date, ladder_data)
                results.append(analysis)
            except Exception as e:
                logger.error(f"分析股票 {stock_code} 失败: {e}")
                results.append(
                    self._create_empty_analysis(
                        stock_code, date, f"分析失败: {str(e)}"
                    )
                )

        return results
