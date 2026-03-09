"""
Stage1 Agent - 数据沉淀与复盘

职责：
- 读取当日收盘行情数据
- 调用现有的复盘Agents生成三份报告
- 构建和更新基因池
- 计算个股技术位

需求: 1.1, 1.5, 21.1
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from ..common.logger import get_logger
from ..common.models import GenePool, MarketReport, EmotionReport, ThemeReport
from ..storage.file_storage_manager import FileStorageManager
from ..storage.database_manager import DatabaseManager
from .report_generator import ReportGenerator
from .gene_pool_builder import GenePoolBuilder
from .technical_calculator import TechnicalCalculator

logger = get_logger(__name__)


class Stage1Agent:
    """
    Stage1 Agent - 数据沉淀与复盘
    
    职责：
    1. 生成三份复盘报告（大盘、情绪、题材）
    2. 构建基因池（连板梯队、炸板股、辨识度个股、趋势股）
    3. 计算个股技术位
    4. 存储所有输出数据
    
    特点：
    - 独立运作，不依赖其他Agent
    - 支持单独启动和运行
    - 完整的错误处理和日志记录
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Stage1 Agent
        
        Args:
            config: 配置字典，包含各模块的配置参数
        """
        self.config = config or {}
        
        # 初始化各模块
        self.report_generator = ReportGenerator(config)
        self.gene_pool_builder = GenePoolBuilder(config)
        self.technical_calculator = TechnicalCalculator(config)
        
        # 初始化存储管理器
        base_dir = self.config.get('base_dir', 'data')
        self.file_storage = FileStorageManager(base_dir)
        
        # 初始化数据库管理器
        db_path = self.config.get('db_path', 'data/historical/gene_pool_history.db')
        self.database = DatabaseManager(db_path)
        
        logger.info("Stage1 Agent初始化完成")
    
    def run(self, date: str) -> Dict[str, Any]:
        """
        运行Stage1 Agent主流程
        
        Args:
            date: 分析日期，格式：YYYY-MM-DD
        
        Returns:
            Dict: 运行结果，包含：
                - success: bool, 是否成功
                - date: str, 分析日期
                - gene_pool_path: str, 基因池文件路径
                - market_report_path: str, 大盘报告文件路径
                - emotion_report_path: str, 情绪报告文件路径
                - theme_report_path: str, 题材报告文件路径
                - error: str, 错误信息（如果失败）
        
        需求: 1.1, 1.5, 21.1
        """
        logger.info(f"========== Stage1 Agent开始运行: {date} ==========")
        
        result = {
            'success': False,
            'date': date,
            'gene_pool_path': None,
            'market_report_path': None,
            'emotion_report_path': None,
            'theme_report_path': None,
            'error': None
        }
        
        try:
            # 步骤1: 生成三份复盘报告
            logger.info("步骤1: 生成复盘报告")
            reports = self._generate_reports(date)
            
            if not reports:
                raise RuntimeError("生成复盘报告失败")
            
            # 步骤2: 构建基因池
            logger.info("步骤2: 构建基因池")
            gene_pool = self._build_gene_pool(date)
            
            if not gene_pool:
                raise RuntimeError("构建基因池失败")
            
            # 步骤3: 计算技术位
            logger.info("步骤3: 计算技术位")
            gene_pool = self._calculate_technical_levels(gene_pool, date)
            
            # 步骤4: 存储数据
            logger.info("步骤4: 存储数据")
            paths = self._save_data(date, gene_pool, reports)
            
            # 步骤5: 存储到数据库（可选）
            if self.config.get('enable_database', True):
                logger.info("步骤5: 存储到数据库")
                self._save_to_database(date, gene_pool, reports)
            
            # 更新结果
            result['success'] = True
            result.update(paths)
            
            logger.info(f"========== Stage1 Agent运行成功: {date} ==========")
            logger.info(f"基因池个股数: {len(gene_pool.all_stocks)}")
            logger.info(f"连板梯队: {len(gene_pool.continuous_limit_up)}")
            logger.info(f"炸板股: {len(gene_pool.failed_limit_up)}")
            logger.info(f"辨识度个股: {len(gene_pool.recognition_stocks)}")
            logger.info(f"趋势股: {len(gene_pool.trend_stocks)}")
            
        except Exception as e:
            logger.error(f"Stage1 Agent运行失败: {e}", exc_info=True)
            result['error'] = str(e)
        
        return result
    
    def _generate_reports(self, date: str) -> Optional[Dict[str, Any]]:
        """
        生成三份复盘报告
        
        Args:
            date: 分析日期
        
        Returns:
            Dict: 包含三份报告的字典，如果失败返回None
        """
        try:
            # 生成大盘分析报告
            market_report = self.report_generator.generate_market_report(date)
            logger.info("大盘分析报告生成成功")
            
            # 生成情绪分析报告
            emotion_report = self.report_generator.generate_emotion_report(date)
            logger.info("情绪分析报告生成成功")
            
            # 生成题材分析报告
            theme_report = self.report_generator.generate_theme_report(date)
            logger.info("题材分析报告生成成功")
            
            return {
                'market_report': market_report,
                'emotion_report': emotion_report,
                'theme_report': theme_report
            }
            
        except Exception as e:
            logger.error(f"生成复盘报告失败: {e}", exc_info=True)
            return None
    
    def _build_gene_pool(self, date: str) -> Optional[GenePool]:
        """
        构建基因池
        
        Args:
            date: 分析日期
        
        Returns:
            GenePool: 基因池对象，如果失败返回None
        """
        try:
            gene_pool = self.gene_pool_builder.build_gene_pool(date)
            logger.info(f"基因池构建成功，共 {len(gene_pool.all_stocks)} 只个股")
            return gene_pool
            
        except Exception as e:
            logger.error(f"构建基因池失败: {e}", exc_info=True)
            return None
    
    def _calculate_technical_levels(
        self, 
        gene_pool: GenePool, 
        date: str
    ) -> GenePool:
        """
        计算基因池中所有个股的技术位
        
        Args:
            gene_pool: 基因池对象
            date: 分析日期
        
        Returns:
            GenePool: 更新后的基因池对象
        """
        try:
            success_count = 0
            fail_count = 0
            
            # 遍历所有个股，计算技术位
            for stock_code, stock in gene_pool.all_stocks.items():
                try:
                    # 获取历史数据（60天）
                    price_history, volume_history = self._get_stock_history(stock_code, date, lookback_days=60)
                    
                    if not price_history or not volume_history:
                        logger.warning(f"个股 {stock_code} 历史数据不足，跳过技术位计算")
                        fail_count += 1
                        continue
                    
                    # 计算技术位
                    technical_levels = self.technical_calculator.calculate_technical_levels(
                        stock, 
                        price_history,
                        volume_history
                    )
                    
                    # 更新个股的技术位
                    stock.technical_levels = technical_levels
                    success_count += 1
                    
                except Exception as e:
                    logger.warning(f"计算个股 {stock_code} 技术位失败: {e}")
                    fail_count += 1
                    continue
            
            logger.info(f"技术位计算完成: 成功 {success_count}, 失败 {fail_count}")
            return gene_pool
            
        except Exception as e:
            logger.error(f"计算技术位失败: {e}", exc_info=True)
            return gene_pool
    
    def _get_stock_history(
        self,
        stock_code: str,
        end_date: str,
        lookback_days: int = 60
    ) -> tuple:
        """
        获取个股历史数据
        
        Args:
            stock_code: 股票代码
            end_date: 结束日期，格式：YYYY-MM-DD
            lookback_days: 回溯天数（默认60天，约3个月）
        
        Returns:
            tuple: (price_history, volume_history)
                - price_history: List[float], 历史收盘价列表
                - volume_history: List[float], 历史成交量列表
        """
        try:
            from datetime import datetime, timedelta
            from ..data_sources.akshare_client import AKShareClient
            
            # 计算开始日期（5个月 = 150天，考虑交易日实际获取更多天数）
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            start_dt = end_dt - timedelta(days=150)  # 5个月约150天
            start_date = start_dt.strftime('%Y%m%d')
            end_date_str = end_dt.strftime('%Y%m%d')
            
            # 使用AKShare获取历史数据
            akshare_client = AKShareClient()
            hist_data = akshare_client.get_stock_hist(
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date_str,
                period="daily",
                adjust="qfq"  # 前复权
            )
            
            if hist_data.empty:
                logger.warning(f"个股 {stock_code} 历史数据为空")
                return [], []
            
            # 提取收盘价和成交量
            # AKShare返回的列名：日期、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率
            price_history = hist_data['收盘'].tolist()
            volume_history = hist_data['成交量'].tolist()
            
            logger.info(f"成功获取个股 {stock_code} 历史数据: {len(price_history)} 条记录")
            return price_history, volume_history
            
        except Exception as e:
            logger.error(f"获取个股历史数据失败: {stock_code}, {e}")
            return [], []
    
    def _save_data(
        self, 
        date: str, 
        gene_pool: GenePool, 
        reports: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        保存数据到文件系统
        
        Args:
            date: 分析日期
            gene_pool: 基因池对象
            reports: 报告字典
        
        Returns:
            Dict: 文件路径字典
        """
        try:
            # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
            date_str = date.replace('-', '')
            
            # 保存基因池
            gene_pool_path = self.file_storage.save_gene_pool(gene_pool)
            logger.info(f"基因池已保存: {gene_pool_path}")
            
            # 保存大盘报告
            market_report_path = self.file_storage.save_json(
                reports['market_report'],
                'market_report',
                date_str,
                'stage1'
            )
            logger.info(f"大盘报告已保存: {market_report_path}")
            
            # 保存情绪报告
            emotion_report_path = self.file_storage.save_json(
                reports['emotion_report'],
                'emotion_report',
                date_str,
                'stage1'
            )
            logger.info(f"情绪报告已保存: {emotion_report_path}")
            
            # 保存题材报告
            theme_report_path = self.file_storage.save_json(
                reports['theme_report'],
                'theme_report',
                date_str,
                'stage1'
            )
            logger.info(f"题材报告已保存: {theme_report_path}")
            
            return {
                'gene_pool_path': gene_pool_path,
                'market_report_path': market_report_path,
                'emotion_report_path': emotion_report_path,
                'theme_report_path': theme_report_path
            }
            
        except Exception as e:
            logger.error(f"保存数据失败: {e}", exc_info=True)
            raise
    
    def _save_to_database(
        self, 
        date: str, 
        gene_pool: GenePool, 
        reports: Dict[str, Any]
    ) -> None:
        """
        保存数据到数据库
        
        Args:
            date: 分析日期
            gene_pool: 基因池对象
            reports: 报告字典
        """
        try:
            # 使用DatabaseManager的insert_gene_pool方法保存基因池
            inserted_count = self.database.insert_gene_pool(gene_pool)
            logger.info(f"基因池历史已保存到数据库: {inserted_count} 条记录")
            
        except Exception as e:
            logger.error(f"保存到数据库失败: {e}", exc_info=True)
            # 数据库保存失败不影响主流程
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取Agent状态信息
        
        Returns:
            Dict: 状态信息
        """
        return {
            'agent': 'Stage1Agent',
            'status': 'ready',
            'config': self.config,
            'storage_stats': self.file_storage.get_storage_stats()
        }
    
    def validate_dependencies(self) -> Dict[str, bool]:
        """
        验证依赖项是否可用
        
        Returns:
            Dict: 依赖项验证结果
        """
        results = {
            'report_generator': False,
            'gene_pool_builder': False,
            'technical_calculator': False,
            'file_storage': False,
            'database': False
        }
        
        try:
            # 验证报告生成器
            results['report_generator'] = self.report_generator is not None
            
            # 验证基因池构建器
            results['gene_pool_builder'] = self.gene_pool_builder is not None
            
            # 验证技术计算器
            results['technical_calculator'] = self.technical_calculator is not None
            
            # 验证文件存储
            results['file_storage'] = self.file_storage is not None
            
            # 验证数据库
            results['database'] = self.database is not None
            
        except Exception as e:
            logger.error(f"验证依赖项失败: {e}")
        
        return results
