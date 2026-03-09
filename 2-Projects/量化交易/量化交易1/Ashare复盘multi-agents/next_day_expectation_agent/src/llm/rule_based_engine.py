"""
规则引擎模块

提供基于规则的分析功能，作为LLM不可用时的降级方案。
"""

from typing import Any, Dict, List, Optional
import json
from ..common.logger import get_logger

logger = get_logger(__name__)


class RuleBasedEngine:
    """
    规则引擎
    
    当LLM不可用时，使用基于规则的方法进行基础分析。
    """
    
    def __init__(self):
        """初始化规则引擎"""
        logger.info("Initialized RuleBasedEngine")
        
        # 定义各类任务的规则
        self.rules = {
            "market_sentiment": self._analyze_market_sentiment_rules,
            "theme_detection": self._analyze_theme_detection_rules,
            "baseline_expectation": self._analyze_baseline_expectation_rules,
            "expectation_score": self._analyze_expectation_score_rules,
            "decision_navigation": self._analyze_decision_navigation_rules,
            "general": self._analyze_general_rules
        }
    
    def analyze(
        self,
        prompt: str,
        task_type: str = "general",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        使用规则进行分析
        
        Args:
            prompt: 输入提示词
            task_type: 任务类型
            context: 上下文数据（可选）
            
        Returns:
            分析结果文本
        """
        logger.info(f"Analyzing with rule-based engine (task_type={task_type})")
        
        # 获取对应的规则函数
        rule_func = self.rules.get(task_type, self._analyze_general_rules)
        
        try:
            result = rule_func(prompt, context)
            logger.info("Rule-based analysis completed")
            return result
        except Exception as e:
            logger.error(f"Rule-based analysis failed: {e}")
            return self._generate_fallback_response(task_type)
    
    def _analyze_market_sentiment_rules(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        市场情绪分析规则
        
        基于涨停家数、跌停家数、成交额等指标判断市场情绪。
        """
        if not context:
            return "无法进行市场情绪分析：缺少上下文数据"
        
        # 提取关键指标
        limit_up_count = context.get("limit_up_count", 0)
        limit_down_count = context.get("limit_down_count", 0)
        index_change = context.get("index_change", 0.0)
        volume_ratio = context.get("volume_ratio", 1.0)
        
        # 规则判断
        sentiment = "中性"
        confidence = 0.5
        
        # 强势判断
        if limit_up_count > 50 and index_change > 1.0 and volume_ratio > 1.2:
            sentiment = "强势"
            confidence = 0.8
        elif limit_up_count > 30 and index_change > 0.5:
            sentiment = "偏强"
            confidence = 0.7
        # 弱势判断
        elif limit_down_count > 30 and index_change < -1.0:
            sentiment = "弱势"
            confidence = 0.8
        elif limit_down_count > 20 or index_change < -0.5:
            sentiment = "偏弱"
            confidence = 0.7
        
        result = {
            "sentiment": sentiment,
            "confidence": confidence,
            "analysis": f"涨停{limit_up_count}家，跌停{limit_down_count}家，"
                       f"指数涨跌{index_change:.2f}%，量比{volume_ratio:.2f}",
            "source": "rule_based"
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    def _analyze_theme_detection_rules(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        题材检测规则
        
        基于关键词匹配和新闻标题识别新题材。
        """
        if not context:
            return "无法进行题材检测：缺少上下文数据"
        
        news_items = context.get("news", [])
        
        # 定义题材关键词
        theme_keywords = {
            "AI": ["人工智能", "AI", "大模型", "ChatGPT", "算力"],
            "新能源": ["新能源", "光伏", "锂电", "储能", "氢能"],
            "半导体": ["芯片", "半导体", "集成电路", "晶圆"],
            "数字经济": ["数字经济", "数据要素", "算力", "云计算"],
            "军工": ["军工", "国防", "航空", "航天"],
            "医药": ["医药", "生物医药", "创新药", "医疗器械"],
            "消费": ["消费", "白酒", "食品", "零售"],
            "地产": ["地产", "房地产", "建筑"],
            "金融": ["银行", "保险", "券商", "金融"]
        }
        
        detected_themes = []
        
        # 遍历新闻，匹配关键词
        for news in news_items:
            title = news.get("title", "")
            content = news.get("content", "")
            text = title + " " + content
            
            for theme, keywords in theme_keywords.items():
                if any(keyword in text for keyword in keywords):
                    detected_themes.append({
                        "theme": theme,
                        "source": title,
                        "confidence": 0.6
                    })
                    break
        
        result = {
            "themes": detected_themes,
            "count": len(detected_themes),
            "source": "rule_based"
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    def _analyze_baseline_expectation_rules(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        基准预期计算规则
        
        基于连板高度、题材状态、市场环境计算基准预期。
        """
        if not context:
            return "无法计算基准预期：缺少上下文数据"
        
        stock_code = context.get("stock_code", "")
        board_height = context.get("board_height", 0)
        yesterday_change = context.get("yesterday_change", 0.0)
        theme_status = context.get("theme_status", "中性")  # 主升/退潮/中性
        market_sentiment = context.get("market_sentiment", "中性")
        
        # 基础预期（根据连板高度）
        if board_height >= 5:
            base_min, base_max = 5.0, 8.0
        elif board_height >= 3:
            base_min, base_max = 3.0, 6.0
        elif board_height >= 1:
            base_min, base_max = 1.0, 4.0
        elif yesterday_change > 5:
            base_min, base_max = 0.0, 3.0
        else:
            base_min, base_max = -2.0, 2.0
        
        # 题材调整
        if theme_status == "主升":
            base_min += 2.0
            base_max += 2.0
        elif theme_status == "退潮":
            base_min -= 3.0
            base_max -= 2.0
        
        # 市场环境调整
        if market_sentiment == "强势":
            base_min += 1.0
            base_max += 1.0
        elif market_sentiment == "弱势":
            base_min -= 2.0
            base_max -= 1.0
        
        result = {
            "stock_code": stock_code,
            "expected_open_min": round(base_min, 2),
            "expected_open_max": round(base_max, 2),
            "logic": f"连板{board_height}板+题材{theme_status}+市场{market_sentiment}",
            "confidence": 0.6,
            "source": "rule_based"
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    def _analyze_expectation_score_rules(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        超预期分值计算规则
        
        基于量能、价格、独立性三个维度计算分值。
        """
        if not context:
            return "无法计算超预期分值：缺少上下文数据"
        
        # 量能分值
        auction_amount = context.get("auction_amount", 0.0)
        yesterday_amount = context.get("yesterday_amount", 1.0)
        amount_ratio = auction_amount / yesterday_amount if yesterday_amount > 0 else 0
        
        if amount_ratio >= 0.1:
            volume_score = 100
        elif amount_ratio >= 0.05:
            volume_score = 80
        elif amount_ratio >= 0.03:
            volume_score = 60
        elif amount_ratio >= 0.02:
            volume_score = 40
        else:
            volume_score = 20
        
        # 价格分值
        actual_open = context.get("actual_open", 0.0)
        expected_min = context.get("expected_min", 0.0)
        expected_max = context.get("expected_max", 0.0)
        
        if actual_open > expected_max:
            price_score = 80 + min(20, (actual_open - expected_max) * 5)
        elif actual_open >= expected_min:
            price_score = 60
        else:
            price_score = max(0, 60 - (expected_min - actual_open) * 10)
        
        # 独立性分值
        stock_change = context.get("stock_change", 0.0)
        index_change = context.get("index_change", 0.0)
        excess_return = stock_change - index_change
        
        if excess_return >= 5:
            independence_score = 100
        elif excess_return >= 3:
            independence_score = 80
        elif excess_return >= 1:
            independence_score = 60
        elif excess_return >= 0:
            independence_score = 40
        else:
            independence_score = 20
        
        # 综合分值（默认权重：量能40%、价格40%、独立性20%）
        total_score = volume_score * 0.4 + price_score * 0.4 + independence_score * 0.2
        
        # 评级
        if total_score >= 80:
            rating = "优秀"
            recommendation = "打板"
        elif total_score >= 60:
            rating = "良好"
            recommendation = "低吸"
        elif total_score >= 40:
            rating = "一般"
            recommendation = "观望"
        else:
            rating = "较差"
            recommendation = "撤退"
        
        result = {
            "volume_score": round(volume_score, 2),
            "price_score": round(price_score, 2),
            "independence_score": round(independence_score, 2),
            "total_score": round(total_score, 2),
            "rating": rating,
            "recommendation": recommendation,
            "confidence": 0.6,
            "source": "rule_based"
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    def _analyze_decision_navigation_rules(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        决策导航规则
        
        基于核心股表现和附加池情况生成操作建议。
        """
        if not context:
            return "无法生成决策导航：缺少上下文数据"
        
        core_stocks_status = context.get("core_stocks_status", "中性")  # 超预期/符合/不及
        additional_pool_count = context.get("additional_pool_count", 0)
        market_sentiment = context.get("market_sentiment", "中性")
        
        # 场景判定
        if core_stocks_status == "超预期":
            scenario = "整体超预期"
            strategy = "扫板附加池中最先涨停的标的，或低吸基因池形态最好的回踩"
            risk = "顶背离风险，注意及时止盈"
        elif core_stocks_status == "不及":
            scenario = "分歧兑现"
            strategy = "空仓观望，即便附加池有个股乱跳也不要动"
            risk = "情绪退潮，高风险"
        elif additional_pool_count > 3:
            scenario = "高低切"
            strategy = "放弃高位连板，手动狙击附加池中满足大单点火的标的"
            risk = "题材切换风险，注意新题材可持续性"
        else:
            scenario = "震荡整理"
            strategy = "观望为主，等待明确信号"
            risk = "方向不明，避免盲目操作"
        
        result = {
            "scenario": scenario,
            "strategy": strategy,
            "risk": risk,
            "confidence": 0.5,
            "source": "rule_based"
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    def _analyze_general_rules(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        通用分析规则
        
        提供基础的文本分析。
        """
        result = {
            "analysis": "规则引擎提供的基础分析",
            "note": "LLM不可用，使用规则引擎降级方案",
            "confidence": 0.4,
            "source": "rule_based"
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    def _generate_fallback_response(self, task_type: str) -> str:
        """
        生成降级响应
        
        当规则引擎也失败时，返回最基础的响应。
        """
        return json.dumps({
            "error": "分析失败",
            "task_type": task_type,
            "message": "LLM和规则引擎均不可用",
            "source": "fallback"
        }, ensure_ascii=False, indent=2)
    
    def add_rule(
        self,
        task_type: str,
        rule_func: callable
    ) -> None:
        """
        添加自定义规则
        
        Args:
            task_type: 任务类型
            rule_func: 规则函数，签名为 func(prompt, context) -> str
        """
        self.rules[task_type] = rule_func
        logger.info(f"Added custom rule for task_type={task_type}")
    
    def get_supported_tasks(self) -> List[str]:
        """
        获取支持的任务类型列表
        
        Returns:
            任务类型列表
        """
        return list(self.rules.keys())
