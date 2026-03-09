"""
基因池构建器

职责：
- 扫描当日连板梯队中的所有个股
- 识别炸板股（使用开盘啦的反包板数据接口）
- 识别辨识度个股（使用开盘啦的板块风向标接口）
- 识别趋势股（筛选同花顺热股前50）
- 构建和更新基因池
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

from ..common.logger import get_logger
from ..common.models import Stock, GenePool, TechnicalLevels
from ..data_sources.kaipanla_client import KaipanlaClient
from .technical_calculator import TechnicalCalculator

# 尝试导入 WencaiClient（可选）
try:
    from ..data_sources.wencai_client import WencaiClient
    WENCAI_AVAILABLE = True
except ImportError:
    WENCAI_AVAILABLE = False
    WencaiClient = None

logger = get_logger(__name__)


class GenePoolBuilder:
    """基因池构建器
    
    职责：
    - 识别连板梯队个股
    - 识别炸板股（使用反包板接口）
    - 识别辨识度个股（使用板块风向标接口）
    - 识别趋势股（筛选同花顺热股前50）
    - 构建基因池
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化基因池构建器
        
        Args:
            config: 配置字典，支持以下选项：
                - use_wencai: bool, 是否优先使用问财获取热股（默认False）
                - wencai_fallback: bool, 当kaipanla失败时是否回退到问财（默认True）
        """
        self.config = config or {}
        self.kaipanla_client = KaipanlaClient()
        self.technical_calculator = TechnicalCalculator(config)
        
        # 初始化问财客户端（如果可用且配置启用）
        self.wencai_client = None
        self.use_wencai = self.config.get('use_wencai', False)
        self.wencai_fallback = self.config.get('wencai_fallback', True)
        
        if WENCAI_AVAILABLE and (self.use_wencai or self.wencai_fallback):
            try:
                self.wencai_client = WencaiClient()
                logger.info(f"问财客户端已初始化 (use_wencai={self.use_wencai}, fallback={self.wencai_fallback})")
            except Exception as e:
                logger.warning(f"问财客户端初始化失败: {e}")
                self.wencai_client = None
        
        logger.info("基因池构建器初始化完成")
    
    def scan_continuous_limit_up(self, date: str) -> List[Stock]:
        """扫描连板梯队
        
        Args:
            date: 分析日期，格式：YYYY-MM-DD
            
        Returns:
            List[Stock]: 连板个股列表
        """
        logger.info(f"扫描连板梯队: {date}")
        
        try:
            # 获取连板个股数据
            continuous_data = self.kaipanla_client.get_continuous_limit_up_stocks(date)
            
            if continuous_data.empty:
                logger.warning(f"未找到连板个股: {date}")
                return []
            
            # 获取板块排名数据（用于补充题材信息）
            sector_themes_map = {}
            try:
                sector_data = self.kaipanla_client.get_sector_ranking(date=date)
                if sector_data and 'sectors' in sector_data:
                    # 构建股票代码到题材列表的映射
                    for sector in sector_data['sectors']:
                        sector_name = sector.get('sector_name', '')
                        stocks_in_sector = sector.get('stocks', [])
                        
                        for s in stocks_in_sector:
                            stock_code = str(s.get('股票代码', s.get('stock_code', '')))
                            if stock_code:
                                if stock_code not in sector_themes_map:
                                    sector_themes_map[stock_code] = []
                                if sector_name and sector_name not in sector_themes_map[stock_code]:
                                    sector_themes_map[stock_code].append(sector_name)
                    
                    logger.info(f"获取到 {len(sector_themes_map)} 只股票的题材信息")
            except Exception as e:
                logger.warning(f"获取板块排名数据失败: {e}")
            
            # 转换为Stock对象列表
            stocks = []
            for _, row in continuous_data.iterrows():
                stock = self._create_stock_from_row(row, date)
                if stock:
                    # 补充量价数据
                    stock = self._enrich_stock_with_intraday_data(stock, date)
                    
                    # 补充题材信息（从预先获取的板块数据）
                    if stock.code in sector_themes_map:
                        stock.themes = sector_themes_map[stock.code]
                        logger.debug(f"补充个股 {stock.code} {stock.name} 题材: {', '.join(stock.themes)}")
                    
                    stocks.append(stock)
            
            logger.info(f"找到 {len(stocks)} 只连板个股")
            return stocks
            
        except Exception as e:
            logger.error(f"扫描连板梯队失败: {e}")
            return []
    
    def identify_failed_limit_up(self, date: str) -> List[Stock]:
        """识别炸板股（曾涨停但未封住的个股）
        使用开盘啦的历史炸板股数据接口
        
        Args:
            date: 日期，格式YYYY-MM-DD
            
        Returns:
            炸板股列表
        """
        logger.info(f"开始识别炸板股: {date}")
        
        try:
            # 使用开盘啦的历史炸板股接口
            broken_stocks_data = self.kaipanla_client.get_historical_broken_limit_up(date)
            
            if not broken_stocks_data:
                logger.info(f"{date}无炸板股")
                return []
            
            # 转换为Stock对象
            failed_stocks = []
            for stock_data in broken_stocks_data:
                stock = Stock(
                    code=stock_data.get('stock_code', ''),
                    name=stock_data.get('stock_name', ''),
                    market_cap=0.0,  # API不返回市值
                    price=0.0,  # API不返回价格
                    change_pct=stock_data.get('change_pct', 0.0),
                    volume=0.0,  # API不返回成交量
                    amount=stock_data.get('turnover_amount', 0.0),
                    turnover_rate=stock_data.get('turnover_rate', 0.0),
                    board_height=stock_data.get('yesterday_consecutive', 0),
                    themes=stock_data.get('sector', '').split('、') if stock_data.get('sector') else [],
                    technical_levels=None
                )
                # 添加自定义属性
                stock.is_failed_limit_up = True
                stock.limit_up_time = stock_data.get('limit_up_time', 0)
                stock.open_time = stock_data.get('open_time', 0)
                stock.main_capital_net = stock_data.get('main_capital_net', 0.0)
                failed_stocks.append(stock)
            
            logger.info(f"识别到{len(failed_stocks)}只炸板股")
            return failed_stocks
            
        except Exception as e:
            logger.error(f"识别炸板股失败: {e}")
            return []
    
    def _get_hot_stocks(self, max_rank: int = 50, date: Optional[str] = None) -> pd.Series:
        """获取同花顺热门股排行
        
        支持多数据源，优先级：
        1. 如果配置了 use_wencai=True，优先使用问财
        2. 否则使用 kaipanla（Selenium爬虫）
        3. 如果 kaipanla 失败且配置了 wencai_fallback=True，回退到问财
        
        Args:
            max_rank: 最大获取排名数
            date: 日期（可选），格式YYYY-MM-DD
            
        Returns:
            pd.Series: index为排名，values为个股名称
        """
        logger.info(f"获取同花顺热门股 (max_rank={max_rank}, date={date})")
        
        # 策略1: 优先使用问财（如果配置启用）
        if self.use_wencai and self.wencai_client:
            try:
                logger.info("使用问财获取热门股（优先模式）")
                hot_stocks = self.wencai_client.get_hot_stocks_simple(
                    max_rank=max_rank,
                    date=date
                )
                if not hot_stocks.empty:
                    logger.info(f"问财成功获取 {len(hot_stocks)} 只热门股")
                    return hot_stocks
                else:
                    logger.warning("问财返回空数据，尝试使用 kaipanla")
            except Exception as e:
                logger.warning(f"问财获取失败: {e}，尝试使用 kaipanla")
        
        # 策略2: 使用 kaipanla（默认方式）
        try:
            logger.info("使用 kaipanla 获取热门股")
            hot_stocks = self.kaipanla_client.get_ths_hot_rank(max_rank=max_rank)
            if not hot_stocks.empty:
                logger.info(f"kaipanla 成功获取 {len(hot_stocks)} 只热门股")
                return hot_stocks
            else:
                logger.warning("kaipanla 返回空数据")
        except Exception as e:
            logger.warning(f"kaipanla 获取失败: {e}")
        
        # 策略3: 回退到问财（如果配置启用）
        if self.wencai_fallback and self.wencai_client:
            try:
                logger.info("使用问财获取热门股（回退模式）")
                hot_stocks = self.wencai_client.get_hot_stocks_simple(
                    max_rank=max_rank,
                    date=date
                )
                if not hot_stocks.empty:
                    logger.info(f"问财成功获取 {len(hot_stocks)} 只热门股（回退）")
                    return hot_stocks
            except Exception as e:
                logger.error(f"问财回退也失败: {e}")
        
        # 所有策略都失败
        logger.error("所有数据源都无法获取热门股数据")
        return pd.Series()
    
    def identify_recognition_stocks(self, date: str, plate_id: str = "801225") -> List[Stock]:
        """识别辨识度个股
        
        辨识度个股定义（简化版）：
        - 直接使用同花顺热门股排行榜前20名作为辨识度个股
        - 这些个股具有高市场关注度和流动性
        - 可选：结合技术支撑位作为补充筛选条件
        
        Args:
            date: 分析日期，格式：YYYY-MM-DD
            plate_id: 板块ID（保留参数，暂未使用）
            
        Returns:
            List[Stock]: 辨识度个股列表
        """
        logger.info(f"识别辨识度个股: {date}")
        
        try:
            # 获取同花顺热股前20名作为辨识度个股（使用新的多数据源方法）
            ths_hot_stocks = self._get_hot_stocks(max_rank=20, date=date)
            
            if ths_hot_stocks.empty:
                logger.warning(f"未获取到同花顺热股数据")
                return []
            
            logger.info(f"获取到{len(ths_hot_stocks)}只同花顺热股")
            
            recognition_stocks = []
            
            # 直接使用热股名称创建Stock对象
            # 注意：由于没有详细的市场数据，这里只能创建基础的Stock对象
            for rank, stock_name in ths_hot_stocks.items():
                stock = Stock(
                    code="",  # 暂时没有代码
                    name=stock_name,
                    market_cap=0.0,
                    price=0.0,
                    change_pct=0.0,
                    volume=0.0,
                    amount=0.0,
                    turnover_rate=0.0,
                    board_height=0,
                    themes=[],
                    technical_levels=None
                )
                # 添加自定义属性
                stock.is_recognition_stock = True
                stock.hot_rank = int(rank)  # 保存热度排名
                recognition_stocks.append(stock)
                logger.debug(f"识别到辨识度个股: {stock_name} (排名: {rank})")
            
            logger.info(f"找到 {len(recognition_stocks)} 只辨识度个股")
            return recognition_stocks
            
        except Exception as e:
            logger.error(f"识别辨识度个股失败: {e}")
            return []
    
    def identify_trend_stocks(self, date: str) -> List[Stock]:
        """识别趋势股
        
        趋势股定义：
        - 近期沿均线上涨的个股
        - 必须出现在同花顺热股前20
        - 价格在5日均线之上
        - 均线呈多头排列（MA5 > MA10 > MA20）
        
        Args:
            date: 分析日期，格式：YYYY-MM-DD
            
        Returns:
            List[Stock]: 趋势股列表
        """
        logger.info(f"识别趋势股: {date}")
        
        try:
            # 1. 获取同花顺热股前20（使用新的多数据源方法）
            ths_hot_stocks = self._get_hot_stocks(max_rank=20, date=date)
            
            if ths_hot_stocks.empty:
                logger.warning(f"未获取到同花顺热股数据")
                return []
            
            logger.info(f"获取到{len(ths_hot_stocks)}只同花顺热股")
            
            # 2. 遍历热股，获取历史数据并判断趋势
            trend_stocks = []
            
            for rank, stock_name in ths_hot_stocks.items():
                try:
                    # 创建基础Stock对象
                    stock = Stock(
                        code="",  # 暂时没有代码
                        name=stock_name,
                        market_cap=0.0,
                        price=0.0,
                        change_pct=0.0,
                        volume=0.0,
                        amount=0.0,
                        turnover_rate=0.0,
                        board_height=0,
                        themes=[],
                        technical_levels=None
                    )
                    
                    # 判断是否为趋势股（需要获取历史数据）
                    if self._is_trend_stock(stock, date):
                        stock.is_trend_stock = True
                        stock.hot_rank = int(rank)
                        trend_stocks.append(stock)
                        logger.debug(f"识别到趋势股: {stock_name} (排名: {rank})")
                        
                except Exception as e:
                    logger.warning(f"处理热股 {stock_name} 失败: {e}")
                    continue
            
            logger.info(f"找到 {len(trend_stocks)} 只趋势股")
            return trend_stocks
            
        except Exception as e:
            logger.error(f"识别趋势股失败: {e}")
            return []
    
    def build_gene_pool(self, date: str) -> GenePool:
        """构建基因池
        
        Args:
            date: 分析日期，格式：YYYY-MM-DD
            
        Returns:
            GenePool: 基因池对象
        """
        logger.info(f"构建基因池: {date}")
        
        try:
            # 扫描各类个股
            continuous_limit_up = self.scan_continuous_limit_up(date)
            failed_limit_up = self.identify_failed_limit_up(date)
            recognition_stocks = self.identify_recognition_stocks(date)
            
            # 构建all_stocks字典（去重）
            all_stocks = {}
            for stock in continuous_limit_up + failed_limit_up + recognition_stocks:
                if stock.code and stock.code not in all_stocks:
                    all_stocks[stock.code] = stock
            
            # 从all_stocks中识别趋势股（这些股票已经有技术位数据）
            trend_stocks = []
            for stock_code, stock in all_stocks.items():
                if self._is_trend_stock(stock, date):
                    stock.is_trend_stock = True
                    trend_stocks.append(stock)
                    logger.debug(f"识别到趋势股: {stock.code} {stock.name}")
            
            logger.info(f"从基因池中识别到 {len(trend_stocks)} 只趋势股")
            
            # 创建基因池对象
            gene_pool = GenePool(
                date=date,
                continuous_limit_up=continuous_limit_up,
                failed_limit_up=failed_limit_up,
                recognition_stocks=recognition_stocks,
                trend_stocks=trend_stocks,
                all_stocks=all_stocks
            )
            
            logger.info(f"基因池构建完成，共 {len(all_stocks)} 只个股")
            return gene_pool
            
        except Exception as e:
            logger.error(f"构建基因池失败: {e}")
            # 返回空基因池
            return GenePool(
                date=date,
                continuous_limit_up=[],
                failed_limit_up=[],
                recognition_stocks=[],
                trend_stocks=[],
                all_stocks={}
            )
    
    def _create_stock_from_row(self, row: pd.Series, date: str) -> Optional[Stock]:
        """从DataFrame行创建Stock对象
        
        Args:
            row: DataFrame行
            date: 日期
            
        Returns:
            Stock: 个股对象，如果创建失败返回None
        """
        try:
            # 提取基础信息（支持中英文列名）
            code = str(row.get('代码', row.get('股票代码', row.get('stock_code', ''))))
            name = str(row.get('名称', row.get('股票名称', row.get('stock_name', ''))))
            
            if not code or not name or code == '' or name == '':
                logger.warning(f"个股代码或名称缺失: {row.to_dict()}")
                return None
            
            # 提取数值字段（处理可能的缺失值）
            market_cap_val = row.get('流通市值', row.get('市值', 0))
            market_cap = float(market_cap_val) / 10000 if market_cap_val else 0.0  # 转换为亿元
            
            price_val = row.get('最新价', row.get('收盘价', row.get('price', 0)))
            price = float(price_val) if price_val else 0.0
            
            change_pct_val = row.get('涨跌幅', row.get('change_pct', 0))
            change_pct = float(change_pct_val) if change_pct_val else 0.0
            
            volume_val = row.get('成交量', row.get('volume', 0))
            volume = float(volume_val) if volume_val else 0.0
            
            amount_val = row.get('成交额', row.get('amount', 0))
            amount = float(amount_val) if amount_val else 0.0  # 单位：万元
            
            turnover_rate_val = row.get('换手率', row.get('turnover_rate', 0))
            turnover_rate = float(turnover_rate_val) if turnover_rate_val else 0.0
            
            board_height_val = row.get('连板天数', row.get('连板高度', row.get('consecutive_days', 0)))
            board_height = int(board_height_val) if board_height_val else 0
            
            # 提取题材信息
            themes = []
            theme_str = row.get('所属题材', row.get('板块', row.get('themes', '')))
            if theme_str and isinstance(theme_str, str):
                themes = [t.strip() for t in theme_str.split(',') if t.strip()]
            
            # 创建Stock对象
            stock = Stock(
                code=code,
                name=name,
                market_cap=market_cap,
                price=price,
                change_pct=change_pct,
                volume=volume,
                amount=amount,
                turnover_rate=turnover_rate,
                board_height=board_height,
                themes=themes,
                technical_levels=None  # 技术位稍后计算
            )
            
            logger.debug(f"创建Stock对象成功: {code} {name}, 连板{board_height}天")
            return stock
            
        except Exception as e:
            logger.error(f"创建Stock对象失败: {e}, row: {row.to_dict()}")
            return None
    
    def _is_at_support_level(self, stock: Stock, date: str) -> bool:
        """判断个股是否处于支撑位
        
        Args:
            stock: 个股对象
            date: 日期
            
        Returns:
            bool: True表示处于支撑位
        """
        try:
            # TODO: 实现支撑位判断逻辑
            # 这里先简单判断：价格距离5日均线在±3%以内
            # 实际实现需要获取历史数据并计算技术位
            
            # 暂时返回False，等待technical_calculator实现
            return False
            
        except Exception as e:
            logger.error(f"判断支撑位失败: {e}")
            return False
    
    def _is_trend_stock(self, stock: Stock, date: str) -> bool:
        """判断个股是否为趋势股
        
        趋势股判断标准（放宽版）：
        1. 价格在5日均线之上（距离MA5在0%到20%之间）- 放宽以适应强势股
        2. 均线呈多头排列（MA5 > MA10 > MA20）
        3. 价格有效（price > 0）
        
        Args:
            stock: 个股对象
            date: 日期
            
        Returns:
            bool: True表示为趋势股
        """
        try:
            # 检查价格是否有效
            if stock.price <= 0:
                logger.debug(f"个股 {stock.code} {stock.name} 价格无效: {stock.price}")
                return False
            
            # 由于stock.name可能没有对应的代码，暂时无法获取历史数据
            # 这里简化处理：如果stock有技术位数据，则使用技术位判断
            if stock.technical_levels:
                # 检查是否在均线之上
                ma5_distance = stock.technical_levels.ma5_distance_pct
                ma10_distance = stock.technical_levels.ma10_distance_pct
                ma20_distance = stock.technical_levels.ma20_distance_pct
                
                # 获取均线值用于判断多头排列
                ma5 = stock.technical_levels.ma5
                ma10 = stock.technical_levels.ma10
                ma20 = stock.technical_levels.ma20
                
                # 判断条件：
                # 1. 价格在MA5之上（距离0%-20%）- 放宽阈值以适应强势股
                # 2. MA5 > MA10 > MA20（多头排列）
                if (0 <= ma5_distance <= 20 and 
                    ma5 > ma10 and 
                    ma10 > ma20):
                    logger.debug(f"个股 {stock.code} {stock.name} 符合趋势特征: "
                               f"MA5={ma5_distance:.2f}%, MA10={ma10_distance:.2f}%, MA20={ma20_distance:.2f}%, "
                               f"多头排列: MA5({ma5:.2f}) > MA10({ma10:.2f}) > MA20({ma20:.2f})")
                    return True
                else:
                    logger.debug(f"个股 {stock.code} {stock.name} 不符合趋势特征: "
                               f"MA5距离={ma5_distance:.2f}% (需要0-20%), "
                               f"多头排列: MA5({ma5:.2f}) > MA10({ma10:.2f}) > MA20({ma20:.2f}) = {ma5 > ma10 and ma10 > ma20}")
            
            # 如果没有技术位数据，暂时返回False
            return False
            
        except Exception as e:
            logger.error(f"判断趋势股失败: {e}")
            return False
    
    def _enrich_stock_with_intraday_data(self, stock: Stock, date: str) -> Stock:
        """为个股补充分时数据中的量价信息
        
        Args:
            stock: 个股对象
            date: 日期，格式：YYYY-MM-DD
            
        Returns:
            Stock: 补充了量价数据的个股对象
        """
        try:
            # 调用kaipanla_client获取个股分时数据
            intraday_data = self.kaipanla_client.get_stock_intraday(stock.code, date)
            
            if not intraday_data or 'data' not in intraday_data:
                logger.warning(f"未获取到个股 {stock.code} {stock.name} 的分时数据")
                return stock
            
            # 从分时数据中提取量价信息
            df = intraday_data['data']
            
            # 更新价格信息
            if 'hprice' in intraday_data and intraday_data['hprice']:
                stock.price = float(intraday_data['hprice'])  # 使用最高价（连板股通常收盘在涨停价）
            
            # 更新涨跌幅
            if 'px_change_rate' in intraday_data and intraday_data['px_change_rate']:
                stock.change_pct = float(intraday_data['px_change_rate'])
            
            # 更新成交量（从分时数据累加）
            if not df.empty and 'volume' in df.columns:
                stock.volume = float(df['volume'].sum())  # 单位：手
            
            # 更新成交额
            if 'total_turnover' in intraday_data and intraday_data['total_turnover']:
                stock.amount = float(intraday_data['total_turnover']) / 10000  # 转换为万元
            elif not df.empty and 'turnover' in df.columns:
                # 如果total_turnover不可用，从分时数据累加
                stock.amount = float(df['turnover'].sum()) / 10000  # 转换为万元
            
            # 换手率需要流通市值，暂时无法计算
            # stock.turnover_rate = 0.0
            
            logger.debug(f"补充个股 {stock.code} {stock.name} 量价数据: "
                        f"价格={stock.price:.2f}, 涨幅={stock.change_pct:.2f}%, "
                        f"成交量={stock.volume:.0f}手, 成交额={stock.amount:.2f}万")
            
            return stock
            
        except Exception as e:
            logger.warning(f"补充个股 {stock.code} {stock.name} 量价数据失败: {e}")
            return stock
