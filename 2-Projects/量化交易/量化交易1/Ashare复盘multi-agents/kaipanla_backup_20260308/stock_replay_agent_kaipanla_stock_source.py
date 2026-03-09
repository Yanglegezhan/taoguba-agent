"""
开盘啦数据源 - 核心个股复盘专用

封装 KaipanlaCrawler，提供核心个股复盘所需的数据接口
"""
import sys
import time
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

# 导入项目根路径以便导入外部模块
project_root = Path(__file__).resolve().parents[4]
kaipanla_crawler_path = project_root / "kaipanla_crawler"
if str(kaipanla_crawler_path) not in sys.path:
    sys.path.insert(0, str(kaipanla_crawler_path))

try:
    from kaipanla_crawler import KaipanlaCrawler
except ImportError:
    # 如果导入失败，尝试直接导入
    sys.path.insert(0, str(project_root))
    try:
        from kaipanla_crawler.kaipanla_crawler import KaipanlaCrawler
    except ImportError:
        raise ImportError(
            "无法导入 KaipanlaCrawler。请确保 kaipanla_crawler 目录在项目根目录下。"
        )


class KaipanlaStockSource:
    """
    开盘啦数据源 - 核心个股复盘专用

    主要接口：
    - get_consecutive_limit_up(date) - 获取连板梯队数据
    - get_realtime_all_boards_stocks() - 获取所有涨停板个股
    - get_stock_intraday(stock_code, date) - 获取个股分时数据
    - get_index_intraday(index_code, date) - 获取大盘指数分时
    - get_realtime_sharp_withdrawal() - 获取大幅回撤数据
    """

    def __init__(
        self,
        request_delay: float = 0.5,
        max_retries: int = 3,
        enable_cache: bool = True,
        cache: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化数据源

        Args:
            request_delay: 请求延迟（秒），避免被限流
            max_retries: 最大重试次数
            enable_cache: 是否启用缓存
            cache: 缓存字典（可选）
        """
        self.crawler = KaipanlaCrawler()
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.enable_cache = enable_cache
        self.cache = cache if cache is not None else {}
        self.cache_ttl = 3600  # 缓存有效期1小时
        self.cache_timestamps: Dict[str, float] = {}

    def _get_cache_key(self, method: str, *args) -> str:
        """生成缓存键"""
        return f"{method}:{str(args)}"

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self.enable_cache:
            return None

        if key not in self.cache:
            return None

        # 检查缓存是否过期
        cache_time = self.cache_timestamps.get(key, 0)
        if time.time() - cache_time > self.cache_ttl:
            del self.cache[key]
            del self.cache_timestamps[key]
            return None

        return self.cache[key]

    def _save_to_cache(self, key: str, data: Any) -> None:
        """保存数据到缓存"""
        if not self.enable_cache:
            return

        self.cache[key] = data
        self.cache_timestamps[key] = time.time()

    def _retry_request(self, func, *args, **kwargs) -> Any:
        """
        带重试机制的请求

        Args:
            func: 请求函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            请求结果
        """
        last_error = None
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                time.sleep(self.request_delay)
                return result
            except Exception as e:
                last_error = e
                print(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 指数退避
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

        print(f"请求重试 {self.max_retries} 次后失败: {last_error}")
        return None

    def get_consecutive_limit_up(
        self, date: Optional[str] = None, timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取指定日期的连板梯队情况

        Args:
            date: 日期，格式YYYY-MM-DD，默认为当前日期
            timeout: 超时时间（秒）

        Returns:
            dict: 包含连板梯队信息
                - date: 日期
                - max_consecutive: 最高连板高度
                - max_consecutive_stocks: 最高连板个股名称（多个用/分隔）
                - max_consecutive_concepts: 最高连板个股题材（多个用/分隔）
                - ladder: 连板梯队详细数据
                    - 2: 二连板股票列表
                    - 3: 三连板股票列表
                    - 4: 四连板股票列表
                    - ...
                - max_consecutive_stocks_list: 最高连板股票详情列表
                - ladder_details: 连板梯队股票详情

        示例:
            source = KaipanlaStockSource()
            data = source.get_consecutive_limit_up("2026-01-19")
            print(f"最高板: {data['max_consecutive']}连板")
            print(f"最高板个股: {data['max_consecutive_stocks']}")
        """
        cache_key = self._get_cache_key("consecutive_limit_up", date)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            print("使用缓存的连板梯队数据")
            return cached_data

        result = self._retry_request(self.crawler.get_consecutive_limit_up, date, timeout=timeout)

        if result:
            # 添加一些额外字段便于使用
            ladder = result.get("ladder", {})

            # 提取最高板股票详情
            max_consecutive = result.get("max_consecutive", 0)
            max_consecutive_stocks_list = ladder.get(max_consecutive, []) if max_consecutive > 0 else []

            # 构建详细信息
            result["max_consecutive_stocks_list"] = max_consecutive_stocks_list

            # 构建阶梯详情，方便迭代
            ladder_details = {}
            for days, stocks in ladder.items():
                ladder_details[days] = [
                    {
                        "stock_code": s.get("股票代码", ""),
                        "stock_name": s.get("股票名称", ""),
                        "consecutive_days": s.get("连板天数", days),
                        "concepts": self._parse_concepts(
                            s.get("题材", ""), s.get("概念", "")
                        ),
                    }
                    for s in stocks
                ]
            result["ladder_details"] = ladder_details

            self._save_to_cache(cache_key, result)

        return result or {}

    def _parse_concepts(self, sector: str, concept: str) -> List[str]:
        """
        解析题材和概念，返回去重的概念列表

        Args:
            sector: 题材字符串
            concept: 概念字符串

        Returns:
            去重的概念列表
        """
        all_concepts = []

        # 解析题材
        if sector:
            concepts = [c.strip() for c in sector.replace("/", "、").split("、") if c.strip()]
            all_concepts.extend(concepts)

        # 解析概念
        if concept:
            concepts = [c.strip() for c in concept.replace("/", "、").split("、") if c.strip()]
            all_concepts.extend(concepts)

        # 去重但保持顺序
        unique_concepts = []
        seen = set()
        for c in all_concepts:
            if c not in seen:
                unique_concepts.append(c)
                seen.add(c)

        return unique_concepts

    def get_realtime_all_boards_stocks(
        self, timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取实时所有连板的股票列表（首板到五板以上）

        Args:
            timeout: 超时时间（秒）

        Returns:
            dict: 包含各连板的股票列表
                - first_board: 首板股票列表
                - second_board: 二板股票列表
                - third_board: 三板股票列表
                - fourth_board: 四板股票列表
                - fifth_board_plus: 五板及以上股票列表
                - statistics: 统计信息

        示例:
            source = KaipanlaStockSource()
            data = source.get_realtime_all_boards_stocks()
            print(f"首板: {len(data['first_board'])}只")
        """
        cache_key = self._get_cache_key("realtime_all_boards_stocks")
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            print("使用缓存的实时涨停板数据")
            return cached_data

        result = self._retry_request(
            self.crawler.get_realtime_all_boards_stocks, timeout=timeout
        )

        if result:
            self._save_to_cache(cache_key, result)

        return result or {}

    def get_stock_intraday(
        self, stock_code: str, date: Optional[str] = None, timeout: Optional[int] = 300
    ) -> Dict[str, Any]:
        """
        获取个股分时数据

        Args:
            stock_code: 股票代码，如 "002498" 或 "sh.600000"
            date: 日期，格式YYYY-MM-DD，默认为None（获取实时数据）
            timeout: 超时时间（秒）

        Returns:
            dict: 包含个股分时数据
                - stock_code: 股票代码
                - date: 日期
                - total_main_inflow: 主力净流入总额（元）
                - total_main_outflow: 主力净流出总额（元）
                - data: DataFrame，包含分时数据
                    - time: 时间（HH:MM格式）
                    - price: 价格
                    - avg_price: 均价
                    - volume: 成交量（手）
                    - turnover: 成交额（元）
                    - main_net_inflow: 主力净流入（元）
                    - flag: 价格标志

        示例:
            source = KaipanlaStockSource()
            data = source.get_stock_intraday("002498", "2026-01-16")
            df = data['data']
            print(f"总成交量: {df['volume'].sum():,} 手")
        """
        # 统一股票代码格式
        stock_code = self._normalize_stock_code(stock_code)

        cache_key = self._get_cache_key("stock_intraday", stock_code, date)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            print(f"使用缓存的个股分时数据: {stock_code}")
            return cached_data

        result = self._retry_request(
            self.crawler.get_stock_intraday, stock_code, date, timeout=timeout
        )

        if result:
            self._save_to_cache(cache_key, result)

        return result or {}

    def _normalize_stock_code(self, stock_code: str) -> str:
        """
        标准化股票代码格式

        将 "sh.600000" 格式转换为 "600000" 格式
        或将 "600000" 格式转换为 "SH600000" 格式（如需要）

        Args:
            stock_code: 股票代码

        Returns:
            标准化后的股票代码
        """
        if "." in stock_code:
            # "sh.600000" -> "600000"
            parts = stock_code.split(".")
            return parts[-1]
        elif len(stock_code) == 6:
            # "600000" -> "600000" (保持不变，用于API)
            return stock_code
        elif stock_code.startswith(("SH", "SZ")):
            # "SH600000" -> "600000"
            return stock_code[2:]

        return stock_code

    def get_index_intraday(
        self,
        index_code: str = "SH000001",
        date: Optional[str] = None,
        timeout: Optional[int] = 300,
    ) -> Dict[str, Any]:
        """
        获取大盘指数分时数据

        Args:
            index_code: 指数代码，默认"SH000001"（上证指数）
                       - SH000001: 上证指数
                       - SZ399001: 深证成指
                       - SZ399006: 创业板指
                       - SH000300: 沪深300
            date: 日期，格式YYYY-MM-DD，默认为None（获取实时数据）
            timeout: 超时时间（秒）

        Returns:
            dict: 包含指数分时数据
                - index_code: 指数代码
                - index_name: 指数名称
                - date: 日期
                - open: 开盘价
                - close: 收盘价
                - high: 最高价
                - low: 最低价
                - preclose: 昨收价
                - change_pct: 涨跌幅（%）
                - data: DataFrame，包含分时数据

        示例:
            source = KaipanlaStockSource()
            data = source.get_index_intraday("SH000001", "2026-01-20")
            print(f"涨跌幅: {data['change_pct']:.2f}%")
        """
        cache_key = self._get_cache_key("index_intraday", index_code, date)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            print(f"使用缓存的指数分时数据: {index_code}")
            return cached_data

        result = self._retry_request(
            self.crawler.get_index_intraday, index_code, date, timeout=timeout
        )

        if result:
            self._save_to_cache(cache_key, result)

        return result or {}

    def get_realtime_sharp_withdrawal(
        self, timeout: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取大幅回撤股票数据（实时）

        Args:
            timeout: 超时时间（秒）

        Returns:
            list: 大幅回撤股票列表
                - 日期: 日期
                - 股票代码: 股票代码
                - 股票名称: 股票名称
                - 当日涨跌幅(%): 当日涨跌幅
                - 回撤幅度(%): 回撤幅度
                - 最新价: 最新价
                - 总数: 总数

        示例:
            source = KaipanlaStockSource()
            data = source.get_realtime_sharp_withdrawal()
            print(f"大幅回撤家数: {len(data)}")
        """
        cache_key = self._get_cache_key("realtime_sharp_withdrawal")
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            print("使用缓存的大幅回撤数据")
            return cached_data

        result = self._retry_request(
            self.crawler.get_realtime_sharp_withdrawal, timeout=timeout
        )

        if result is not None and hasattr(result, "to_dict"):
            # 如果是DataFrame，转换为列表
            result = result.to_dict("records")

        if result:
            self._save_to_cache(cache_key, result)

        return result or []

    def get_daily_data(
        self, end_date: str, start_date: Optional[str] = None
    ) -> Any:
        """
        获取交易日数据

        Args:
            end_date: 结束日期，格式YYYY-MM-DD
            start_date: 起始日期，格式YYYY-MM-DD，可选

        Returns:
            - 只传end_date: 返回Series（单日数据）
            - 传start_date和end_date: 返回DataFrame（日期范围数据）
        """
        cache_key = self._get_cache_key("daily_data", end_date, start_date)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            print("使用缓存的每日数据")
            return cached_data

        result = self._retry_request(
            self.crawler.get_daily_data, end_date, start_date
        )

        if result:
            self._save_to_cache(cache_key, result)

        return result

    def get_new_high_data(
        self,
        end_date: str,
        start_date: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Any:
        """
        获取百日新高数据

        Args:
            end_date: 结束日期
            start_date: 开始日期，可选
            timeout: 超时时间

        Returns:
            DataFrame
        """
        cache_key = self._get_cache_key("new_high_data", end_date, start_date)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            print("使用缓存的百日新高数据")
            return cached_data

        result = self._retry_request(
            self.crawler.get_new_high_data, end_date, start_date, timeout=timeout
        )

        if result:
            self._save_to_cache(cache_key, result)

        return result

    def get_market_sentiment(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取市场情绪数据

        Args:
            date: 日期

        Returns:
            市场情绪数据
        """
        cache_key = self._get_cache_key("market_sentiment", date)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            print("使用缓存的市场情绪数据")
            return cached_data

        result = self._retry_request(self.crawler.get_market_sentiment, date)

        if result:
            self._save_to_cache(cache_key, result)

        return result or {}

    def get_market_index(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取市场指数数据

        Args:
            date: 日期

        Returns:
            指数数据
        """
        cache_key = self._get_cache_key("market_index", date)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            print("使用缓存的市场指数数据")
            return cached_data

        result = self._retry_request(self.crawler.get_market_index, date)

        if result:
            self._save_to_cache(cache_key, result)

        return result or {}

    def get_limit_up_ladder(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取涨停梯队数据

        Args:
            date: 日期

        Returns:
            涨停梯队数据
        """
        cache_key = self._get_cache_key("limit_up_ladder", date)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            print("使用缓存的涨停梯队数据")
            return cached_data

        result = self._retry_request(self.crawler.get_limit_up_ladder, date)

        if result:
            self._save_to_cache(cache_key, result)

        return result or {}

    def get_sharp_withdrawal(self, date: Optional[str] = None) -> pd.DataFrame:
        """
        获取大幅回撤数据

        Args:
            date: 日期

        Returns:
            DataFrame
        """
        cache_key = self._get_cache_key("sharp_withdrawal", date)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            print("使用缓存的大幅回撤数据")
            return cached_data

        result = self._retry_request(self.crawler.get_sharp_withdrawal, date)

        if result:
            self._save_to_cache(cache_key, result)

        return result if result is not None else pd.DataFrame()

    def get_sector_ranking(
        self, date: Optional[str] = None, index: int = 0, timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取涨停原因板块数据

        Args:
            date: 日期
            index: 索引
            timeout: 超时时间

        Returns:
            板块排名数据
        """
        cache_key = self._get_cache_key("sector_ranking", date, index)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            print("使用缓存的板块排名数据")
            return cached_data

        result = self._retry_request(
            self.crawler.get_sector_ranking, date, index, timeout=timeout
        )

        if result:
            self._save_to_cache(cache_key, result)

        return result or {}

    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.cache_timestamps.clear()
        print("缓存已清空")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_enabled": self.enable_cache,
            "cache_size": len(self.cache),
            "cache_keys": list(self.cache.keys()),
        }


def verify_data_source() -> None:
    """
    验证数据源接口

    输出各接口的返回结果，用于调试和验证
    """
    print("=" * 60)
    print("数据源接口验证")
    print("=" * 60)

    source = KaipanlaStockSource()

    # 1. 测试连板数据
    print("\n1. 测试 get_consecutive_limit_up()")
    print("-" * 60)
    consecutive_data = source.get_consecutive_limit_up(date="2026-01-19")
    print(f"返回结果: {consecutive_data}")

    # 2. 测试实时涨停板
    print("\n2. 测试 get_realtime_all_boards_stocks()")
    print("-" * 60)
    realtime_boards = source.get_realtime_all_boards_stocks()
    if realtime_boards:
        stats = realtime_boards.get("statistics", {})
        print(f"统计信息: {stats}")
        print(f"首板数量: {stats.get('first_board_count', 0)}")
        print(f"二板数量: {stats.get('second_board_count', 0)}")

    # 3. 测试个股分时
    print("\n3. 测试 get_stock_intraday()")
    print("-" * 60)
    stock_intraday = source.get_stock_intraday("002498", date="2026-01-16")
    print(f"返回结果类型: {type(stock_intraday)}")
    if stock_intraday:
        print(f"股票代码: {stock_intraday.get('stock_code')}")
        print(f"日期: {stock_intraday.get('date')}")
        df = stock_intraday.get("data")
        if df is not None and not df.empty:
            print(f"分时数据条数: {len(df)}")
            print(f"分时数据列: {list(df.columns)}")
            print(f"前5条数据:\n{df.head()}")

    # 4. 测试大盘分时
    print("\n4. 测试 get_index_intraday()")
    print("-" * 60)
    index_intraday = source.get_index_intraday("SH000001", date="2026-01-20")
    print(f"返回结果类型: {type(index_intraday)}")
    if index_intraday:
        print(f"指数代码: {index_intraday.get('index_code')}")
        print(f"指数名称: {index_intraday.get('index_name')}")
        print(f"涨跌幅: {index_intraday.get('change_pct')}%")
        df = index_intraday.get("data")
        if df is not None and not df.empty:
            print(f"分时数据条数: {len(df)}")

    # 5. 测试大幅回撤
    print("\n5. 测试 get_realtime_sharp_withdrawal()")
    print("-" * 60)
    sharp_withdrawal = source.get_realtime_sharp_withdrawal()
    print(f"返回结果类型: {type(sharp_withdrawal)}")
    print(f"大幅回撤家数: {len(sharp_withdrawal)}")
    if sharp_withdrawal and len(sharp_withdrawal) > 0:
        print(f"前3条数据: {sharp_withdrawal[:3]}")

    # 6. 缓存统计
    print("\n6. 缓存统计")
    print("-" * 60)
    cache_stats = source.get_cache_stats()
    print(f"缓存启用: {cache_stats['cache_enabled']}")
    print(f"缓存大小: {cache_stats['cache_size']}")
    print(f"缓存键: {cache_stats['cache_keys']}")

    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)


if __name__ == "__main__":
    verify_data_source()
