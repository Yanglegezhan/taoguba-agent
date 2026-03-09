# -*- coding: utf-8 -*-
"""LLM分析器"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..models.data_models import (
    DarkLine,
    StatisticalAnalysis,
    NamingAnalysis,
    LLMInterpretation
)


class LLMAnalyzer:
    """LLM暗线解读分析器"""

    def __init__(self, config):
        """初始化分析器"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.provider = config.provider
        self.api_key = config.api_key
        self.model_name = config.model_name
        self.temperature = config.temperature

    def analyze_dark_lines(
        self,
        dark_lines: List[DarkLine],
        stat_analysis: StatisticalAnalysis,
        naming_analysis: NamingAnalysis
    ) -> Optional[LLMInterpretation]:
        """使用LLM分析暗线"""
        self.logger.info(f"Running LLM analysis on {len(dark_lines)} dark lines")

        # 加载提示词模板
        prompt_template = self._load_prompt_template()
        if not prompt_template:
            self.logger.warning("Prompt template not found, skipping LLM analysis")
            return None

        # 构建上下文
        context = self._build_context(dark_lines, stat_analysis, naming_analysis)

        # 构建完整提示词
        prompt = prompt_template.format(**context)

        # 调用LLM
        try:
            response_text = self._call_llm(prompt)
            self.logger.info(f"LLM response received: {len(response_text)} chars")
            
            # 保存完整响应到文件以便调试
            import os
            debug_dir = Path(__file__).parent.parent.parent / "logs"
            debug_dir.mkdir(exist_ok=True)
            debug_file = debug_dir / "llm_response_debug.txt"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("LLM完整响应\n")
                f.write("=" * 60 + "\n")
                f.write(response_text)
                f.write("\n" + "=" * 60 + "\n")
            self.logger.info(f"LLM响应已保存到: {debug_file}")

            # 解析响应
            interpretation = self._parse_json_response(response_text)
            if interpretation:
                return interpretation
            else:
                self.logger.warning("LLM响应解析失败，返回None")
                self.logger.warning(f"响应前200字符: {response_text[:200]}")
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

        return None

    def _load_prompt_template(self) -> Optional[str]:
        """加载提示词模板"""
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "dark_line_analysis.md"

        if not prompt_path.exists():
            self.logger.warning(f"Prompt template not found: {prompt_path}")
            return None

        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to load prompt template: {e}")
            return None

    def _build_context(
        self,
        dark_lines: List[DarkLine],
        stat_analysis: StatisticalAnalysis,
        naming_analysis: NamingAnalysis
    ) -> Dict[str, str]:
        """构建LLM分析上下文"""
        # 暗线列表
        dark_lines_text = "\n".join([
            f"{i+1}. {dl.title} (类型: {dl.dark_line_type}, 置信度: {dl.confidence:.2f})"
            f"\n   描述: {dl.description}"
            for i, dl in enumerate(dark_lines)
        ])

        # 统计摘要
        stat_summary = ""
        if hasattr(stat_analysis, 'limit_up_count'):
            stat_summary += f"涨停数量: {stat_analysis.limit_up_count}\n"
        if hasattr(stat_analysis, 'broken_net_ratio'):
            stat_summary += f"破净比例: {stat_analysis.broken_net_ratio:.1f}%\n"

        # 省份分析
        if hasattr(stat_analysis, 'province_analysis'):
            prov = stat_analysis.province_analysis
            if hasattr(prov, 'significant_items') and prov.significant_items:
                stat_summary += f"显著省份: {', '.join(prov.significant_items[:5])}\n"

        # 企业性质分析
        if hasattr(stat_analysis, 'ownership_analysis'):
            own = stat_analysis.ownership_analysis
            if hasattr(own, 'significant_items') and own.significant_items:
                stat_summary += f"显著企业性质: {', '.join(own.significant_items)}\n"

        # 命名特征
        naming_text = ""
        if naming_analysis.feature_summary:
            features = "\n".join([
                f"- {name}: {count}只 ({naming_analysis.feature_ratio.get(name, 0):.1f}%)"
                for name, count in list(naming_analysis.feature_summary.items())[:10]
            ])
            naming_text = f"命名特征统计:\n{features}"

        return {
            "dark_lines": dark_lines_text,
            "statistical_summary": stat_summary,
            "naming_features": naming_text
        }

    def _call_llm(self, prompt: str) -> str:
        """调用LLM API"""
        if self.provider == "zhipu":
            return self._call_zhipu(prompt)
        elif self.provider == "openai":
            return self._call_openai(prompt)
        elif self.provider == "deepseek":
            return self._call_deepseek(prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _call_zhipu(self, prompt: str) -> str:
        """调用智谱AI"""
        try:
            from zhipuai import ZhipuAI

            client = ZhipuAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的A股题材分析师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )
            return response.choices[0].message.content
        except ImportError:
            self.logger.error("zhipuai package not installed")
            raise
        except Exception as e:
            self.logger.error(f"ZhipuAI API error: {e}")
            raise

    def _call_openai(self, prompt: str) -> str:
        """调用OpenAI"""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的A股题材分析师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )
            return response.choices[0].message.content
        except ImportError:
            self.logger.error("openai package not installed")
            raise
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise

    def _call_deepseek(self, prompt: str) -> str:
        """调用DeepSeek"""
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的A股题材分析师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )
            return response.choices[0].message.content
        except ImportError:
            self.logger.error("openai package not installed")
            raise
        except Exception as e:
            self.logger.error(f"DeepSeek API error: {e}")
            raise

    def _parse_json_response(self, response_text: str) -> Optional[LLMInterpretation]:
        """解析LLM JSON响应"""
        try:
            # 尝试提取JSON部分
            response_text = response_text.strip()
            
            self.logger.debug(f"原始响应长度: {len(response_text)} 字符")

            # 查找JSON代码块
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end == -1:
                    end = len(response_text)
                json_str = response_text[start:end].strip()
                self.logger.debug("从 ```json 代码块中提取JSON")
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                if end == -1:
                    end = len(response_text)
                json_str = response_text[start:end].strip()
                self.logger.debug("从 ``` 代码块中提取JSON")
            else:
                # 尝试查找第一个 { 和最后一个 }
                start = response_text.find('{')
                end = response_text.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_str = response_text[start:end+1]
                    self.logger.debug("从文本中提取JSON对象")
                else:
                    json_str = response_text
                    self.logger.debug("使用完整响应文本")

            self.logger.debug(f"提取的JSON字符串前100字符: {json_str[:100]}")

            # 解析JSON
            data = json.loads(json_str)
            
            self.logger.info("✓ JSON解析成功")
            self.logger.debug(f"解析后的数据: {data}")

            return LLMInterpretation(
                interpretation_type=data.get("interpretation_type", "综合分析"),
                theme_nature=data.get("theme_nature", "未知"),
                sustainability=data.get("sustainability", "短期"),
                key_drivers=data.get("key_drivers", []),
                risks=data.get("risks", []),
                recommendations=data.get("recommendations", []),
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", "")
            )
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
            self.logger.error(f"尝试解析的内容: {json_str[:500] if 'json_str' in locals() else response_text[:500]}")
            return None
        except Exception as e:
            self.logger.error(f"解析LLM响应时出错: {e}")
            self.logger.error(f"响应内容: {response_text[:500]}")
            return None
