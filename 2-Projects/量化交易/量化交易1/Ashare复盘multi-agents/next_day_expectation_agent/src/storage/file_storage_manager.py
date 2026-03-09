"""
文件存储管理器

本模块实现文件存储管理功能，包括：
- 文件命名规范
- 目录结构管理
- 文件读写操作
- 历史数据管理

需求: 23.6, 23.7
"""

import os
import json
import shutil
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

from ..common.logger import get_logger
from ..common.models import (
    GenePool, BaselineExpectation, NavigationReport, 
    AdditionalPool, AuctionData, ExpectationScore
)

logger = get_logger(__name__)


class FileStorageManager:
    """
    文件存储管理器
    
    负责管理系统的文件存储，包括：
    - 目录结构管理
    - 文件命名规范
    - 数据文件的读写
    - 历史数据的归档
    """
    
    # 文件命名模板
    FILE_TEMPLATES = {
        'gene_pool': 'gene_pool_{date}.json',
        'market_report': 'market_report_{date}.json',
        'emotion_report': 'emotion_report_{date}.json',
        'theme_report': 'theme_report_{date}.json',
        'overnight_variables': 'overnight_variables_{date}.json',
        'baseline_expectation': 'baseline_expectation_{date}.json',
        'new_themes': 'new_themes_{date}.json',
        'auction_monitoring': 'auction_monitoring_{date}.json',
        'additional_pool': 'additional_pool_{date}.json',
        'decision_navigation': 'decision_navigation_{date}.json',
        'daily_report': 'daily_report_{date}.html'
    }
    
    def __init__(self, base_dir: str = 'data'):
        """
        初始化文件存储管理器
        
        Args:
            base_dir: 基础数据目录，默认为'data'
        """
        self.base_dir = Path(base_dir)
        self._ensure_directory_structure()
        logger.info(f"FileStorageManager initialized with base_dir: {self.base_dir}")
    
    def _ensure_directory_structure(self) -> None:
        """
        确保目录结构存在
        
        创建以下目录结构：
        data/
        ├── config/
        ├── stage1_output/
        ├── stage2_output/
        ├── stage3_output/
        ├── historical/
        └── logs/
        """
        directories = [
            self.base_dir / 'config',
            self.base_dir / 'stage1_output',
            self.base_dir / 'stage2_output',
            self.base_dir / 'stage3_output',
            self.base_dir / 'historical',
            self.base_dir / 'logs'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    def get_file_path(self, file_type: str, date: str, stage: Optional[str] = None) -> Path:
        """
        根据文件类型和日期获取文件路径
        
        Args:
            file_type: 文件类型（如'gene_pool', 'baseline_expectation'等）
            date: 日期字符串（格式：YYYYMMDD）
            stage: 阶段标识（'stage1', 'stage2', 'stage3'），可选
        
        Returns:
            文件完整路径
        
        Raises:
            ValueError: 如果文件类型不支持
        """
        if file_type not in self.FILE_TEMPLATES:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        filename = self.FILE_TEMPLATES[file_type].format(date=date)
        
        # 根据文件类型确定输出目录
        if stage:
            output_dir = self.base_dir / f'{stage}_output'
        else:
            # 根据文件类型自动判断阶段
            if file_type in ['gene_pool', 'market_report', 'emotion_report', 'theme_report']:
                output_dir = self.base_dir / 'stage1_output'
            elif file_type in ['overnight_variables', 'baseline_expectation', 'new_themes']:
                output_dir = self.base_dir / 'stage2_output'
            elif file_type in ['auction_monitoring', 'additional_pool', 'decision_navigation', 'daily_report']:
                output_dir = self.base_dir / 'stage3_output'
            else:
                output_dir = self.base_dir
        
        return output_dir / filename
    
    def save_json(self, data: Any, file_type: str, date: str, stage: Optional[str] = None) -> str:
        """
        保存数据为JSON文件
        
        Args:
            data: 要保存的数据（可以是字典或有to_dict方法的对象）
            file_type: 文件类型
            date: 日期字符串
            stage: 阶段标识，可选
        
        Returns:
            保存的文件路径
        """
        filepath = self.get_file_path(file_type, date, stage)
        
        # 转换为字典
        if hasattr(data, 'to_dict'):
            json_data = data.to_dict()
        elif isinstance(data, dict):
            json_data = data
        else:
            raise TypeError(f"Data must be dict or have to_dict method, got {type(data)}")
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {file_type} to {filepath}")
        return str(filepath)
    
    def load_json(self, file_type: str, date: str, stage: Optional[str] = None) -> Dict[str, Any]:
        """
        从JSON文件加载数据
        
        Args:
            file_type: 文件类型
            date: 日期字符串
            stage: 阶段标识，可选
        
        Returns:
            加载的数据字典
        
        Raises:
            FileNotFoundError: 如果文件不存在
        """
        filepath = self.get_file_path(file_type, date, stage)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {file_type} from {filepath}")
        return data
    
    def file_exists(self, file_type: str, date: str, stage: Optional[str] = None) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_type: 文件类型
            date: 日期字符串
            stage: 阶段标识，可选
        
        Returns:
            文件是否存在
        """
        filepath = self.get_file_path(file_type, date, stage)
        return filepath.exists()
    
    def save_gene_pool(self, gene_pool: GenePool) -> str:
        """
        保存基因池
        
        Args:
            gene_pool: 基因池对象
        
        Returns:
            保存的文件路径
        """
        return self.save_json(gene_pool, 'gene_pool', gene_pool.date, 'stage1')
    
    def load_gene_pool(self, date: str) -> GenePool:
        """
        加载基因池
        
        Args:
            date: 日期字符串
        
        Returns:
            基因池对象
        """
        data = self.load_json('gene_pool', date, 'stage1')
        return GenePool.from_dict(data)
    
    def save_baseline_expectations(
        self, 
        expectations: Dict[str, BaselineExpectation], 
        date: str
    ) -> str:
        """
        保存基准预期
        
        Args:
            expectations: 基准预期字典（stock_code -> BaselineExpectation）
            date: 日期字符串
        
        Returns:
            保存的文件路径
        """
        data = {
            'date': date,
            'expectations': {code: exp.to_dict() for code, exp in expectations.items()}
        }
        return self.save_json(data, 'baseline_expectation', date, 'stage2')
    
    def load_baseline_expectations(self, date: str) -> Dict[str, BaselineExpectation]:
        """
        加载基准预期
        
        Args:
            date: 日期字符串
        
        Returns:
            基准预期字典（stock_code -> BaselineExpectation）
        """
        data = self.load_json('baseline_expectation', date, 'stage2')
        return {
            code: BaselineExpectation.from_dict(exp) 
            for code, exp in data.get('expectations', {}).items()
        }
    
    def save_navigation_report(self, report: NavigationReport) -> str:
        """
        保存决策导航报告
        
        Args:
            report: 决策导航报告对象
        
        Returns:
            保存的文件路径
        """
        return self.save_json(report, 'decision_navigation', report.date, 'stage3')
    
    def load_navigation_report(self, date: str) -> NavigationReport:
        """
        加载决策导航报告
        
        Args:
            date: 日期字符串
        
        Returns:
            决策导航报告对象
        """
        data = self.load_json('decision_navigation', date, 'stage3')
        return NavigationReport.from_dict(data)
    
    def save_additional_pool(self, pool: AdditionalPool) -> str:
        """
        保存附加票池
        
        Args:
            pool: 附加票池对象
        
        Returns:
            保存的文件路径
        """
        return self.save_json(pool, 'additional_pool', pool.date, 'stage3')
    
    def load_additional_pool(self, date: str) -> AdditionalPool:
        """
        加载附加票池
        
        Args:
            date: 日期字符串
        
        Returns:
            附加票池对象
        """
        data = self.load_json('additional_pool', date, 'stage3')
        return AdditionalPool.from_dict(data)
    
    def list_files(self, file_type: str, stage: Optional[str] = None) -> List[str]:
        """
        列出指定类型的所有文件
        
        Args:
            file_type: 文件类型
            stage: 阶段标识，可选
        
        Returns:
            文件路径列表
        """
        if file_type not in self.FILE_TEMPLATES:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        # 确定搜索目录
        if stage:
            search_dir = self.base_dir / f'{stage}_output'
        else:
            # 根据文件类型自动判断阶段
            if file_type in ['gene_pool', 'market_report', 'emotion_report', 'theme_report']:
                search_dir = self.base_dir / 'stage1_output'
            elif file_type in ['overnight_variables', 'baseline_expectation', 'new_themes']:
                search_dir = self.base_dir / 'stage2_output'
            elif file_type in ['auction_monitoring', 'additional_pool', 'decision_navigation', 'daily_report']:
                search_dir = self.base_dir / 'stage3_output'
            else:
                search_dir = self.base_dir
        
        # 获取文件名模板的前缀
        template = self.FILE_TEMPLATES[file_type]
        prefix = template.split('{')[0]
        
        # 搜索匹配的文件
        files = []
        if search_dir.exists():
            for file in search_dir.iterdir():
                if file.is_file() and file.name.startswith(prefix):
                    files.append(str(file))
        
        return sorted(files)
    
    def archive_old_files(self, days_to_keep: int = 30) -> int:
        """
        归档旧文件到historical目录
        
        Args:
            days_to_keep: 保留最近多少天的文件，默认30天
        
        Returns:
            归档的文件数量
        """
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        archived_count = 0
        
        # 遍历所有输出目录
        for stage in ['stage1_output', 'stage2_output', 'stage3_output']:
            stage_dir = self.base_dir / stage
            if not stage_dir.exists():
                continue
            
            for file in stage_dir.iterdir():
                if not file.is_file():
                    continue
                
                # 从文件名提取日期
                try:
                    # 假设文件名格式为 xxx_YYYYMMDD.json
                    date_str = file.stem.split('_')[-1]
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                    
                    if file_date < cutoff_date:
                        # 移动到historical目录
                        historical_dir = self.base_dir / 'historical' / stage
                        historical_dir.mkdir(parents=True, exist_ok=True)
                        
                        dest_path = historical_dir / file.name
                        shutil.move(str(file), str(dest_path))
                        archived_count += 1
                        logger.info(f"Archived {file.name} to {historical_dir}")
                
                except (ValueError, IndexError) as e:
                    logger.warning(f"Could not parse date from filename {file.name}: {e}")
                    continue
        
        logger.info(f"Archived {archived_count} files older than {days_to_keep} days")
        return archived_count
    
    def cleanup_old_files(self, days_to_keep: int = 90) -> int:
        """
        清理historical目录中的旧文件
        
        Args:
            days_to_keep: 保留最近多少天的文件，默认90天
        
        Returns:
            删除的文件数量
        """
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0
        
        historical_dir = self.base_dir / 'historical'
        if not historical_dir.exists():
            return 0
        
        # 递归遍历historical目录
        for file in historical_dir.rglob('*'):
            if not file.is_file():
                continue
            
            # 从文件名提取日期
            try:
                date_str = file.stem.split('_')[-1]
                file_date = datetime.strptime(date_str, '%Y%m%d')
                
                if file_date < cutoff_date:
                    file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old file: {file.name}")
            
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse date from filename {file.name}: {e}")
                continue
        
        logger.info(f"Deleted {deleted_count} files older than {days_to_keep} days from historical")
        return deleted_count
    
    def get_latest_file(self, file_type: str, stage: Optional[str] = None) -> Optional[str]:
        """
        获取指定类型的最新文件
        
        Args:
            file_type: 文件类型
            stage: 阶段标识，可选
        
        Returns:
            最新文件的路径，如果没有文件则返回None
        """
        files = self.list_files(file_type, stage)
        return files[-1] if files else None
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息
        
        Returns:
            存储统计信息字典
        """
        stats = {
            'base_dir': str(self.base_dir),
            'total_size_mb': 0,
            'stages': {}
        }
        
        # 统计各阶段的文件数量和大小
        for stage in ['stage1_output', 'stage2_output', 'stage3_output', 'historical']:
            stage_dir = self.base_dir / stage
            if not stage_dir.exists():
                continue
            
            file_count = 0
            total_size = 0
            
            for file in stage_dir.rglob('*'):
                if file.is_file():
                    file_count += 1
                    total_size += file.stat().st_size
            
            stats['stages'][stage] = {
                'file_count': file_count,
                'size_mb': round(total_size / (1024 * 1024), 2)
            }
            stats['total_size_mb'] += stats['stages'][stage]['size_mb']
        
        stats['total_size_mb'] = round(stats['total_size_mb'], 2)
        return stats
