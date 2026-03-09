"""
SQLite数据库管理器

本模块实现SQLite数据库管理功能，包括：
- 数据库Schema创建
- 数据插入和查询
- 历史数据存储
- 数据统计分析

需求: 17.1-17.5
"""

import sqlite3
import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from ..common.logger import get_logger
from ..common.models import (
    Stock, GenePool, BaselineExpectation, 
    AuctionData, ExpectationScore, StatusScore
)

logger = get_logger(__name__)


class DatabaseManager:
    """
    SQLite数据库管理器
    
    负责管理系统的数据库操作，包括：
    - 数据库Schema创建和维护
    - 历史数据的存储和查询
    - 数据统计和分析
    """
    
    # 数据库Schema定义
    SCHEMA_SQL = """
    -- 基因池历史表
    CREATE TABLE IF NOT EXISTS gene_pool_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        stock_code TEXT NOT NULL,
        stock_name TEXT,
        category TEXT,  -- continuous_limit_up, failed_limit_up, recognition_stocks, trend_stocks
        board_height INTEGER,
        price REAL,
        change_pct REAL,
        amount REAL,
        technical_data TEXT,  -- JSON格式
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(date, stock_code, category)
    );
    
    CREATE INDEX IF NOT EXISTS idx_gene_pool_date ON gene_pool_history(date);
    CREATE INDEX IF NOT EXISTS idx_gene_pool_stock ON gene_pool_history(stock_code);
    CREATE INDEX IF NOT EXISTS idx_gene_pool_category ON gene_pool_history(category);
    
    -- 基准预期历史表
    CREATE TABLE IF NOT EXISTS baseline_expectation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        stock_code TEXT NOT NULL,
        stock_name TEXT,
        expected_open_min REAL,
        expected_open_max REAL,
        expected_amount_min REAL,
        logic TEXT,
        confidence REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(date, stock_code)
    );
    
    CREATE INDEX IF NOT EXISTS idx_baseline_date ON baseline_expectation_history(date);
    CREATE INDEX IF NOT EXISTS idx_baseline_stock ON baseline_expectation_history(stock_code);
    
    -- 竞价监测结果表
    CREATE TABLE IF NOT EXISTS auction_monitoring_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        stock_code TEXT NOT NULL,
        stock_name TEXT,
        open_price REAL,
        auction_amount REAL,
        auction_volume REAL,
        seal_amount REAL,
        withdrawal_detected INTEGER,  -- 0 or 1
        trajectory_rating TEXT,
        volume_score REAL,
        price_score REAL,
        independence_score REAL,
        expectation_score REAL,
        recommendation TEXT,
        confidence REAL,
        actual_performance TEXT,  -- 用于后续回测，JSON格式
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(date, stock_code)
    );
    
    CREATE INDEX IF NOT EXISTS idx_auction_date ON auction_monitoring_history(date);
    CREATE INDEX IF NOT EXISTS idx_auction_stock ON auction_monitoring_history(stock_code);
    CREATE INDEX IF NOT EXISTS idx_auction_score ON auction_monitoring_history(expectation_score);
    
    -- 附加池历史表
    CREATE TABLE IF NOT EXISTS additional_pool_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        stock_code TEXT NOT NULL,
        stock_name TEXT,
        pool_type TEXT,  -- top_seals, rush_positioning, energy_burst, reverse_nuclear, sector_formation
        theme_recognition REAL,
        urgency REAL,
        emotion_hedge REAL,
        status_score REAL,
        rank INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(date, stock_code, pool_type)
    );
    
    CREATE INDEX IF NOT EXISTS idx_additional_date ON additional_pool_history(date);
    CREATE INDEX IF NOT EXISTS idx_additional_stock ON additional_pool_history(stock_code);
    CREATE INDEX IF NOT EXISTS idx_additional_type ON additional_pool_history(pool_type);
    CREATE INDEX IF NOT EXISTS idx_additional_score ON additional_pool_history(status_score);
    """
    
    def __init__(self, db_path: str = 'data/historical/gene_pool_history.db'):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn: Optional[sqlite3.Connection] = None
        self._initialize_database()
        logger.info(f"DatabaseManager initialized with db_path: {self.db_path}")
    
    def _initialize_database(self) -> None:
        """初始化数据库，创建表结构"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 执行Schema创建
        cursor.executescript(self.SCHEMA_SQL)
        conn.commit()
        
        logger.info("Database schema initialized")
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        获取数据库连接
        
        Returns:
            数据库连接对象
        """
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row  # 使用Row对象，可以通过列名访问
        return self.conn
    
    def close(self) -> None:
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    # ==================== 基因池历史数据操作 ====================
    
    def insert_gene_pool(self, gene_pool: GenePool) -> int:
        """
        插入基因池数据
        
        Args:
            gene_pool: 基因池对象
        
        Returns:
            插入的记录数
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        inserted_count = 0
        
        # 定义类别映射
        categories = {
            'continuous_limit_up': gene_pool.continuous_limit_up,
            'failed_limit_up': gene_pool.failed_limit_up,
            'recognition_stocks': gene_pool.recognition_stocks,
            'trend_stocks': gene_pool.trend_stocks
        }
        
        for category, stocks in categories.items():
            for stock in stocks:
                try:
                    technical_data = json.dumps(
                        stock.technical_levels.to_dict() if stock.technical_levels else {}
                    )
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO gene_pool_history 
                        (date, stock_code, stock_name, category, board_height, 
                         price, change_pct, amount, technical_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        gene_pool.date,
                        stock.code,
                        stock.name,
                        category,
                        stock.board_height,
                        stock.price,
                        stock.change_pct,
                        stock.amount,
                        technical_data
                    ))
                    inserted_count += 1
                
                except sqlite3.Error as e:
                    logger.error(f"Error inserting gene pool stock {stock.code}: {e}")
        
        conn.commit()
        logger.info(f"Inserted {inserted_count} gene pool records for date {gene_pool.date}")
        return inserted_count
    
    def query_gene_pool(
        self, 
        date: Optional[str] = None,
        stock_code: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询基因池历史数据
        
        Args:
            date: 日期筛选，可选
            stock_code: 股票代码筛选，可选
            category: 类别筛选，可选
            limit: 返回记录数限制
        
        Returns:
            查询结果列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM gene_pool_history WHERE 1=1"
        params = []
        
        if date:
            query += " AND date = ?"
            params.append(date)
        
        if stock_code:
            query += " AND stock_code = ?"
            params.append(stock_code)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += " ORDER BY date DESC, stock_code LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            result = dict(row)
            # 解析technical_data
            if result.get('technical_data'):
                try:
                    result['technical_data'] = json.loads(result['technical_data'])
                except json.JSONDecodeError:
                    result['technical_data'] = {}
            results.append(result)
        
        return results
    
    # ==================== 基准预期历史数据操作 ====================
    
    def insert_baseline_expectations(
        self, 
        expectations: Dict[str, BaselineExpectation],
        date: str
    ) -> int:
        """
        插入基准预期数据
        
        Args:
            expectations: 基准预期字典
            date: 日期
        
        Returns:
            插入的记录数
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        inserted_count = 0
        
        for stock_code, expectation in expectations.items():
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO baseline_expectation_history 
                    (date, stock_code, stock_name, expected_open_min, expected_open_max,
                     expected_amount_min, logic, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    date,
                    expectation.stock_code,
                    expectation.stock_name,
                    expectation.expected_open_min,
                    expectation.expected_open_max,
                    expectation.expected_amount_min,
                    expectation.logic,
                    expectation.confidence
                ))
                inserted_count += 1
            
            except sqlite3.Error as e:
                logger.error(f"Error inserting baseline expectation for {stock_code}: {e}")
        
        conn.commit()
        logger.info(f"Inserted {inserted_count} baseline expectation records for date {date}")
        return inserted_count
    
    def query_baseline_expectations(
        self,
        date: Optional[str] = None,
        stock_code: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询基准预期历史数据
        
        Args:
            date: 日期筛选，可选
            stock_code: 股票代码筛选，可选
            limit: 返回记录数限制
        
        Returns:
            查询结果列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM baseline_expectation_history WHERE 1=1"
        params = []
        
        if date:
            query += " AND date = ?"
            params.append(date)
        
        if stock_code:
            query += " AND stock_code = ?"
            params.append(stock_code)
        
        query += " ORDER BY date DESC, stock_code LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== 竞价监测历史数据操作 ====================
    
    def insert_auction_monitoring(
        self,
        date: str,
        stock_code: str,
        stock_name: str,
        auction_data: AuctionData,
        expectation_score: ExpectationScore
    ) -> int:
        """
        插入竞价监测数据
        
        Args:
            date: 日期
            stock_code: 股票代码
            stock_name: 股票名称
            auction_data: 竞价数据
            expectation_score: 超预期分值
        
        Returns:
            插入的记录数（1或0）
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO auction_monitoring_history 
                (date, stock_code, stock_name, open_price, auction_amount, auction_volume,
                 seal_amount, withdrawal_detected, trajectory_rating,
                 volume_score, price_score, independence_score, expectation_score,
                 recommendation, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date,
                stock_code,
                stock_name,
                auction_data.open_price,
                auction_data.auction_amount,
                auction_data.auction_volume,
                auction_data.seal_amount,
                1 if auction_data.withdrawal_detected else 0,
                auction_data.trajectory_rating,
                expectation_score.volume_score,
                expectation_score.price_score,
                expectation_score.independence_score,
                expectation_score.total_score,
                expectation_score.recommendation,
                expectation_score.confidence
            ))
            conn.commit()
            logger.info(f"Inserted auction monitoring for {stock_code} on {date}")
            return 1
        
        except sqlite3.Error as e:
            logger.error(f"Error inserting auction monitoring for {stock_code}: {e}")
            return 0
    
    def query_auction_monitoring(
        self,
        date: Optional[str] = None,
        stock_code: Optional[str] = None,
        min_score: Optional[float] = None,
        recommendation: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询竞价监测历史数据
        
        Args:
            date: 日期筛选，可选
            stock_code: 股票代码筛选，可选
            min_score: 最低分值筛选，可选
            recommendation: 操作建议筛选，可选
            limit: 返回记录数限制
        
        Returns:
            查询结果列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM auction_monitoring_history WHERE 1=1"
        params = []
        
        if date:
            query += " AND date = ?"
            params.append(date)
        
        if stock_code:
            query += " AND stock_code = ?"
            params.append(stock_code)
        
        if min_score is not None:
            query += " AND expectation_score >= ?"
            params.append(min_score)
        
        if recommendation:
            query += " AND recommendation = ?"
            params.append(recommendation)
        
        query += " ORDER BY date DESC, expectation_score DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def update_actual_performance(
        self,
        date: str,
        stock_code: str,
        performance_data: Dict[str, Any]
    ) -> bool:
        """
        更新实际表现数据（用于回测）
        
        Args:
            date: 日期
            stock_code: 股票代码
            performance_data: 实际表现数据字典
        
        Returns:
            是否更新成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE auction_monitoring_history 
                SET actual_performance = ?
                WHERE date = ? AND stock_code = ?
            """, (
                json.dumps(performance_data),
                date,
                stock_code
            ))
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Updated actual performance for {stock_code} on {date}")
                return True
            else:
                logger.warning(f"No record found for {stock_code} on {date}")
                return False
        
        except sqlite3.Error as e:
            logger.error(f"Error updating actual performance: {e}")
            return False
    
    # ==================== 附加池历史数据操作 ====================
    
    def insert_additional_pool(
        self,
        date: str,
        stock: Stock,
        pool_type: str,
        status_score: StatusScore
    ) -> int:
        """
        插入附加池数据
        
        Args:
            date: 日期
            stock: 个股对象
            pool_type: 池类型
            status_score: 地位分值
        
        Returns:
            插入的记录数（1或0）
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO additional_pool_history 
                (date, stock_code, stock_name, pool_type, theme_recognition,
                 urgency, emotion_hedge, status_score, rank)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date,
                stock.code,
                stock.name,
                pool_type,
                status_score.theme_recognition,
                status_score.urgency,
                status_score.emotion_hedge,
                status_score.total_score,
                status_score.rank
            ))
            conn.commit()
            logger.info(f"Inserted additional pool record for {stock.code} on {date}")
            return 1
        
        except sqlite3.Error as e:
            logger.error(f"Error inserting additional pool for {stock.code}: {e}")
            return 0
    
    def query_additional_pool(
        self,
        date: Optional[str] = None,
        stock_code: Optional[str] = None,
        pool_type: Optional[str] = None,
        min_score: Optional[float] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询附加池历史数据
        
        Args:
            date: 日期筛选，可选
            stock_code: 股票代码筛选，可选
            pool_type: 池类型筛选，可选
            min_score: 最低分值筛选，可选
            limit: 返回记录数限制
        
        Returns:
            查询结果列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM additional_pool_history WHERE 1=1"
        params = []
        
        if date:
            query += " AND date = ?"
            params.append(date)
        
        if stock_code:
            query += " AND stock_code = ?"
            params.append(stock_code)
        
        if pool_type:
            query += " AND pool_type = ?"
            params.append(pool_type)
        
        if min_score is not None:
            query += " AND status_score >= ?"
            params.append(min_score)
        
        query += " ORDER BY date DESC, status_score DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== 统计分析功能 ====================
    
    def get_stock_history(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取个股的完整历史记录
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，可选
            end_date: 结束日期，可选
        
        Returns:
            包含各类历史数据的字典
        """
        result = {
            'gene_pool': [],
            'baseline_expectation': [],
            'auction_monitoring': [],
            'additional_pool': []
        }
        
        # 构建日期筛选条件
        date_filter = ""
        params = [stock_code]
        
        if start_date and end_date:
            date_filter = " AND date BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        elif start_date:
            date_filter = " AND date >= ?"
            params.append(start_date)
        elif end_date:
            date_filter = " AND date <= ?"
            params.append(end_date)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 查询基因池历史
        cursor.execute(
            f"SELECT * FROM gene_pool_history WHERE stock_code = ?{date_filter} ORDER BY date",
            params
        )
        result['gene_pool'] = [dict(row) for row in cursor.fetchall()]
        
        # 查询基准预期历史
        cursor.execute(
            f"SELECT * FROM baseline_expectation_history WHERE stock_code = ?{date_filter} ORDER BY date",
            params
        )
        result['baseline_expectation'] = [dict(row) for row in cursor.fetchall()]
        
        # 查询竞价监测历史
        cursor.execute(
            f"SELECT * FROM auction_monitoring_history WHERE stock_code = ?{date_filter} ORDER BY date",
            params
        )
        result['auction_monitoring'] = [dict(row) for row in cursor.fetchall()]
        
        # 查询附加池历史
        cursor.execute(
            f"SELECT * FROM additional_pool_history WHERE stock_code = ?{date_filter} ORDER BY date",
            params
        )
        result['additional_pool'] = [dict(row) for row in cursor.fetchall()]
        
        return result
    
    def get_recommendation_accuracy(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        计算建议的准确率（需要先更新actual_performance）
        
        Args:
            start_date: 开始日期，可选
            end_date: 结束日期，可选
        
        Returns:
            准确率统计字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT recommendation, COUNT(*) as total,
                   SUM(CASE WHEN actual_performance IS NOT NULL THEN 1 ELSE 0 END) as with_performance
            FROM auction_monitoring_history
            WHERE 1=1
        """
        params = []
        
        if start_date and end_date:
            query += " AND date BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        elif start_date:
            query += " AND date >= ?"
            params.append(start_date)
        elif end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " GROUP BY recommendation"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        stats = {}
        for row in results:
            stats[row['recommendation']] = {
                'total': row['total'],
                'with_performance': row['with_performance']
            }
        
        return stats
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            数据库统计信息字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {
            'db_path': str(self.db_path),
            'db_size_mb': round(self.db_path.stat().st_size / (1024 * 1024), 2),
            'tables': {}
        }
        
        # 统计各表的记录数
        tables = [
            'gene_pool_history',
            'baseline_expectation_history',
            'auction_monitoring_history',
            'additional_pool_history'
        ]
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()['count']
            
            cursor.execute(f"SELECT MIN(date) as min_date, MAX(date) as max_date FROM {table}")
            date_range = cursor.fetchone()
            
            stats['tables'][table] = {
                'record_count': count,
                'date_range': {
                    'min': date_range['min_date'],
                    'max': date_range['max_date']
                }
            }
        
        return stats
    
    def vacuum(self) -> None:
        """
        优化数据库（清理碎片）
        """
        conn = self._get_connection()
        conn.execute("VACUUM")
        logger.info("Database vacuumed")
