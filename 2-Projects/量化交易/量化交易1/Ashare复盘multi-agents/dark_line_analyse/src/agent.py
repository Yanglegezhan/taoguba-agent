# -*- coding: utf-8 -*-
"""涨停暗线分析主Agent"""

import logging
from pathlib import Path
from typing import Optional


class DarkLineAgent:
    """涨停暗线分析Agent"""

    def __init__(self, config):
        """初始化Agent"""
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 延迟导入以避免循环导入
        from .data.kaipanla_source import KaipanlaSource
        from .data.data_source_adapter import DataSourceAdapter
        from .analysis.statistical_analyzer import StatisticalAnalyzer
        from .analysis.naming_analyzer import NamingAnalyzer
        from .analysis.dark_line_detector import DarkLineDetector
        from .llm.llm_analyzer import LLMAnalyzer
        from .output.report_generator import ReportGenerator

        # 获取配置
        analysis_config = config.get_analysis_config()
        self.llm_config = config.get_llm_config()
        output_config = config.get_output_config()

        # 初始化各组件
        self.kaipanla_source = KaipanlaSource(config)
        self.data_source = DataSourceAdapter(config)  # 使用适配器自动选择数据源
        self.statistical_analyzer = StatisticalAnalyzer(analysis_config)
        self.naming_analyzer = NamingAnalyzer(analysis_config)
        self.dark_line_detector = DarkLineDetector(analysis_config)
        self.llm_analyzer = LLMAnalyzer(self.llm_config)
        self.report_generator = ReportGenerator(
            output_dir=output_config.report_dir,
            output_format=output_config.format
        )

    def analyze(self, date: str):
        """执行暗线分析"""
        self.logger.info(f"Starting dark line analysis for {date}")

        # 1. 获取涨停个股列表
        self.logger.info("Fetching limit up stocks...")
        limit_up_stocks = self.kaipanla_source.get_limit_up_stocks(date)
        self.logger.info(f"Found {len(limit_up_stocks)} limit up stocks")

        if not limit_up_stocks:
            self.logger.warning("No limit up stocks found for date")
            return self._create_empty_result(date)

        # 2. 获取基础信息和财务数据
        self.logger.info("Fetching stock basic and financial data...")
        enriched_stocks = []
        for stock in limit_up_stocks:
            if isinstance(stock, dict):
                enriched = self.data_source.enrich_stock_basic(
                    stock_code=stock['stock_code'],
                    stock_name=stock.get('stock_name', ''),
                    limit_up_info=stock,
                    trade_date=date
                )
                enriched_stocks.append(enriched)
            else:
                enriched_stocks.append(stock)
        self.logger.info(f"Enriched {len(enriched_stocks)} stocks")

        # 3. 执行统计学分析
        self.logger.info("Performing statistical analysis...")
        stat_analysis = self.statistical_analyzer.full_analyze(enriched_stocks)

        # 4. 执行命名语义分析
        self.logger.info("Performing naming analysis...")
        naming_results = self.naming_analyzer.analyze_batch(enriched_stocks)

        # 5. 检测暗线
        self.logger.info("Detecting dark lines...")
        dark_lines = self.dark_line_detector.detect(
            stat_analysis=stat_analysis,
            naming_analysis=naming_results,
            stocks=enriched_stocks
        )
        self.logger.info(f"Detected {len(dark_lines)} dark lines")

        # 6. LLM解读（可选）
        llm_interpretation = None
        if dark_lines and self.llm_config and self.llm_config.api_key:
            try:
                self.logger.info("Running LLM interpretation...")
                llm_interpretation = self.llm_analyzer.analyze_dark_lines(
                    dark_lines=dark_lines,
                    stat_analysis=stat_analysis,
                    naming_analysis=naming_results
                )
            except Exception as e:
                self.logger.warning(f"LLM interpretation failed: {e}")

        # 7. 构建检测结果
        from .models.data_models import DarkLineDetection
        detection = DarkLineDetection(
            analysis_date=date,
            limit_up_count=len(enriched_stocks),
            statistical_analysis=stat_analysis,
            naming_analysis=naming_results,
            dark_lines=dark_lines,
            llm_interpretation=llm_interpretation
        )

        # 8. 生成报告
        self.logger.info("Generating reports...")
        self.report_generator.generate(detection, enriched_stocks=enriched_stocks, include_stock_details=True)

        return detection

    def _create_empty_result(self, date: str):
        """创建空结果"""
        from .models.data_models import (
            DarkLineDetection,
            StatisticalAnalysis,
            NamingAnalysis,
            EmptyAnalysis
        )
        return DarkLineDetection(
            analysis_date=date,
            limit_up_count=0,
            statistical_analysis=EmptyAnalysis(),
            naming_analysis=NamingAnalysis(
                feature_summary={},
                feature_ratio={},
                similar_names=[],
                prefix_patterns={}
            ),
            dark_lines=[],
            llm_interpretation=None
        )
