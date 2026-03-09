"""
Critic智能体基类

对分析结果进行批评和验证
"""
import logging
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime

# 导入项目模块
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

from src.llm.client import LLMClient
from src.llm.prompt_engine import PromptEngine
from src.models.stock_models import CriticEvaluation


logger = logging.getLogger(__name__)


class CriticAgent:
    """Critic智能体基类"""

    def __init__(
        self,
        agent_type: Literal["consecutive_board", "trend_stock"],
        llm_client: Optional[LLMClient] = None,
        prompt_engine: Optional[PromptEngine] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化Critic智能体

        Args Args:
            agent_type: 被评估的Agent类型
            llm_client: LLM客户端实例
            prompt_engine: 提示词引擎实例
            config: 配置参数
        """
        self.agent_type = agent_type
        self.llm_client = llm_client
        self.prompt_engine = prompt_engine if prompt_engine is not None else PromptEngine()

        self.config = config if config is not None else {}

        # 默认配置
        self.default_config = {
            "strictness": "medium",  # low/medium/high
            "check_logic_consistency": True,
            "check_data_sufficiency": True,
            "check_conclusion_validity": True,
            "identify_issues": True,
            "suggest_improvements": True,
        }

    def evaluate(
        self,
        stock_code: str,
        stock_name: str,
        analysis_result: Dict[str, Any],
        analysis_date: Optional[str] = None,
    ) -> CriticEvaluation:
        """
        评估分析结果

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            analysis_result: 分析结果
            analysis_date: 分析日期

        Returns:
            Critic评估结果
        """
        logger.info(f"开始Critic评估: {stock_code}, Agent类型: {self.agent_type}")

        if analysis_date is None:
            analysis_date = datetime.now().strftime("%Y-%m-%d")

        # 1. 检查逻辑一致性
        logic_consistency, consistency_feedback = self._check_logic_consistency(
            analysis_result
        )

        # 2. 检查数据充分性
        data_sufficiency, missing_data = self._check_data_sufficiency(
            analysis_result
        )

        # 3. 检查结论合理性
        conclusion_validity, validity_feedback = self._check_conclusion_validity(
            analysis_result
        )

        # 4. 识别问题
        identified_issues, issue_severity = self._identify_issues(
            analysis_result, logic_consistency, data_sufficiency, conclusion_validity
        )

        # 5. 生成改进建议
        improvement_suggestions = self._generate_improvement_suggestions(
            analysis_result, identified_issues
        )

        # 6. 计算总体得分
        overall_score = self._calculate_overall_score(
            logic_consistency,
            data_sufficiency,
            conclusion_validity,
        )

        # 7. 判断是否接受分析
        accepted, rejection_reason = self._judge_acceptance(
            overall_score, issue_severity, self.config.get("strictness")
        )

        # 8. 构建评估结果
        evaluation = CriticEvaluation(
            agent_type=self.agent_type,
            stock_code=stock_code,
            stock_name=stock_name,
            evaluation_date=analysis_date,
            logic_consistency=logic_consistency,
            consistency_feedback=consistency_feedback,
            data_sufficiency=data_sufficiency,
            missing_data=missing_data,
            conclusion_validity=conclusion_validity,
            validity_feedback=validity_feedback,
            identified_issues=identified_issues,
            issue_severity=issue_severity,
            improvement_suggestions=improvement_suggestions,
            overall_score=overall_score,
            accepted=accepted,
            rejection_reason=rejection_reason,
        )

        logger.info(f"完成Critic评估: {stock_code}, 得分: {overall_score:.2f}")

        return evaluation

    def _check_logic_consistency(
        self, analysis_result: Dict[str, Any]
    ) -> tuple:
        """检查逻辑一致性"""
        if not self.config.get(
            "check_logic_consistency", self.default_config["check_logic_consistency"]
        ):
            return 1.0, "未检查"

        issues = []
        score = 1.0

        # 检查连板天数是否合理
        consecutive_days = analysis_result.get("consecutive_days", 0)
        role = analysis_result.get("role", {})
        if isinstance(role, dict):
            role_str = role.get("role", "")
        elif hasattr(role, "role"):
            role_str = role.role
        else:
            role_str = str(role)

        # 连板天数为0但角色为头狼/中军 - 不一致
        if consecutive_days <= 1 and any(
            x in role_str for x in ["头狼", "中军", "先锋"]
        ):
            issues.append("连板天数与角色不一致")
            score -= 0.3

        # 风险评估与机会判断冲突
        risk_assessment = analysis_result.get("risk_assessment", "")
        opportunity_judgment = analysis_result.get(
            "opportunity_judgment", ""
        )

        if "风险可控" in risk_assessment and "机会有限" in opportunity_judgment:
            # 风险可控但机会有限 - 这是合理的
            pass
        elif "高风险" in risk_assessment and "机会极大" in opportunity_judgment:
            # 高风险且机会极大 - 逻辑上有问题
            issues.append("风险评估与机会判断存在矛盾")
            score -= 0.2

        # 检查资金流向与封板强度
        fund_analysis = analysis_result.get("fund_analysis", {})
        board_strength = analysis_result.get("board_strength", 0)

        if fund_analysis:
            flow_direction = fund_analysis.get("flow_direction", "")
            if "大幅流出" in flow_direction and board_strength > 0.5:
                issues.append("资金大幅流出但板强度高 - 不一致")
                score -= 0.2

        # 归一化分数
        score = max(score, 0.0)
        feedback = "逻辑一致" if not issues else f"逻辑问题：{'；'.join(issues)}"

        return score, feedback

    def _check_data_sufficiency(
        self, analysis_result: Dict[str, Any]
    ) -> tuple:
        """检查数据充分性"""
        if not self.config.get(
            "check_data_sufficiency", self.default_config["check_data_sufficiency"]
        ):
            return 1.0, []

        missing_fields = []
        required_fields = [
            "stock_code",
            "stock_name",
            "consecutive_days",
            "turnover_analysis",
            "fund_analysis",
            "role",
        ]

        for field in required_fields:
            if field not in analysis_result or analysis_result[field] is None:
                missing_fields.append(field)

        # 检查分析数据的完整性
        turnover_analysis = analysis_result.get("turnover_analysis", {})
        if turnover_analysis:
            if "turnover" not in turnover_analysis:
                missing_fields.append("turnover_analysis.turnover")

        fund_analysis = analysis_result.get("fund_analysis", {})
        if fund_analysis:
            if "main_net_inflow" not in fund_analysis:
                missing_fields.append("fund_analysis.main_net_inflow")

        score = max(0, 1 - len(missing_fields) * 0.1)
        feedback = (
            "数据充分充分" if not missing_fields else f"缺失数据：{'、'.join(missing_fields)}"
        )

        return score, missing_fields

    def _check_conclusion_validity(
        self, analysis_result: Dict[str, Any]
    ) -> tuple:
        """检查结论合理性"""
        if not self.config.get(
            "check_conclusion_validity", self.default_config["check_conclusion_validity"]
        ):
            return 1.0, "未检查"

        issues = []
        score = 1.0

        # 检查置信度是否合理
        confidence = analysis_result.get("confidence", "")
        reasoning = analysis_result.get("reasoning", "")

        # 置信度高但推理过程短
        if confidence == "高" and len(reasoning) < 20:
            issues.append("置信度高但推理过程过于简单")
            score -= 0.2

        # 置信度高但存在严重风险
        risk_assessment = analysis_result.get("risk_assessment", "")
        if confidence == "高" and any(
            x in risk_assessment for x in ["极高风险", "风险失控"]
        ):
            issues.append("置信度高但风险评估为极高风险 - 矛盾")
            score -= 0.3

        score = max(score, 0.0)
        feedback = "结论合理" if not issues else f"结论问题：{'；'.join(issues)}"

        return score, feedback

    def _identify_issues(
        self,
        analysis_result: Dict[str, Any],
        logic_consistency: float,
        data_sufficiency: float,
        conclusion_validity: float,
    ) -> tuple:
        """识别问题"""
        if not self.config.get(
            "identify_issues", self.default_config["identify_issues"]
        ):
            return [], []

        issues = []
        severities = []

        # 逻辑一致性问题
        if logic_consistency < 0.7:
            issues.append("逻辑一致性不足")
            severities.append("high" if logic_consistency < 0.5 else "medium")

        # 数据充分性问题
        if data_sufficiency < 0.7:
            issues.append("数据充分性不足")
            severities.append("high" if data_sufficiency < 0.5 else "medium")

        # 结论合理性问题
        if conclusion_validity < 0.7:
            issues.append("结论合理性有待提高")
            severities.append("medium" if conclusion_validity < 0.5 else "low")

        # 连板高度相关
        consecutive_days = analysis_result.get("consecutive_days", 0)
        if consecutive_days >= 5:
            # 高板风险
            risk_assessment = analysis_result.get("risk_assessment", "")
            if "风险可控" in risk_assessment or "风险较低" in risk_assessment:
                issues.append("高板股票风险评估过于乐观")
                severities.append("medium")

        # 特殊动作检测
        special_actions = analysis_result.get("special_actions", {})
        if special_actions and len(special_actions) > 0:
            detected_count = sum(
                1
                for action in special_actions.values()
                if action.get("detected", False)
            )
            # 检测到多个特殊动作但推理中未体现
            reasoning = analysis_result.get("reasoning", "")
            if detected_count >= 2 and all(
                action not in reasoning for action in ["领涨", "逆跌", "反核"]
            ):
                issues.append("检测到多个特殊动作但推理中未充分说明")
                severities.append("low")

        return issues, severities

    def _generate_improvement_suggestions(
        self, analysis_result: Dict[str, Any], identified_issues: List[str]
    ) -> List[str]:
        """生成改进建议"""
        if not self.config.get(
            "suggest_improvements", self.default_config["suggest_improvements"]
        ):
            return []

        suggestions = []

        # 基于已识别问题的建议
        for issue in identified_issues:
            if "逻辑一致性" in issue:
                suggestions.append("建议重新检查分析逻辑，确保各部分分析保持一致")
            elif "数据充分性" in issue:
                suggestions.append("建议补充相关数据，特别是成交量、资金流向等关键指标")
            elif "结论合理性" in issue:
                suggestions.append("建议加强结论的支撑依据，提供更多数据支持")
            elif "高板股票" in issue:
                suggestions.append("高板股票应充分评估监管风险，避免过于乐观")
            elif "特殊动作" in issue:
                suggestions.append("应在推理中充分说明特殊动作对股价的影响")

        # 通用改进建议
        consecutive_days = analysis_result.get("consecutive_days", 0)

        if consecutive_days >= 4:
            if "监管风险" not in " ".join(identified_issues):
                suggestions.append("建议在高板分析中明确提及监管风险")

        # 同题材对比分析
        sector_premium = analysis_result.get("sector_premium")
        if sector_premium and sector_premium.get("is_leader"):
            if "题材龙头" not in " ".join(identified_issues):
                suggestions.append("作为题材龙头，应重点关注其对整个题材的带动作用")

        return suggestions

    def _calculate_overall_score(
        self,
        logic_consistency: float,
        data_sufficiency: float,
        conclusion_validity: float,
    ) -> float:
        """计算总体得分"""
        # 加权计算
        total_score = (
            logic_consistency * 0.4
            + data_sufficiency * 0.3
            + conclusion_validity * 0.3
        )

        return round(total_score, 2)

    def _judge_acceptance(
        self, overall_score: float, issue_severity: List[str], strictness: str
    ) -> tuple:
        """判断是否接受分析"""
        # 根据严格程度调整阈值
        if strictness == "high":
            threshold = 0.8
        elif strictness == "low":
            threshold = 0.5
        else:  # medium
            threshold = 0.6

        # 检查是否有严重问题
        has_high_severity = any(s == "high" for s in issue_severity)

        accepted = overall_score >= threshold and not has_high_severity

        if not accepted:
            if overall_score < threshold:
                rejection_reason = f"总体得分{overall_score:.2f}低于阈值{threshold}"
            elif has_high_severity:
                rejection_reason = "存在严重问题"
            else:
                rejection_reason = "综合评估未达到接受标准"
        else:
            rejection_reason = ""

        return accepted, rejection_reason


class ConsecutiveBoardCritic(CriticAgent):
    """连板Critic智能体"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompt_engine: Optional[PromptEngine] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            agent_type="consecutive_board",
            llm_client=llm_client,
            prompt_engine=prompt_engine,
            config=config,
        )


class TrendStockCritic(CriticAgent):
    """趋势Critic智能体"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompt_engine: Optional[PromptEngine] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            agent_type="trend_stock",
            llm_client=llm_client,
            prompt_engine=prompt_engine,
            config=config,
        )
