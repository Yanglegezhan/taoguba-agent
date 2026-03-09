#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心个股复盘智能体阵列 - CLI入口

支持连板核心复盘、趋势核心复盘、Critic评估和综合报告生成
"""
import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# 导入项目模块
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.data.kaipanla_stock_source import KaipanlaStockSource
from src.agent.consecutive_board_agent import ConsecutiveBoardStockAgent
from src.agent.trend_stock_agent import TrendStockAgent
from src.agent.critic_agent import ConsecutiveBoardCritic, TrendStockCritic
from src.agent.synthesis_agent import StockSynthesisAgent
from src.llm.client import create_client
from src.output.report_generator import ReportGenerator
from src.output.json_exporter import JsonExporter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("stock_replay_agent.log"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="核心个股复盘智能体阵列",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析指定日期的核心个股
  python -m stock_replay_agent --date 2025-02-10

  # 指定股票代码
  python -m stock_replay_agent --date 2025-02-10 --stocks 605398,002881

  # 只分析连板
  python -m stock_replay_agent --date 2025-02-10 --analysis-types consecutive_board

  # 指定输出格式
  python -m stock_replay_agent --date 2025-02-10 --output all

  # 使用特定LLM
  python -m stock_replay_agent --date 2025-02-10 --model glm-4

  # 禁用Critic评估
  python -m stock_replay_agent --date 2025-02-10 --no-critic

  # 验证数据源
  python -m stock_replay_agent --verify-data-source
        """,
    )

    # 必需参数
    parser.add_argument(
        "--date",
        type=str,
        help="分析日期，格式 YYYY-MM-DD",
    )

    # 可选参数
    parser.add_argument(
        "--stocks",
        type=str,
        default=None,
        help="指定股票代码，逗号分隔（如 605398,002881）",
    )

    parser.add_argument(
        "--analysis-types",
        type=str,
        default="consecutive_board,trend_stock",
        help="分析类型，逗号分隔（consecutive_board, trend_stock）",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="all",
        choices=["markdown", "json", "all"],
        help="输出格式",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="glm-4",
        help="LLM模型名称（glm-4, glm-4-plus, gpt-4等）",
    )

    parser.add_argument(
        "--provider",
        type=str,
        default="zhipu",
        help="LLM提供商（zhipu, openai, deepseek）",
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="LLM API密钥（默认从环境变量ZHIPUAI_API_KEY读取）",
    )

    parser.add_argument(
        "--no-critic",
        action="store_true",
        help="禁用Critic评估",
    )

    parser.add_argument(
        "--no-synthesis",
        action="store_true",
        help="禁用综合报告生成",
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="配置文件路径",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="输出目录路径",
    )

    parser.add_argument(
        "--verify-data-source",
        action="store_true",
        help="验证数据源接口并输出结果",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细输出模式",
    )

    return parser.parse_args()


def load_config(config_path: Optional[str]) -> dict:
    """加载配置文件"""
    if config_path is None:
        return {}

    config_file = Path(config_path)
    if not config_file.exists():
        logger.warning(f"配置文件不存在: {config_path}")
        return {}

    import yaml

    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_api_key(args) -> str:
    """获取API密钥"""
    # 优先使用命令行参数
    if args.api_key:
        return args.api_key

    # 从环境变量获取
    api_key = os.environ.get("ZHIPUAI_API_KEY")
    if api_key:
        return api_key

    # 从配置文件获取
    config = load_config(args.config)
    if "llm" in config and "api_key" in config["llm"]:
        return config["llm"]["api_key"]

    raise ValueError(
        "未找到API密钥，请通过 --api-key 参数或设置 ZHIPUAI_API_KEY 环境变量"
    )


def verify_data_source():
    """验证数据源接口"""
    logger.info("=" * 60)
    logger.info("数据源接口验证")
    logger.info("=" * 60)

    try:
        from src.data.kaipanla_stock_source import verify_data_source
        verify_data_source()
        logger.info("\n" + "=" * 60)
        logger.info("验证完成")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"验证失败: {e}")
        sys.exit(1)


