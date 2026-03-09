"""
综合复盘智能体

综合四个智能体的分析结果，生成最终复盘报告
"""
import logging
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
import json

# 导入项目模块
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

from src.llm.client import LLMClient
from src.llm.prompt_engine import PromptEngine
from src.models.stock_models import SynthesisReport


logger = logging.getLogger(__name__)


class StockSynthesisAgent:
    """综合复盘智能体"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompt_engine: Optional[PromptEngine] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化综合复盘智能体

        Args:
            llm_client: LLM客户端实例
            prompt_engine: 提示词引擎实例
            config: 配置参数
        """
        self.llm_client = llm_client
        self.prompt_engine = prompt_engine if prompt_engine is not None else PromptEngine()

        self.config = config if config is not None else {}

        # 默认配置
        self.default_config = {
            "read_external_reports": True,
            "external_report_paths": [
                "../index_replay_agent/output/reports",
                "../sentiment_replay_agent/output/sentiment/reports",
                "../Theme_repay_agent/output/reports",
                "../dark_line_analyse/output/reports",
            ],
            "highlight_contradictions": True,
        }

    def synthesize(
        self,
        consecutive_board_results: List[Dict[str, Any]],
        trend_stock_results: List[Dict[str, Any]],
        critic_evaluations: List[Dict[str, Any]],
        analysis_date: Optional[str] = None,
        external_context: Optional[Dict[str, Any]] = None,
    ) -> SynthesisReport:
        """
        综合分析结果

        Args:
            consecutive_board_results: 连板分析结果列表
            trend_stock_results: 趋势股分析结果列表
            critic_evaluations: Critic评估结果列表
            analysis_date: 分析日期
            external_context: 外部报告上下文

        Returns:
            综合复盘报告
        """
        if analysis_date is None:
            analysis_date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"开始综合分析，日期: {analysis_date}")
        logger.info(
            f"连板分析: {len(consecutive_board_results)}个，"
            f"趋势分析: {len(trend_stock_results)}个，"
            f"Critic评估: {len(critic_evaluations)}个"
        )

        # 1. 获取外部报告上下文
        if external_context is None:
            external_context = self._load_external_context(analysis_date)

        # 2. 分析一致性结论
        consistent_conclusions = self._find_consistent_conclusions(
            consecutive_board_results, trend_stock_results, critic_evaluations
        )

        # 3. 发现矛盾点
        contradictions = self._identify_contradictions(
            consecutive_board_results, trend_stock_results, critic_evaluations
        )

        # 4. 题材综合分析
        sector_analysis = self._analyze_sectors(
            consecutive_board_results, trend_stock_results
        )

        # 5. 生成综合摘要
        summary = self._generate_summary(
            consecutive_board_results,
            trend_stock_results,
            critic_evaluations,
            external_context,
            contradictions,
        )

        # 6. 生成整体操作建议
        overall_recommendation, specific_recommendations = (
            self._generate_recommendations(
                consecutive_board_results,
                trend_stock_results,
                critic_evaluations,
                sector_analysis,
            )
        )

        # 7. 构建综合报告
        report = SynthesisReport(
            report_date=analysis_date,
            report_title=f"核心个股复盘报告 ({analysis_date})",
            consecutive_board_stocks=consecutive_board_results,
            trend_stocks=trend_stock_results,
            critic_evaluations=critic_evaluations,
            summary=summary,
            consistent_conclusions=consistent_conclusions,
            contradictions=contradictions,
            sector_analysis=sector_analysis,
            overall_recommendation=overall_recommendation,
            specific_recommendations=specific_recommendations,
            external_context=external_context,
            created_at=datetime.now().isoformat(),
        )

        logger.info("完成综合分析")

        return report

    def _load_external_context(
        self, date: str
    ) -> Dict[str, Any]:
        """加载外部报告上下文"""
        if not self.config.get(
            "read_external_reports", self.default_config["read_external_reports"]
        ):
            return {}

        external_context = {}
        report_paths = self.config.get(
            "external_report_paths", self.default_config["external_report_paths"]
        )

        base_dir = Path(__file__).resolve().parents[2]

        for path in report_paths:
            report_dir = base_dir / path
            if report_dir.exists():
                # 查找当日的报告文件
                date_str = date.replace("-", "")
                pattern = f"*{date_str}*.md"
                reports = list(report_dir.glob(pattern))

                if reports:
                    # 读取最新报告
                    latest_report = max(reports, key=lambda p: p.stat().st_mtime)
                    try:
                        content = latest_report.read_text(encoding="utf-8")
                        external_context[str(report_dir)] = {
                            "file": str(latest_report),
                            "content": content,
                            "summary": self._extract_summary(content),
                        }
                        logger.info(f"加载外部报告: {latest_report.name}")
                    except Exception as e:
                        logger.warning(f"读取报告失败 {latest_report}: {e}")

        return external_context

    def _extract_summary(self, content: str) -> str:
        """从报告中提取摘要"""
        # 尝试提取摘要部分
        lines = content.split("\n")
        summary_lines = []
        in_summary = False

        for line in lines:
            if "## 摘要" in line or "# 摘要" in line:
                in_summary = True
                continue
            if in_summary and line.startswith("##"):
                break
            if in_summary and line.strip():
                summary_lines.append(line)

        if summary_lines:
            return "\n".join(summary_lines[:10])  # 取前10行

        # 如果没有找到摘要，返回前500字符
        return content[:500]

    def _find_consistent_conclusions(
        self,
        consecutive_board_results: List[Dict[str, Any]],
        trend_stock_results: List[Dict[str, Any]],
        critic_evaluations: List[Dict[str, Any]],
    ) -> List[str]:
        """找出一一致性结论"""
        conclusions = []

        # 分析Critic接受的分析
        accepted_analysis = []
        for eval in critic_evaluations:
            if eval.get("accepted", False):
                stock_code = eval.get("stock_code", "")
                agent_type = eval.get("agent_type", "")
                accepted_analysis.append(f"{stock_code}({agent_type})")

        if accepted_analysis:
            conclusions.append(
                f"Critic接受的分析: {', '.join(accepted_analysis)}"
            )

        # 统计连板梯队健康度
        if consecutive_board_results:
            high_confidence_stocks = [
                s.get("stock_name", "")
                for s in consecutive_board_results
                if s.get("confidence") == "高"
            ]
            if high_confidence_stocks:
                conclusions.append(
                    f"高置信度连板股: {', '.join(high_confidence_stocks)}"
                )

        # 统计趋势股健康度
        if trend_stock_results:
            strong_trends = [
                s.get("stock_name", "")
                for s in trend_stock_results
                if "主升浪" in s.get("trend_pattern", {}).get("pattern_type", "")
            ]
            if strong_trends:
                conclusions.append(
                    f"主升浪趋势股: {', '.join(strong_trends)}"
                )

        return conclusions

    def _identify_contradictions(
        self,
        consecutive_board_results: List[Dict[str, Any]],
        trend_stock_results: List[Dict[str, Any]],
        critic_evaluations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """识别矛盾点"""
        contradictions = []

        # 检查Critic拒绝的分析
        rejected_analysis = []
        for eval in critic_evaluations:
            if not eval.get("accepted", True):
                stock_code = eval.get("stock_code", "")
                reason = eval.get("rejection_reason", "")
                contradictions.append(
                    {
                        "type": "critic_rejection",
                        "stock_code": stock_code,
                        "description": f"Critic拒绝分析: {reason}",
                        "severity": "medium",
                    }
                )
                rejected_analysis.append(stock_code)

        # 检查同一股票的连板分析和趋势分析（如果有重叠）
        consecutive_stocks = {
            s.get("stock_code"): s for s in consecutive_board_results
        }
        trend_stocks = {
            s.get("stock_code"): s for s in trend_stock_results
        }

        for stock_code in set(consecutive_stocks.keys()) & set(trend_stocks.keys()):
            # 同一只股票同时出现在连板和趋势分析中
            consecutive_risk = consecutive_stocks[stock_code].get(
                "risk_assessment", ""
            )
            trend_risk = trend_stocks[stock_code].get("risk_level", "")

            if "高风险" in consecutive_r and trend_risk == "低":
                contradictions.append(
                    {
                        "type": "risk_assessment_conflict",
                        "stock_code": stock_code,
                        "description": f"连板分析认为高风险，趋势分析认为低风险",
                        "severity": "low",
                    }
                )

        return contradictions

    def _analyze_sectors(
        self,
        consecutive_board_results: List[Dict[str, Any]],
        trend_stock_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """分析题材"""
        sectors = {}

        # 统计连板题材
        sector_leaders = []
        for stock in consecutive_board_results:
            sector_premium = stock.get("sector_premium")
            if sector_premium and sector_premium.get("is_leader", False):
                sector = sector_premium.get("sector", "")
                if sector:
                    sector_leaders.append(sector)

        if sector_leaders:
            sectors["leaders"] = list(set(sector_leaders))

        # 统计热门题材（出现次数>=2）
        sector_counts = {}
        for stock in consecutive_board_results:
            sector_premium = stock.get("sector_premium")
            if sector_premium:
                sector = sector_premium.get("sector", "")
                if sector:
                    sector_counts[sector] = sector_counts.get(sector, 0) + 1

        hot_sectors = [s for s, c in sector_counts.items() if c >= 2]
        if hot_sectors:
            sectors["hot"] = hot_sectors

        # 分析题材健康度
        if hot_sectors:
            sectors["health"] = "活跃" if len(hot_sectors) >= 3 else "一般"
        else:
            sectors["health"] = "清淡"

        return sectors

    def _generate_summary(
        self,
        consecutive_board_results: List[Dict[str, Any]],
        trend_stock_results: List[Dict[str, Any]],
        critic_evaluations: List[Dict[str, Any]],
        external_context: Dict[str, Any],
        contradictions: List[Dict[str, Any]],
    ) -> str:
        """生成综合摘要"""
        parts = [f"## 核心个股复盘摘要\n"]

        # 连板板块摘要
        if consecutive_board_results:
            parts.append(f"### 连板板块分析")
            parts.append(f"- 分析股票数量: {len(consecutive_board_results)}")
            high_confidence = sum(
                1 for s in consecutive_board_results if s.get("confidence") == "高"
            )
            parts.append(f"- 高置信度分析: {high_confidence}个")
            parts.append("")

        # 趋势板块摘要
        if trend_stock_results:
            parts.append(f"### 趋势板块分析")
            parts.append(f"- 分析股票数量: {len(trend_stock_results)}")
            main_trend_count = sum(
                1
                for s in trend_stock_results
                if "主升浪" in s.get("trend_pattern", {}).get("pattern_type", "")
            )
            parts.append(f"- 主升浪数量: {main_trend_count}个")
            parts.append("")

        # Critic摘要
        if critic_evaluations:
            accepted_count = sum(
                1 for e in critic_evaluations if e.get("accepted", False)
            )
            parts.append(f"### Critic评估")
            parts.append(f"- 接受率: {accepted_count}/{len(critic_evaluations)}")
            parts.append("")

        # 矛盾点摘要
        if contradictions:
            parts.append(f"### 发现的矛盾点")
            parts.append(f"- 矛盾数量: {len(contradictions)}")
            for contradiction in contradictions[:3]:
                parts.append(f"- {contradiction.get('description', '')}")
            parts.append("")

        # 外部上下文摘要
        if external_context:
            parts.append(f"### 外部报告集成")
            parts.append(f"- 集成报告数量: {len(external_context)}")
            parts.append("")

        return "\n".join(parts)

    def _generate_recommendations(
        self,
        consecutive_board_results: List[Dict[str, Any]],
        trend_stock_results: List[Dict[str, Any]],
        critic_evaluations: List[Dict[str, Any]],
        sector_analysis: Dict[str, Any],
    ) -> tuple:
        """生成操作建议"""
        specific_recommendations = []

        # 连板板块建议
        for stock in consecutive_board_results:
            stock_code = stock.get("stock_code", "")
            stock_name = stock.get("stock_name", "")
            confidence = stock.get("confidence", "")
            opportunity = stock.get("opportunity_judgment", "")

            recommendation = {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "action": "观望",
                "reason": "",
            }

            if confidence == "高" and "机会" in opportunity:
                recommendation["action"] = "关注"
                recommendation["reason"] = f"{opportunity}，高置信度"
            elif confidence == "中" and "机会" in opportunity:
                recommendation["action"] = "谨慎关注"
                recommendation["reason"] = f"{opportunity}，中置信度"
            elif "风险" in opportunity:
                recommendation["action"] = "回避"
                recommendation["reason"] = f"{opportunity}，风险较高"

            specific_recommendations.append(recommendation)

        # 趋势板块建议
        for stock in trend_stock_results:
            stock_code = stock.get("stock_code", "")
            stock_name = stock.get("stock_name", "")
            opportunity = stock.get("opportunity_level", "")
            sustainability = stock.get("sustainability", "")

            recommendation = {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "action": "观望",
                "reason": "",
            }

            if opportunity == "高" and sustainability == "强":
                recommendation["action"] = "考虑参与"
                recommendation["reason"] = f"机会高且趋势强"
            elif opportunity == "中":
                recommendation["action"] = "谨慎参与"
                recommendation["reason"] = f"机会中等"
            elif opportunity == "低":
                recommendation["action"] = "观望"
                recommendation["reason"] = f"机会较低"

            specific_recommendations.append(recommendation)

        # 整体建议
        if specific_recommendations:
            high_opportunity = sum(
                1
                for r in specific_recommendations
                if r["action"] in ["关注", "考虑参与"]
            )
            total = len(specific_recommendations)

            if high_opportunity > total * 0.6:
                overall_recommendation = "积极"
            elif high_opportunity > total * 0.3:
                overall_recommendation = "中性"
            else:
                overall_recommendation = "谨慎"
        else:
            overall_recommendation = "中性"

        return overall_recommendation, specific_recommendations

    def format_report(self, report: SynthesisReport) -> str:
        """格式化报告为Markdown"""
        lines = []

        # 标题
        lines.append(f"# {report.report_title}")
        lines.append("")
        lines.append(f"**报告日期**: {report.report_date}")
        lines.append(f"**生成时间**: {report.created_at}")
        lines.append("")

        # 摘要
        lines.append("## 摘要")
        lines.append(report.summary)
        lines.append("")

        # 一致性结论
        if report.consistent_conclusions:
            lines.append("## 一致性结论")
            for conclusion in report.consistent_conclusions:
                lines.append(f"- {conclusion}")
            lines.append("")

        # 矛盾点
        if report.contradictions:
            lines.append("## 矛盾点")
            for contradiction in report.contradictions:
                severity_emoji = {
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢",
                }.get(contradiction.get("severity", "low"), "")
                lines.append(
                    f"{severity_emoji} **{contradiction.get('type', '')}**: {contradiction.get('description', '')}"
                )
            lines.append("")

        # 题材分析
        if report.sector_analysis:
            lines.append("## 题材分析")
            for key, value in report.sector_analysis.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")

        # 操作建议
        lines.append("## 操作建议")
        lines.append(f"### 整体建议: {report.overall_recommendation}")
        lines.append("")

        lines.append("### 个股建议")
        lines.append("| 股票代码 | 股票名称 | 建议 | 原因 |")
        lines.append("|---------|---------|------|------|")
        for rec in report.specific_recommendations:
            action_emoji = {
                "关注": "👀",
                "考虑参与": "✅",
                "谨慎关注": "⚠️",
                "谨慎参与": "⚠️",
                "观望": "⏸️",
                "回避": "❌",
            }.get(rec["action"], "")
            lines.append(
                f"| {rec['stock_code']} | {rec['stock_name']} | {action_emoji} {rec['action']} | {rec['reason']} |"
            )

        # 连板分析详情
        if report.consecutive_board_stocks:
            lines.append("")
            lines.append("## 连板分析详情")
            for stock in report.consecutive_board_stocks:
                lines.append("")
                lines.append(f"### {stock['stock_name']} ({stock['stock_code']})")
                lines.append(f"- **连板天数**: {stock.get('consecutive_days', 0)}板")
                lines.append(
                    f"- **角色**: {stock.get('role', {}).get('role', '')}"
                )
                lines.append(f"- **置信度**: {stock.get('confidence', '')}")
                lines.append(f"- **风险评估**: {stock.get('risk_assessment', '')}")
                lines.append(f"- **机会判断**: {stock.get('opportunity_judgment', '')}")

        # 趋势分析详情
        if report.trend_stocks:
            lines.append("")
            lines.append("## 趋势分析详情")
            for stock in report.trend_stocks:
                lines.append("")
                lines.append(f"### {stock['stock_name']} ({stock['stock_code']})")
                pattern = stock.get("trend_pattern", {})
                lines.append(
                    f"- **趋势形态**: {pattern.get('pattern_type', '')} ({pattern.get('stage', '')})"
                )
                lines.append(f"- **置信度**: {stock.get('confidence', '')}")
                lines.append(f"- **风险等级**: {stock.get('risk_level', '')}")
                lines.append(f"- **机会等级**: {stock.get('opportunity_level', '')}")

        # Critic评估详情
        if report.critic_evaluations:
            lines.append("")
            lines.append("## Critic评估详情")
            for eval in report.critic_evaluations:
                lines.append("")
                lines.append(
                    f"### {eval['stock_name']} ({eval['stock_code']}) - {eval['agent_type']}"
                )
                status = "✅ 接受" if eval.get("accepted") else "❌ 拒绝"
                lines.append(f"- **评估结果**: {status}")
                lines.append(
                    f"- **总体得分**: {eval.get('overall_score', 0):.2f}"
                )
                if not eval.get("accepted"):
                    lines.append(
                        f"- **拒绝原因**: {eval.get('rejection_reason', '')}"
                    )
                if eval.get("identified_issues"):
                    lines.append(f"- **识别的问题**:")
                    for issue in eval["identified_issues"]:
                        lines.append(f"  - {issue}")

        return "\n".join(lines)

    def export_json(self, report: SynthesisReport) -> Dict[str, Any]:
        """导出报告为JSON格式"""
        # 使用Pydantic的model_dump
        return report.model_dump(mode="json", exclude_none=True)

    def save_report(
        self,
        report: SynthesisReport,
        output_dir: Optional[str] = None,
        formats: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        保存报告

        Args:
            report: 综合报告
            output_dir: 输出目录
            formats: 输出格式列表 (markdown, json]

        Returns:
            保存的文件路径字典
        """
        if formats is None:
            formats = ["markdown", "json"]

        if output_dir is None:
            output_dir = Path(__file__).resolve().parents[2] / "output" / "reports"

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        saved_files = {}

        # 保存Markdown报告
        if "markdown" in formats:
            md_content = self.format_report(report)
            date_str = report.report_date.replace("-", "")
            md_file = output_path / f"stock_replay_{date_str}.md"
            md_file.write_text(md_content, encoding="utf-8")
            saved_files["markdown"] = str(md_file)
            logger.info(f"保存Markdown报告: {md_file}")

        # 保存JSON报告
        if "json" in formats:
            json_data = self.export_json(report)
            date_str = report.report_date.replace("-", "")
            json_file = output_path / "data" / f"stock_replay_{date_str}.json"
            json_file.parent.mkdir(parents=True, exist_ok=True)
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            saved_files["json"] = str(json_file)
            logger.info(f"保存JSON报告: {json_file}")

        return saved_files
