# -*- coding: utf-8 -*-
"""
开盘啦数据源 - 获取涨停个股列表
"""

import sys
import logging
from typing import List, Dict, Any
from pathlib import Path

# 添加 kaipanla_crawler 到路径
kaipanla_path = Path(__file__).parent.parent.parent.parent.parent / 'kaipanla_crawler'
if str(kaipanla_path) not in sys.path:
    sys.path.insert(0, str(kaipanla_path))

try:
    from kaipanla_crawler import KaipanlaCrawler
except ImportError as e:
    logging.warning(f'无法导入 kaipanla_crawler: {e}')
    KaipanlaCrawler = None

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logging.warning('AKShare 不可用，历史数据将使用开盘啦接口（仅连板）')


class KaipanlaSource:
    """开盘啦数据源 - 获取涨停个股列表"""

    def __init__(self, config_or_params, max_retries: int = 3, timeout: int = 60):
        """
        初始化数据源
        
        Args:
            config_or_params: ConfigManager对象 或 直接传入参数
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
        """
        if KaipanlaCrawler is None:
            raise ImportError('kaipanla_crawler 不可用，请确保已正确安装')

        # 兼容两种初始化方式
        if hasattr(config_or_params, 'get_data_source_config'):
            # 传入config对象
            data_source_config = config_or_params.get_data_source_config()
            max_retries = data_source_config.kaipanla_max_retries
            timeout = data_source_config.kaipanla_timeout

        self.crawler = KaipanlaCrawler()
        self.max_retries = max_retries
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    def get_limit_up_stocks(self, date: str) -> List[Dict[str, Any]]:
        """
        智能获取涨停个股列表
        
        优先使用 AKShare 获取完整数据（包括首板和连板）
        如果 AKShare 失败，降级到开盘啦接口
        """
        from datetime import datetime
        
        # 优先使用 AKShare 获取完整数据
        if AKSHARE_AVAILABLE:
            try:
                self.logger.info(f'使用 AKShare 获取 {date} 的完整涨停数据...')
                stocks = self._get_limit_up_stocks_from_akshare(date)
                if stocks:
                    self.logger.info(f'✓ AKShare 获取到 {len(stocks)} 只涨停股票（完整数据）')
                    return stocks
                else:
                    self.logger.warning('AKShare 未获取到数据，降级到开盘啦接口')
            except Exception as e:
                self.logger.warning(f'AKShare 获取失败: {e}，降级到开盘啦接口')
        
        # 降级到开盘啦接口
        today = datetime.now().strftime("%Y-%m-%d")
        
        if date == today:
            # 今天：使用实时接口获取完整数据
            self.logger.info(f'检测到查询今日数据 ({date})，使用开盘啦实时接口...')
            return self._get_limit_up_stocks_realtime()
        else:
            # 历史：使用历史接口（连板数据）
            self.logger.info(f'查询历史数据 ({date})，使用开盘啦历史接口（仅连板股票）...')
            return self._get_limit_up_stocks_historical(date)
    
    def _get_limit_up_stocks_from_akshare(self, date: str) -> List[Dict[str, Any]]:
        """
        使用 AKShare 获取完整涨停数据（包括首板和连板）
        
        Args:
            date: 日期，格式 YYYY-MM-DD
            
        Returns:
            涨停股票列表
        """
        try:
            # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
            date_str = date.replace('-', '')
            
            # 使用 AKShare 的东方财富涨停股池接口
            df = ak.stock_zt_pool_em(date=date_str)
            
            if df is None or df.empty:
                self.logger.warning(f'AKShare 未获取到 {date} 的涨停数据')
                return []
            
            stocks = []
            for _, row in df.iterrows():
                # 标准化股票代码
                stock_code = str(row['代码'])
                if len(stock_code) == 6:
                    if stock_code.startswith('6'):
                        stock_code = f'{stock_code}.SH'
                    elif stock_code.startswith(('0', '3')):
                        stock_code = f'{stock_code}.SZ'
                
                # 解析首次封板时间（格式：HHMMSS）
                limit_up_time = ''
                if '首次封板时间' in row and row['首次封板时间']:
                    time_str = str(row['首次封板时间'])
                    if len(time_str) >= 6:
                        limit_up_time = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                
                # 解析成交额（单位：元 -> 亿元）
                turnover = 0.0
                if '成交额' in row and row['成交额']:
                    try:
                        turnover = float(row['成交额']) / 100000000
                    except:
                        pass
                
                # 获取市值数据（单位：元 -> 亿元）
                total_market_cap = None
                circulating_market_cap = None
                if '总市值' in row and row['总市值']:
                    try:
                        total_market_cap = float(row['总市值']) / 100000000
                    except:
                        pass
                if '流通市值' in row and row['流通市值']:
                    try:
                        circulating_market_cap = float(row['流通市值']) / 100000000
                    except:
                        pass
                
                # 获取连板数
                consecutive_days = 0
                if '连板数' in row and row['连板数']:
                    try:
                        consecutive_days = int(row['连板数'])
                    except:
                        pass
                
                stock_info = {
                    'stock_code': stock_code,
                    'stock_name': str(row['名称']),
                    'limit_up_time': limit_up_time,
                    'consecutive_days': consecutive_days,
                    'turnover_amount': turnover,
                    'concepts': str(row.get('所属行业', '')),
                    'limit_up_reason': str(row.get('涨停统计', '')),
                    'price': float(row.get('最新价', 0)),
                    'total_market_cap': total_market_cap,
                    'circulating_market_cap': circulating_market_cap
                }
                
                stocks.append(stock_info)
            
            self.logger.info(f'AKShare 获取到 {len(stocks)} 只涨停股票')
            
            # 统计连板分布
            board_stats = {}
            for stock in stocks:
                board = stock['consecutive_days']
                board_stats[board] = board_stats.get(board, 0) + 1
            
            self.logger.info(f'连板分布: {dict(sorted(board_stats.items()))}')
            
            return stocks
            
        except Exception as e:
            self.logger.error(f'AKShare 获取涨停数据失败: {e}')
            import traceback
            traceback.print_exc()
            return []
    
    def _get_limit_up_stocks_realtime(self) -> List[Dict[str, Any]]:
        """获取今日所有涨停股票（实时数据，包括首板）"""
        try:
            all_stocks = []
            seen_codes = set()
            
            # 方法1: 使用实时板块数据（包含所有涨停股票）
            try:
                self.logger.info('使用实时板块接口获取涨停数据...')
                
                # 获取多页数据
                max_pages = 10
                for page in range(max_pages):
                    index = page * 100
                    
                    sector_data = self.crawler.get_sector_ranking(date=None, index=index, timeout=self.timeout)
                    
                    if not sector_data or not sector_data.get('sectors'):
                        break
                    
                    page_stocks = 0
                    for sector in sector_data['sectors']:
                        for stock in sector.get('stocks', []):
                            stock_code = stock.get('股票代码', '')
                            if not stock_code:
                                continue
                            
                            stock_code = self._normalize_stock_code(stock_code)
                            
                            if stock_code in seen_codes:
                                continue
                            
                            seen_codes.add(stock_code)
                            page_stocks += 1
                            
                            stock_info = {
                                'stock_code': stock_code,
                                'stock_name': stock.get('股票名称', ''),
                                'limit_up_time': stock.get('涨停时间', ''),
                                'consecutive_days': stock.get('连板天数', 0),
                                'turnover_amount': self._parse_turnover(stock.get('成交额', 0)),
                                'concepts': stock.get('概念标签', ''),
                                'limit_up_reason': stock.get('涨停原因', ''),
                                'price': stock.get('涨停价', 0)
                            }
                            
                            all_stocks.append(stock_info)
                    
                    if page_stocks == 0:
                        break
                
                if all_stocks:
                    self.logger.info(f'✓ 从实时板块接口获取到 {len(all_stocks)} 只涨停股票（完整数据）')
                    return all_stocks
                    
            except Exception as e:
                self.logger.warning(f'实时板块接口失败: {e}')
            
            # 方法2: 使用实时连板接口（逐板获取）
            try:
                self.logger.info('尝试使用实时连板接口...')
                
                # 获取所有板型的股票（1-10板）
                for board_type in range(1, 11):
                    try:
                        stocks = self.crawler.get_realtime_board_stocks(
                            board_type=board_type,
                            timeout=self.timeout
                        )
                        
                        if not stocks:
                            # 没有更高板了
                            break
                        
                        for stock in stocks:
                            stock_code = self._normalize_stock_code(stock.get('stock_code', ''))
                            
                            if not stock_code or stock_code in seen_codes:
                                continue
                            
                            seen_codes.add(stock_code)
                            
                            stock_info = {
                                'stock_code': stock_code,
                                'stock_name': stock.get('stock_name', ''),
                                'limit_up_time': stock.get('timestamp', ''),
                                'consecutive_days': stock.get('consecutive_days', board_type),
                                'turnover_amount': self._parse_turnover(stock.get('turnover', 0)),
                                'concepts': stock.get('concepts', ''),
                                'limit_up_reason': stock.get('limit_up_reason', ''),
                                'price': stock.get('limit_up_price', 0)
                            }
                            
                            all_stocks.append(stock_info)
                        
                        self.logger.info(f'  {board_type}板: {len(stocks)} 只')
                        
                    except Exception as e:
                        self.logger.debug(f'{board_type}板获取失败: {e}')
                        break
                
                if all_stocks:
                    self.logger.info(f'✓ 从实时连板接口获取到 {len(all_stocks)} 只涨停股票')
                    return all_stocks
                    
            except Exception as e:
                self.logger.warning(f'实时连板接口失败: {e}')
            
            # 方法3: 降级到实时梯队接口
            self.logger.info('尝试使用实时梯队接口...')
            return self._get_limit_up_stocks_from_ladder(date=None)
            
        except Exception as e:
            self.logger.error(f'获取实时涨停列表失败: {e}')
            import traceback
            traceback.print_exc()
            return []
    
    def _get_limit_up_stocks_historical(self, date: str) -> List[Dict[str, Any]]:
        """获取历史涨停股票（仅连板数据）"""
        try:
            self.logger.info(f'获取 {date} 的历史涨停数据（仅连板）...')
            return self._get_limit_up_stocks_from_ladder(date=date)
            
        except Exception as e:
            self.logger.error(f'获取历史涨停列表失败 ({date}): {e}')
            import traceback
            traceback.print_exc()
            return []
    
    def _get_limit_up_stocks_from_ladder(self, date: str = None) -> List[Dict[str, Any]]:
        """从连板梯队获取涨停股票"""
        all_stocks = []
        seen_codes = set()
        
        try:
            ladder_data = self.crawler.get_market_limit_up_ladder(date=date, timeout=self.timeout)

            if not ladder_data:
                self.logger.warning(f'未获取到涨停梯队数据')
                return []

            ladder_dict = ladder_data if isinstance(ladder_data, dict) else {}

            if 'ladder' in ladder_dict:
                ladder_items = ladder_dict['ladder']
            else:
                ladder_items = ladder_dict

            if not isinstance(ladder_items, dict):
                self.logger.warning(f'涨停梯队数据格式异常: {type(ladder_items)}')
                return []

            for board, stocks in ladder_items.items():
                if not isinstance(stocks, list):
                    continue

                consecutive = 0
                if isinstance(board, int):
                    consecutive = board
                elif isinstance(board, str) and board.isdigit():
                    consecutive = int(board)
                elif isinstance(board, str):
                    clean_board = board.replace('板', '')
                    if clean_board.isdigit():
                        consecutive = int(clean_board)

                for stock in stocks:
                    if not isinstance(stock, dict):
                        continue

                    stock_code = self._normalize_stock_code(stock.get('stock_code', ''))
                    
                    if not stock_code or stock_code in seen_codes:
                        continue
                    
                    seen_codes.add(stock_code)

                    stock_info = {
                        'stock_code': stock_code,
                        'stock_name': stock.get('stock_name', ''),
                        'limit_up_time': stock.get('first_limit_up_time', stock.get('limit_up_time', '')),
                        'consecutive_days': consecutive,
                        'turnover_amount': self._parse_turnover(stock.get('turnover', stock.get('turnover_amount', 0))),
                        'concepts': stock.get('concepts', stock.get('limit_up_reason', '')),
                        'limit_up_reason': stock.get('limit_up_reason', '')
                    }

                    all_stocks.append(stock_info)

            data_type = '实时' if date is None else '历史'
            self.logger.info(f'从{data_type}梯队获取到 {len(all_stocks)} 只涨停股票（仅连板）')
            
            return all_stocks
            
        except Exception as e:
            self.logger.error(f'从梯队获取涨停股票失败: {e}')
            return []

    def _normalize_stock_code(self, code: str) -> str:
        """标准化股票代码格式为 XXXXXX.SH 或 XXXXXX.SZ"""
        if not code:
            return code

        for suffix in ['.SH', '.SZ', '.sh', '.sz']:
            if isinstance(code, str) and code.endswith(suffix):
                code = code[:-3]
                break

        if isinstance(code, str) and len(code) == 6:
            if code.startswith('6'):
                return f'{code}.SH'
            elif code.startswith(('0', '3')):
                return f'{code}.SZ'

        return code

    def _parse_turnover(self, turnover: Any) -> float:
        """解析成交额为亿元"""
        if turnover is None:
            return 0.0

        if isinstance(turnover, (int, float)):
            return turnover / 100000000

        if isinstance(turnover, str):
            turnover = turnover.replace(',', '')
            try:
                value = float(turnover)
                if value > 100000000:
                    return value / 100000000
                return value
            except ValueError:
                return 0.0

        return 0.0
