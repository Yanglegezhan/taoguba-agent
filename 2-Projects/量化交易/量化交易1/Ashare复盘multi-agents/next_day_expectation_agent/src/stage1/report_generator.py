"""
报告生成器

集成现有的三个复盘agents（大盘分析、情绪分析、题材分析），
生成三份结构化报告。
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from ..common.logger import get_logger
from ..common.models import MarketReport, EmotionReport, ThemeReport

logger = get_logger(__name__)


class ReportGenerator:
    """报告生成器
    
    职责：
    - 调用现有的大盘分析Agent生成Market_Report
    - 调用现有的情绪分析Agent生成Emotion_Report
    - 调用现有的题材分析Agent生成Theme_Report
    - 将报告转换为标准化的数据模型
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化报告生成器
        
        Args:
            config: 配置字典，包含各个agent的路径和参数
        """
        self.config = config or {}
        
        # 获取项目根目录
        self.project_root = Path(__file__).parent.parent.parent.parent
        
        # 设置各个agent的路径
        self.index_agent_path = self.project_root / "index_replay_agent"
        self.sentiment_agent_path = self.project_root / "sentiment_replay_agent"
        self.theme_agent_path = self.project_root / "Theme_repay_agent"
        
        logger.info("报告生成器初始化完成")
        logger.debug(f"大盘分析Agent路径: {self.index_agent_path}")
        logger.debug(f"情绪分析Agent路径: {self.sentiment_agent_path}")
        logger.debug(f"题材分析Agent路径: {self.theme_agent_path}")
    
    def generate_market_report(
        self, 
        date: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> MarketReport:
        """生成大盘分析报告
        
        Args:
            date: 分析日期，格式：YYYY-MM-DD
            market_data: 可选的市场数据，如果提供则不调用agent
            
        Returns:
            MarketReport: 大盘分析报告对象
            
        Raises:
            RuntimeError: 如果报告生成失败
        """
        logger.info(f"开始生成大盘分析报告: {date}")
        
        try:
            # 调用index_replay_agent
            result = self._call_index_agent(date)
            
            # 解析结果并转换为MarketReport
            report = self._parse_market_report(result, date)
            
            logger.info("大盘分析报告生成成功")
            return report
            
        except Exception as e:
            logger.error(f"生成大盘分析报告失败: {e}")
            raise RuntimeError(f"生成大盘分析报告失败: {e}")
    
    def generate_emotion_report(
        self,
        date: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> EmotionReport:
        """生成情绪分析报告
        
        Args:
            date: 分析日期，格式：YYYY-MM-DD
            market_data: 可选的市场数据，如果提供则不调用agent
            
        Returns:
            EmotionReport: 情绪分析报告对象
            
        Raises:
            RuntimeError: 如果报告生成失败
        """
        logger.info(f"开始生成情绪分析报告: {date}")
        
        try:
            # 调用sentiment_replay_agent
            result = self._call_sentiment_agent(date)
            
            # 解析结果并转换为EmotionReport
            report = self._parse_emotion_report(result, date)
            
            logger.info("情绪分析报告生成成功")
            return report
            
        except Exception as e:
            logger.error(f"生成情绪分析报告失败: {e}")
            raise RuntimeError(f"生成情绪分析报告失败: {e}")
    
    def generate_theme_report(
        self,
        date: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> ThemeReport:
        """生成题材分析报告
        
        Args:
            date: 分析日期，格式：YYYY-MM-DD
            market_data: 可选的市场数据，如果提供则不调用agent
            
        Returns:
            ThemeReport: 题材分析报告对象
            
        Raises:
            RuntimeError: 如果报告生成失败
        """
        logger.info(f"开始生成题材分析报告: {date}")
        
        try:
            # 调用Theme_repay_agent
            result = self._call_theme_agent(date)
            
            # 解析结果并转换为ThemeReport
            report = self._parse_theme_report(result, date)
            
            logger.info("题材分析报告生成成功")
            return report
            
        except Exception as e:
            logger.error(f"生成题材分析报告失败: {e}")
            raise RuntimeError(f"生成题材分析报告失败: {e}")
    
    def _call_index_agent(self, date: str) -> Dict[str, Any]:
        """调用大盘分析Agent
        
        Args:
            date: 分析日期
            
        Returns:
            Dict: Agent返回的结果
        """
        logger.debug(f"调用大盘分析Agent: {date}")
        
        try:
            # 构建命令
            cmd = [
                sys.executable,
                "-m", "src.cli",
                "--date", date,
                "--output-format", "json",
                "--quiet"
            ]
            
            # 设置环境变量以支持UTF-8编码
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # 执行命令（无超时限制）
            result = subprocess.run(
                cmd,
                cwd=str(self.index_agent_path),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # 替换无法编码的字符
                env=env
            )
            
            if result.returncode != 0:
                logger.error(f"大盘分析Agent stderr: {result.stderr}")
                raise RuntimeError(f"大盘分析Agent执行失败: {result.stderr}")
            
            # 提取JSON部分（可能有进度信息在前面）
            stdout = result.stdout.strip()
            
            # 查找所有JSON对象（index_replay_agent输出多个JSON对象）
            json_objects = []
            current_pos = 0
            
            while current_pos < len(stdout):
                # 查找下一个JSON开始位置
                json_start = -1
                for i in range(current_pos, len(stdout)):
                    if stdout[i] in ['{', '[']:
                        json_start = i
                        break
                
                if json_start == -1:
                    break
                
                # 尝试解析JSON对象
                try:
                    decoder = json.JSONDecoder()
                    obj, end_idx = decoder.raw_decode(stdout, json_start)
                    json_objects.append(obj)
                    current_pos = json_start + end_idx
                except json.JSONDecodeError:
                    current_pos = json_start + 1
            
            if not json_objects:
                logger.error(f"未找到有效的JSON输出，完整输出前1000字符: {stdout[:1000]}")
                raise RuntimeError("大盘分析Agent未返回有效的JSON数据")
            
            # 合并所有JSON对象到一个字典
            merged_output = {}
            for obj in json_objects:
                if isinstance(obj, dict):
                    merged_output.update(obj)
            
            logger.debug(f"成功解析大盘分析报告，共{len(json_objects)}个JSON对象")
            return merged_output
            
        except json.JSONDecodeError as e:
            raise RuntimeError(f"解析大盘分析Agent输出失败: {e}")
        except Exception as e:
            raise RuntimeError(f"调用大盘分析Agent失败: {e}")
    
    def _call_sentiment_agent(self, date: str) -> Dict[str, Any]:
        """调用情绪分析Agent
        
        Args:
            date: 分析日期
            
        Returns:
            Dict: Agent返回的结果
        """
        logger.debug(f"调用情绪分析Agent: {date}")
        
        try:
            # 构建命令
            cmd = [
                sys.executable,
                "sentiment_cli.py",
                "--date", date,
                "--format", "json",
                "--quiet"
            ]
            
            # 设置环境变量以支持UTF-8编码
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # 执行命令（无超时限制）
            result = subprocess.run(
                cmd,
                cwd=str(self.sentiment_agent_path),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # 替换无法编码的字符
                env=env
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"情绪分析Agent执行失败: {result.stderr}")
            
            # 读取输出文件（sentiment_cli.py会生成JSON文件）
            output_file = self.sentiment_agent_path / "output" / "sentiment" / "reports" / f"sentiment_{date.replace('-', '')}.json"
            
            if not output_file.exists():
                raise RuntimeError(f"情绪分析报告文件不存在: {output_file}")
            
            with open(output_file, 'r', encoding='utf-8') as f:
                output = json.load(f)
            
            return output
            
        except json.JSONDecodeError as e:
            raise RuntimeError(f"解析情绪分析Agent输出失败: {e}")
        except Exception as e:
            raise RuntimeError(f"调用情绪分析Agent失败: {e}")
    
    def _call_theme_agent(self, date: str) -> Dict[str, Any]:
        """调用题材分析Agent
        
        Args:
            date: 分析日期
            
        Returns:
            Dict: Agent返回的结果
        """
        logger.debug(f"调用题材分析Agent: {date}")
        
        try:
            # 构建命令
            cmd = [
                sys.executable,
                "theme_cli.py",
                "--date", date,
                "--format", "json",
                "--no-save",  # 不保存文件，直接返回结果
                "--quiet"
            ]
            
            # 设置环境变量以支持UTF-8编码
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # 执行命令（无超时限制）
            result = subprocess.run(
                cmd,
                cwd=str(self.theme_agent_path),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # 替换无法编码的字符
                env=env
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"题材分析Agent执行失败: {result.stderr}")
            
            # 解析JSON输出
            output = json.loads(result.stdout)
            return output
            
        except json.JSONDecodeError as e:
            raise RuntimeError(f"解析题材分析Agent输出失败: {e}")
        except Exception as e:
            raise RuntimeError(f"调用题材分析Agent失败: {e}")
            raise RuntimeError(f"调用题材分析Agent失败: {e}")
    
    def _parse_market_report(self, data: Dict[str, Any], date: str) -> MarketReport:
        """解析大盘分析报告数据
        
        Args:
            data: Agent返回的原始数据
            date: 分析日期
            
        Returns:
            MarketReport: 标准化的大盘报告对象
        """
        try:
            # 提取关键指标
            current_price = data.get("current_price", 0.0)
            change_pct = data.get("change_pct", 0.0)
            
            # 提取支撑压力位
            support_levels = data.get("support_levels", [])
            resistance_levels = data.get("resistance_levels", [])
            
            # 提取短期预期
            short_term = data.get("short_term", {})
            scenario = short_term.get("scenario", "")
            target_range = short_term.get("target", [])
            
            # 提取长期预期
            long_term = data.get("long_term", {})
            trend = long_term.get("trend", "")
            
            # 构建MarketReport对象
            report = MarketReport(
                date=date,
                current_price=current_price,
                change_pct=change_pct,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                short_term_scenario=scenario,
                short_term_target=target_range,
                long_term_trend=trend,
                raw_data=data
            )
            
            return report
            
        except Exception as e:
            logger.error(f"解析大盘分析报告失败: {e}")
            raise ValueError(f"解析大盘分析报告失败: {e}")
    
    def _parse_emotion_report(self, data: Dict[str, Any], date: str) -> EmotionReport:
        """解析情绪分析报告数据
        
        Args:
            data: Agent返回的原始数据
            date: 分析日期
            
        Returns:
            EmotionReport: 标准化的情绪报告对象
        """
        try:
            # 提取情绪指标
            market_coefficient = data.get("market_coefficient", 0.0)
            ultra_short_emotion = data.get("ultra_short_emotion", 0.0)
            loss_effect = data.get("loss_effect", 0.0)
            
            # 提取周期节点
            cycle_node = data.get("cycle_node", "")
            
            # 提取赚钱效应评分
            profit_score = data.get("profit_score", 0)
            
            # 提取操作建议
            operation_advice = data.get("operation_advice", {})
            position_suggestion = operation_advice.get("position", "")
            
            # 构建EmotionReport对象
            report = EmotionReport(
                date=date,
                market_coefficient=market_coefficient,
                ultra_short_emotion=ultra_short_emotion,
                loss_effect=loss_effect,
                cycle_node=cycle_node,
                profit_score=profit_score,
                position_suggestion=position_suggestion,
                raw_data=data
            )
            
            return report
            
        except Exception as e:
            logger.error(f"解析情绪分析报告失败: {e}")
            raise ValueError(f"解析情绪分析报告失败: {e}")
    
    def _parse_theme_report(self, data: Dict[str, Any], date: str) -> ThemeReport:
        """解析题材分析报告数据
        
        Args:
            data: Agent返回的原始数据
            date: 分析日期
            
        Returns:
            ThemeReport: 标准化的题材报告对象
        """
        try:
            # 提取热门题材
            hot_themes = data.get("hot_themes", [])
            
            # 提取题材详情
            theme_details = []
            for theme in hot_themes:
                detail = {
                    "name": theme.get("name", ""),
                    "strength": theme.get("strength", 0),
                    "cycle_stage": theme.get("cycle_stage", ""),
                    "capacity": theme.get("capacity", ""),
                    "leading_stocks": theme.get("leading_stocks", [])
                }
                theme_details.append(detail)
            
            # 提取市场概况
            market_summary = data.get("market_summary", "")
            
            # 构建ThemeReport对象
            report = ThemeReport(
                date=date,
                hot_themes=theme_details,
                market_summary=market_summary,
                raw_data=data
            )
            
            return report
            
        except Exception as e:
            logger.error(f"解析题材分析报告失败: {e}")
            raise ValueError(f"解析题材分析报告失败: {e}")