def analyze_consecutive_board(
    agent: ConsecutiveBoardStockAgent,
    stock_codes: List[str],
    date: str,
    enable_critic: bool,
) -> List:
    """分析连板股票"""
    logger.info(f"开始分析连板股票: {len(stock_codes)}只")

    results = []
    critic_evaluations = []

    # 分析每只股票
    for stock_code in stock_codes:
        try:
            analysis = agent.analyze(stock_code, date)
            results.append(analysis)

            # Critic评估
            if enable_critic:
                critic = ConsecutiveBoardCritic()
                critic_eval = critic.evaluate(
                    stock_code=stock_code,
                    stock_name=analysis.stock_name,
                    analysis_result=analysis.model_dump(),
                    analysis_date=date,
                )
                critic_evaluations.append(critic_eval)

        except Exception as e:
            logger.error(f"分析股票 {stock_code} 失败: {e}")
            continue

    return results, critic_evaluations


def analyze_trend_stocks(
    agent: TrendStockAgent,
    stock_codes: List[str],
    date: str,
    enable_critic: bool,
) -> tuple:
    """分析趋势股票"""
    logger.info(f"开始分析趋势股票: {len(stock_codes)}只")

    results = []
    critic_evaluations = []

    # 分析每只股票
    for stock_code in stock_codes:
        try:
            analysis = agent.analyze(stock_code, date)
            results.append(analysis)

            # Critic评估
            if enable_critic:
                critic = TrendStockCritic()
                critic_eval = critic.evaluate(
                    stock_code=stock_code,
                    stock_name=analysis.stock_name,
                    analysis_result=analysis.model_dump(),
                    analysis_date=date,
                )
                critic_evaluations.append(critic_eval)

        except Exception as e:
            logger.error(f"分析股票 {stock_code} 失败: {e}")
            continue

    return results, critic_evaluations


def get_stock_codes_from_ladder(date: str, data_source: KaipanlaStockSource) -> List[str]:
    """从连板梯队获取股票代码"""
    ladder_data = data_source.get_consecutive_limit_up(date)
    ladder_details = ladder_data.get("ladder_details", {})

    stock_codes = []
    for days, stocks in ladder_details.items():
        for stock in stocks:
            stock_codes.append(stock.get("stock_code"))

    return stock_codes


