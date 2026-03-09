"""
外包平台项目搜索器
自动搜索合适的外包项目
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FreelanceProject:
    """外包项目"""
    title: str
    description: str
    budget_min: float
    budget_max: float
    platform: str
    url: str
    posted_date: str
    tags: List[str]
    skills_required: List[str]

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "platform": self.platform,
            "url": self.url,
            "posted_date": self.posted_date,
            "tags": self.tags,
            "skills_required": self.skills_required
        }

    def is_suitable(self, my_skills: List[str]) -> bool:
        """检查项目是否适合"""
        # 检查预算（不接受低于50元的项目）
        if self.budget_max < 50:
            return False

        # 检查技能匹配
        my_skills_lower = [s.lower() for s in my_skills]
        for skill in self.skills_required:
            if any(my_skill in skill.lower() for my_skill in my_skills_lower):
                return True

        return False


class PlatformSearcher:
    """平台搜索器基类"""

    def __init__(self, headers: Optional[dict] = None):
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def search(self, keywords: List[str], min_budget: float = 50) -> List[FreelanceProject]:
        """搜索项目"""
        raise NotImplementedError


class ZhuBaJieSearcher(PlatformSearcher):
    """猪八戒网搜索器"""

    BASE_URL = "https://task.zbj.com"

    def search(self, keywords: List[str], min_budget: float = 50) -> List[FreelanceProject]:
        """
        搜索猪八戒项目

        注意：实际使用需要处理登录、反爬等
        这里提供框架代码
        """
        projects = []

        for keyword in keywords:
            logger.info(f"搜索猪八戒: {keyword}")

            # 构建搜索URL（示例）
            url = f"{self.BASE_URL}/s/?q={keyword}"

            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code != 200:
                    logger.warning(f"请求失败: {response.status_code}")
                    continue

                # 解析页面（实际需要分析猪八戒DOM结构）
                soup = BeautifulSoup(response.text, 'html.parser')

                # TODO: 实际解析逻辑
                # items = soup.select('.task-item')
                # for item in items:
                #     project = self._parse_item(item, min_budget)
                #     if project:
                #         projects.append(project)

            except Exception as e:
                logger.error(f"搜索出错: {e}")

        logger.info(f"猪八戒找到 {len(projects)} 个项目")
        return projects


class MaShiSearcher(PlatformSearcher):
    """码市搜索器"""

    BASE_URL = "https://codemart.com"

    def search(self, keywords: List[str], min_budget: float = 50) -> List[FreelanceProject]:
        """搜索码市项目"""
        projects = []

        for keyword in keywords:
            logger.info(f"搜索码市: {keyword}")

            # 构建搜索URL
            url = f"{self.BASE_URL}/projects?keyword={keyword}"

            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code != 200:
                    continue

                # TODO: 解析码市页面

            except Exception as e:
                logger.error(f"搜索出错: {e}")

        logger.info(f"码市找到 {len(projects)} 个项目")
        return projects


class UpworkSearcher(PlatformSearcher):
    """Upwork搜索器"""

    BASE_URL = "https://www.upwork.com"

    def search(self, keywords: List[str], min_budget: float = 50) -> List[FreelanceProject]:
        """搜索Upwork项目"""
        projects = []

        for keyword in keywords:
            logger.info(f"搜索Upwork: {keyword}")

            # Upwork使用API需要access token
            # 这里提供API调用框架
            url = f"{self.BASE_URL}/ab/jobs/search?q={keyword}"

            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code != 200:
                    continue

                # TODO: 解析Upwork页面

            except Exception as e:
                logger.error(f"搜索出错: {e}")

        logger.info(f"Upwork找到 {len(projects)} 个项目")
        return projects


# 我的技能清单
MY_SKILLS = [
    "Python",
    "爬虫",
    "数据采集",
    "数据处理",
    "自动化",
    "数据分析",
    "量化交易",
    "股票",
    "加密货币",
    "Django",
    "Flask",
    "PyTorch",
    "数据可视化"
]

# 搜索关键词
SEARCH_KEYWORDS = [
    "Python爬虫",
    "数据爬取",
    "网站爬虫",
    "数据采集",
    "量化交易",
    "股票数据",
    "加密货币",
    "自动化脚本",
    "数据处理",
    "Python开发",
    "数据分析",
    "Django开发",
    "Flask开发"
]


def search_all_platforms(min_budget: float = 50) -> List[FreelanceProject]:
    """搜索所有平台"""
    all_projects = []

    searchers = [
        ZhuBaJieSearcher(),
        MaShiSearcher(),
        UpworkSearcher()
    ]

    for searcher in searchers:
        try:
            projects = searcher.search(SEARCH_KEYWORDS, min_budget)
            all_projects.extend(projects)
        except Exception as e:
            logger.error(f"{searcher.__class__.__name__} 搜索失败: {e}")

    # 过滤适合的项目
    suitable_projects = [p for p in all_projects if p.is_suitable(MY_SKILLS)]

    # 按预算排序
    suitable_projects.sort(key=lambda p: p.budget_max, reverse=True)

    return suitable_projects


def save_results(projects: List[FreelanceProject], filepath: str = "projects.json"):
    """保存搜索结果"""
    data = [p.to_dict() for p in projects]
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存 {len(data)} 个项目到 {filepath}")


def generate_project_report(projects: List[FreelanceProject]) -> str:
    """生成项目报告"""
    if not projects:
        return "未找到合适的项目"

    report = []
    report.append("="*80)
    report.append("外包项目搜索报告".center(80))
    report.append("="*80)
    report.append(f"\n共找到 {len(projects)} 个适合的项目\n")
    report.append("-"*80)

    for i, project in enumerate(projects, 1):
        report.append(f"\n【项目 {i}】")
        report.append(f"标题: {project.title}")
        report.append(f"平台: {project.platform}")
        report.append(f"预算: ¥{project.budget_min} - ¥{project.budget_max}")
        report.append(f"链接: {project.url}")
        report.append(f"发布时间: {project.posted_date}")
        report.append(f"所需技能: {', '.join(project.skills_required)}")
        report.append(f"描述: {project.description[:100]}...")

    report.append("\n" + "="*80)
    report.append("总计".center(80))
    report.append("="*80)

    total_value = sum(p.budget_max for p in projects)
    report.append(f"总潜在价值: ¥{total_value}")
    report.append(f"平均预算: ¥{total_value / len(projects):.2f}")

    return "\n".join(report)


def main():
    """主函数"""
    print("开始搜索外包项目...")

    projects = search_all_platforms(min_budget=50)

    report = generate_project_report(projects)
    print(report)

    # 保存结果
    save_results(projects, "money_mission/freelance/projects.json")

    # 保存报告
    with open("money_mission/freelance/report.txt", 'w', encoding='utf-8') as f:
        f.write(report)


if __name__ == "__main__":
    main()
