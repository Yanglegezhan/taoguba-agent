"""
报告生成器测试

测试ReportGenerator类的功能，包括：
- 初始化
- 调用各个复盘agent
- 解析报告数据
- 生成标准化报告对象
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json

from src.stage1.report_generator import ReportGenerator
from src.common.models import MarketReport, EmotionReport, ThemeReport


class TestReportGenerator:
    """报告生成器测试类"""
    
    def test_init(self):
        """测试初始化"""
        generator = ReportGenerator()
        
        assert generator is not None
        assert generator.project_root is not None
        assert generator.index_agent_path.exists()
        assert generator.sentiment_agent_path.exists()
        assert generator.theme_agent_path.exists()
    
    def test_parse_market_report(self):
        """测试解析大盘分析报告"""
        generator = ReportGenerator()
        
        # 模拟agent返回的数据
        mock_data = {
            "current_price": 3018.56,
            "change_pct": 0.62,
            "support_levels": [
                {"price": 3000.0, "strength": "强"},
                {"price": 2990.0, "strength": "中"}
            ],
            "resistance_levels": [
                {"price": 3050.0, "strength": "强"},
                {"price": 3030.0, "strength": "中"}
            ],
            "short_term": {
                "scenario": "震荡修复",
                "target": [3030, 3050]
            },
            "long_term": {
                "trend": "震荡趋势"
            }
        }
        
        # 解析报告
        report = generator._parse_market_report(mock_data, "2025-02-12")
        
        # 验证结果
        assert isinstance(report, MarketReport)
        assert report.date == "2025-02-12"
        assert report.current_price == 3018.56
        assert report.change_pct == 0.62
        assert len(report.support_levels) == 2
        assert len(report.resistance_levels) == 2
        assert report.short_term_scenario == "震荡修复"
        assert report.short_term_target == [3030, 3050]
        assert report.long_term_trend == "震荡趋势"
    
    def test_parse_emotion_report(self):
        """测试解析情绪分析报告"""
        generator = ReportGenerator()
        
        # 模拟agent返回的数据
        mock_data = {
            "market_coefficient": 150.0,
            "ultra_short_emotion": 45.5,
            "loss_effect": 28.3,
            "cycle_node": "修复后分歧",
            "profit_score": 65,
            "operation_advice": {
                "position": "半仓"
            }
        }
        
        # 解析报告
        report = generator._parse_emotion_report(mock_data, "2025-02-12")
        
        # 验证结果
        assert isinstance(report, EmotionReport)
        assert report.date == "2025-02-12"
        assert report.market_coefficient == 150.0
        assert report.ultra_short_emotion == 45.5
        assert report.loss_effect == 28.3
        assert report.cycle_node == "修复后分歧"
        assert report.profit_score == 65
        assert report.position_suggestion == "半仓"
    
    def test_parse_theme_report(self):
        """测试解析题材分析报告"""
        generator = ReportGenerator()
        
        # 模拟agent返回的数据
        mock_data = {
            "hot_themes": [
                {
                    "name": "AI",
                    "strength": 85,
                    "cycle_stage": "主升期",
                    "capacity": "大容量",
                    "leading_stocks": ["002810", "300XXX"]
                },
                {
                    "name": "数字经济",
                    "strength": 72,
                    "cycle_stage": "启动期",
                    "capacity": "中容量",
                    "leading_stocks": ["600XXX"]
                }
            ],
            "market_summary": "市场整体强势，AI题材持续活跃"
        }
        
        # 解析报告
        report = generator._parse_theme_report(mock_data, "2025-02-12")
        
        # 验证结果
        assert isinstance(report, ThemeReport)
        assert report.date == "2025-02-12"
        assert len(report.hot_themes) == 2
        assert report.hot_themes[0]["name"] == "AI"
        assert report.hot_themes[0]["strength"] == 85
        assert report.hot_themes[1]["name"] == "数字经济"
        assert report.market_summary == "市场整体强势，AI题材持续活跃"
    
    @patch('subprocess.run')
    def test_call_index_agent_success(self, mock_run):
        """测试成功调用大盘分析Agent"""
        generator = ReportGenerator()
        
        # 模拟subprocess.run的返回值
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "current_price": 3018.56,
            "change_pct": 0.62
        })
        mock_run.return_value = mock_result
        
        # 调用agent
        result = generator._call_index_agent("2025-02-12")
        
        # 验证结果
        assert result["current_price"] == 3018.56
        assert result["change_pct"] == 0.62
        
        # 验证subprocess.run被正确调用
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "--date" in call_args[0][0]
        assert "2025-02-12" in call_args[0][0]
    
    @patch('subprocess.run')
    def test_call_index_agent_failure(self, mock_run):
        """测试大盘分析Agent调用失败"""
        generator = ReportGenerator()
        
        # 模拟subprocess.run返回错误
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: API key not found"
        mock_run.return_value = mock_result
        
        # 调用agent应该抛出异常
        with pytest.raises(RuntimeError, match="大盘分析Agent执行失败"):
            generator._call_index_agent("2025-02-12")
    
    def test_report_to_dict_and_from_dict(self):
        """测试报告的序列化和反序列化"""
        # 创建MarketReport
        market_report = MarketReport(
            date="2025-02-12",
            current_price=3018.56,
            change_pct=0.62,
            support_levels=[{"price": 3000.0}],
            resistance_levels=[{"price": 3050.0}],
            short_term_scenario="震荡",
            short_term_target=[3030, 3050],
            long_term_trend="震荡趋势"
        )
        
        # 转换为字典
        data = market_report.to_dict()
        assert isinstance(data, dict)
        assert data["date"] == "2025-02-12"
        assert data["current_price"] == 3018.56
        
        # 从字典恢复
        restored = MarketReport.from_dict(data)
        assert restored.date == market_report.date
        assert restored.current_price == market_report.current_price
        assert restored.change_pct == market_report.change_pct


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