def run_analysis(args):
    """运行分析流程"""
    logger.info("启动核心个股复盘智能体阵列")

    # 加载配置
    config = load_config(args.config)
    config.update(vars(args))

    # 获取API密钥
    try:
        api_key = get_api_key(args)
    except ValueError as e:
        logger.error(e)
        sys.exit(1)

    # 初始化LLM客户端
    llm_client = create_client(
        api_key=api_key,
        model=args.model,
        provider=args.provider,
    )

    # 初始化数据源
    data_source_config = config.get("data_source", {})
    data_source = KaipanlaStockSource(
        request_delay=data_source_config.get("kaipanla", {}).get(
            "request_delay", 0.5
        ),
        max_retries=data_source_config.get("kaipanla", {}).get(
            "max_retries", 3
        ),
        enable_cache=data_source_config.get("kaipanla", {}).get(
            "enable_cache", True
        ),
    )

    # 确定输出目录
    if args.output_dir is None:
        output_dir = project_root / "output"
    else:
        output_dir = Path(args.output_dir)

    # 确定分析日期
    date = args.date if args.date else datetime.now().strftime("%Y-%m-%d")

    # 确定要分析的股票代码
    if args.stocks:
        stock_codes = [s.strip() for s in args.stocks.split(",")]
    else:
        # 从连板梯队获取股票代码
        stock_codes = get_stock_codes_from_ladder(date, data_source)
        logger.info(f"从连板梯队获取到 {len(stock_codes)}只股票")

    if not stock_codes:
        logger.warning("未找到可分析的股票")
        sys.exit(0)

    # 确定分析类型
    analysis_types = [t.strip() for t in args.analysis_types.split(",")]

    # 初始化输出器
    report_generator = ReportGenerator(config.get("output", {}))
    json_exporter = JsonExporter(config.get("output", {}))

    # 存储所有分析结果
    all_consecutive_results = []
    all_trend_results = []
    all_critic_evaluations = []

    # 分析连板股票
    if "consecutive_board" in analysis_types:
        logger.info("=" * 60)
        logger.info("连板核心复盘")
        logger.info("=" * 60)

        consecutive_agent = ConsecutiveBoardStockAgent(
            data_source=data_source,
            llm_client=llm_client,
            config=config.get("analysis", {}).get("consecutive_board", {}),
        )

        consecutive_results, critic_evals = analyze_consecutive_board(
            consecutive_agent, stock_codes, date, not args.no_critic
        )

        all_consecutive_results = consecutive_results
        all_critic_evaluations.extend(critic_evals)

        # 生成连板报告
        if "markdown" in args.output or args.output == "all":
            md_report = report_generator.generate_consecutive_board_report(
                consecutive_results, date, critic_evals
            )
            report_generator.save_report(
                md_report, str(output_dir / "reports" / f"consecutive_board_{date.replace('-', '')}.md")
            )

        if "json" in args.output or args.output == "all":
            json_data = json_exporter.export_consecutive_board_analyses(consecutive_results)
            json_exporter.save_json(
                json_data,
                str(output_dir / "data" / f"consecutive_board_{date.replace('-', '')}.json"),
            )

    # 分析趋势股票
    if "trend_stock" in analysis_types:
        logger.info("=" * 60)
        logger.info("趋势核心复盘")
        logger.info("=" * 60)

        trend_agent = TrendStockAgent(
            data_source=data_source,
            llm_client=llm_client,
            config=config.get("analysis", {}).get("trend_stock", {}),
        )

        trend_results, critic_evals = analyze_trend_stocks(
            trend_agent, stock_codes, date, not args.no_critic
        )

        all_trend_results = trend_results
        all_critic_evaluations.extend(critic_evals)

        # 生成趋势报告
        if "markdown" in args.output or args.output == "all":
            md_report = report_generator.generate_trend_stock_report(
                trend_results, date, critic_evals
            )
            report_generator.save_report(
                md_report, str(output_dir / "reports" / f"trend_stock_{date.replace('-', '')}.md")
            )

        if "json" in args.output or args.output == "all":
            json_data = json_exporter.export_trend_stock_analyses(trend_results)
            json_exporter.save_json(
                json_data,
                str(output_dir / "data" / f"trend_stock_{date.replace('-', '')}.json"),
            )

    # 生成综合报告
    if not args.no_synthesis and args.output != "json":
        logger.info("=" * 60)
        logger.info("综合复盘")
        logger.info("=" * 60)

        synthesis_agent = StockSynthesisAgent(
            llm_client=llm_client,
            config=config.get("analysis", {}).get("synthesis", {}),
        )

        synthesis_report = synthesis_agent.synthesize(
            consecutive_board_results=[
                r.model_dump() for r in all_consecutive_results
            ],
            trend_stock_results=[r.model_dump() for r in all_trend_results],
            critic_evaluations=[e.model_dump() for e in all_critic_evaluations],
            analysis_date=date,
        )

        # 保存综合报告
        md_report = synthesis_agent.format_report(synthesis_report)
        synthesis_agent.save_report(
            synthesis_report,
            output_dir=str(output_dir / "reports"),
            formats=["markdown", "json"] if args.output == "all" else ["markdown"],
        )

    logger.info("=" * 60)
    logger.info("分析完成")
    logger.info("=" * 60)

    # 输出文件路径
    if "markdown" in args.output or args.output == "all":
        logger.info(f"Markdown报告目录: {output_dir / 'reports'}")
    if "json" in args.output or args.output == "all":
        logger.info(f"JSON数据目录: {output_dir / 'data'}")


def main():
    """主函数"""
    args = parse_args()

    # 设置详细日志
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 验证数据源模式
    if args.verify_data_source:
        verify_data_source()
        return

    # 运行分析
    try:
        run_analysis(args)
    except KeyboardInterrupt:
        logger.info("用户中断分析")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"分析失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
