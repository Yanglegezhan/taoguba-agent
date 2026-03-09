"""
Scout Agent (Agent 0): 项目发现与接单智能体
负责监控平台、筛选项目、生成竞标文案
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from .base_agent import BaseAgent, AgentTool

logger = logging.getLogger(__name__)


class ScoutAgent(BaseAgent):
    """
     Scout Agent - 项目发现与接单智能体
    
    核心功能:
    - 监控多个接单平台
    - 筛选符合条件的新项目
    - 评估项目价值和接单可行性
    - 生成竞标文案
    """

    def __init__(self, config: Dict[str, Any], llm_provider=None, browser=None):
        # 设置系统提示
        system_prompt = """你是 Auto-Freelance Swarm 的 Scout Agent (项目发现专家)。

你的主要职责是:
1. 监控多个自由职业平台，发现潜在项目机会
2. 根据预设条件筛选高质量项目
3. 评估项目的接单价值（预算、技能匹配度、竞争程度等）
4. 生成专业的竞标文案

重要原则:
- 只推荐符合用户技能栈的项目
- 对预算过低或需求模糊的项目保持谨慎
- 确保推荐的項目都是合法的
- 保护用户账号安全，不过度频繁操作

输出格式:
你应当输出结构化的项目信息，包括:
- 项目基本信息（标题、描述、预算）
- 评估分数（0-100）
- 推荐理由
- 竞标建议
"""
        
        config["system_prompt"] = system_prompt
        super().__init__("ScoutAgent", config, llm_provider)
        
        self.browser = browser
        self.platforms = config.get("platforms", [])
        
        # 项目缓存（避免重复推荐）
        self.seen_projects: Dict[str, datetime] = {}

    async def execute(self, input_data: Any, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行项目发现任务
        
        Args:
            input_data: 输入数据（可以是平台名称或搜索关键词）
            context: 上下文信息
            
        Returns:
            发现的项目列表和推荐
        """
        logger.info("开始执行项目发现任务")
        
        # 决定执行模式
        if isinstance(input_data, str) and input_data.startswith("http"):
            # 抓取特定URL
            projects = await self.fetch_project_from_url(input_data)
        else:
            # 扫描配置的平台
            projects = await self.scan_platforms(input_data or "all")
        
        # 评估每个项目
        evaluated_projects = []
        for project in projects:
            score = await self.evaluate_project(project)
            project["score"] = score
            project["evaluated_at"] = datetime.now().isoformat()
            
            if score >= self.config.get("score_threshold", 70):
                evaluated_projects.append(project)
        
        # 按分数排序
        evaluated_projects.sort(key=lambda x: x["score"], reverse=True)
        
        # 生成推荐报告
        report = await self.generate_report(evaluated_projects)
        
        logger.info(f"项目发现完成，找到 {len(evaluated_projects)} 个符合条件的新项目")
        
        return {
            "status": "success",
            "projects_found": len(projects),
            "projects_matched": len(evaluated_projects),
            "projects": evaluated_projects[:10],  # 返回前10个
            "report": report
        }

    async def scan_platforms(self, platform_filter: str = "all") -> List[Dict[str, Any]]:
        """
        扫描配置的平台
        
        Args:
            platform_filter: 平台过滤器
            
        Returns:
            项目列表
        """
        projects = []
        
        # 获取需要扫描的平台
        platforms_to_scan = []
        for platform in self.platforms:
            if platform_filter == "all" or platform.get("name") == platform_filter:
                if platform.get("enabled", False):
                    platforms_to_scan.append(platform)
        
        logger.info(f"将扫描 {len(platforms_to_scan)} 个平台")
        
        # 并行扫描（带速率限制）
        semaphore = asyncio.Semaphore(2)  # 最多同时扫描2个平台
        
        async def scan_with_limit(platform):
            async with semaphore:
                try:
                    return await self.scan_platform(platform)
                except Exception as e:
                    logger.error(f"扫描平台 {platform.get('name')} 失败: {e}")
                    return []
        
        results = await asyncio.gather(
            *[scan_with_limit(p) for p in platforms_to_scan],
            return_exceptions=True
        )
        
        for result in results:
            if isinstance(result, list):
                projects.extend(result)
        
        return projects

    async def scan_platform(self, platform: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        扫描单个平台
        
        Args:
            platform: 平台配置
            
        Returns:
            项目列表
        """
        logger.info(f"开始扫描平台: {platform.get('name')}")
        
        # 添加随机延迟，模拟人工操作
        delay = platform.get("anti_crawl", {}).get("random_delay", True)
        if delay:
            min_delay = platform.get("anti_crawl", {}).get("min_delay", 3)
            max_delay = platform.get("anti_crawl", {}).get("max_delay", 8)
            await asyncio.sleep(plateau(self.PseudoRandom.uniform(min_delay, max_delay)))
        
        # 如果没有浏览器，返回模拟数据（实际使用时替换为真实抓取）
        if not self.browser:
            # 返回示例数据用于测试
            return self._generate_sample_projects(platform)
        
        # 实际抓取逻辑
        try:
            page = await self.browser.new_page()
            await page.goto(platform.get("project_list_url", ""), wait_until="networkidle")
            
            # 等待页面加载
            await asyncio.sleep(2)
            
            # 提取项目列表
            soup = BeautifulSoup(await page.content(), "html.parser")
            project_elements = soup.select(platform.get("selectors", {}).get("project_list", ".project-item"))
            
            projects = []
            for element in project_elements[:20]:  # 最多取20个
                project = self._extract_project_info(element, platform)
                if project and not self._is_duplicate(project):
                    projects.append(project)
            
            await page.close()
            return projects
            
        except Exception as e:
            logger.error(f"抓取平台 {platform.get('name')} 时出错: {e}")
            return []

    def _extract_project_info(self, element, platform: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从页面元素提取项目信息"""
        selectors = platform.get("selectors", {})
        
        try:
            title_elem = element.select_one(selectors.get("project_title", "h3"))
            budget_elem = element.select_one(selectors.get("project_budget", ".price"))
            desc_elem = element.select_one(selectors.get("project_description", ".desc"))
            
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            budget_text = budget_elem.get_text(strip=True) if budget_elem else "未标注"
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            return {
                "id": f"{platform.get('name')}_{hash(title) % 100000}",
                "platform": platform.get("name"),
                "title": title,
                "budget": budget_text,
                "description": description[:500],  # 截断过长的描述
                "url": platform.get("project_url_pattern", "").format(
                    id=hash(title) % 100000
                ),
                "scraped_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"解析项目元素失败: {e}")
            return None

    def _is_duplicate(self, project: Dict[str, Any]) -> bool:
        """检查是否重复项目"""
        project_id = project.get("id", "")
        
        if project_id in self.seen_projects:
            # 检查是否在24小时内
            seen_time = self.seen_projects[project_id]
            if (datetime.now() - seen_time).total_seconds() < 86400:
                return True
        
        self.seen_projects[project_id] = datetime.now()
        return False

    async def fetch_project_from_url(self, url: str) -> List[Dict[str, Any]]:
        """从特定URL获取项目"""
        logger.info(f"从URL获取项目: {url}")
        # 实际实现...
        return []

    async def evaluate_project(self, project: Dict[str, Any]) -> float:
        """
        评估项目分数
        
        评估维度:
        - 预算匹配度 (25%)
        - 技能匹配度 (25%)
        - 项目清晰度 (20%)
        - 竞争程度 (15%)
        - 时间合理性 (15%)
        """
        
        # 构建评估提示
        prompt = f"""请评估以下自由职业项目的接单价值（0-100分）:

项目标题: {project.get('title', '')}
项目描述: {project.get('description', '')}
预算范围: {project.get('budget', '')}
平台: {project.get('platform', '')}

请从以下维度评分（只需给出总分）:
1. 预算是否合理
2. 是否符合Python/Web开发技能
3. 需求是否清晰明确
4. 竞争激烈程度
5. 时间要求是否合理

请直接给出总分（0-100），不需要详细解释。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            response = await self.call_llm(messages)
            # 提取数字分数
            import re
            match = re.search(r'(\d+)', response)
            if match:
                return min(100, max(0, int(match.group(1))))
        except Exception as e:
            logger.error(f"评估项目失败: {e}")
        
        return 50  # 默认分数

    async def generate_report(self, projects: List[Dict[str, Any]]) -> str:
        """生成项目发现报告"""
        
        if not projects:
            return "未发现符合条件的新项目"
        
        # 取前5个项目生成摘要
        top_projects = projects[:5]
        
        report = f"""## 项目发现报告

扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
发现项目: {len(projects)} 个

### 推荐项目

"""
        
        for i, project in enumerate(top_projects, 1):
            report += f"""**{i}. {project.get('title', '未命名')}**
   - 平台: {project.get('platform', '')}
   - 预算: {project.get('budget', '未标注')}
   - 评分: {project.get('score', 0)}/100
   - 链接: {project.get('url', '')}

"""
        
        return report

    async def generate_bid(
        self,
        project: Dict[str, Any],
        template: str = "standard"
    ) -> str:
        """生成竞标文案"""
        
        prompt = f"""请根据以下项目信息生成专业的竞标文案:

项目标题: {project.get('title', '')}
项目描述: {project.get('description', '')}
预算范围: {project.get('budget', '')}

请生成一段专业、简洁的竞标文案（{self.config.get('bid_length', 300)}字以内），
包含:
1. 对项目需求的理解
2. 你的技术优势
3. 合理的报价建议
4. 预计完成时间

注意: 语气要专业、自信，避免空洞的套话。"""
        
        messages = self.get_messages()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            response = await self.call_llm(messages)
            return response
        except Exception as e:
            logger.error(f"生成竞标文案失败: {e}")
            return "Hi, I'm interested in this project. Please check my profile for details."

    def _generate_sample_projects(self, platform: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成示例项目数据（用于测试）"""
        
        sample_projects = [
            {
                "id": f"{platform.get('name')}_001",
                "platform": platform.get("name"),
                "title": "Python数据采集脚本开发",
                "description": "需要开发一个Python爬虫程序，能够自动采集指定网站的数据，支持定时任务和数据存储。",
                "budget": "1000-3000元",
                "url": "https://example.com/project/001"
            },
            {
                "id": f"{platform.get('name')}_002",
                "platform": platform.get("name"),
                "title": "企业官网开发",
                "description": "使用Django/Flask开发一个企业官方网站，包含产品展示、新闻动态、联系我们等模块。",
                "budget": "5000-10000元",
                "url": "https://example.com/project/002"
            },
            {
                "id": f"{platform.get('name')}_003",
                "platform": platform.get("name"),
                "title": "微信小程序开发",
                "description": "开发一个简单的微信小程序，用于企业内部员工考勤管理。",
                "budget": "8000-15000元",
                "url": "https://example.com/project/003"
            }
        ]
        
        return sample_projects


class Plateau:
    """简单的伪随机数生成器（用于模拟延迟）"""
    
    def __init__(self):
        import random
        self._random = random.Random()
    
    def uniform(self, a: float, b: float) -> float:
        return self._random.uniform(a, b)


# 创建全局伪随机实例
plateau = Plateau()
