"""
技术指标计算器

职责：
- 计算个股的5日、10日、20日均线
- 识别前期高点
- 计算筹码密集区
- 计算距离百分比
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..common.logger import get_logger
from ..common.models import Stock, TechnicalLevels

logger = get_logger(__name__)


class TechnicalCalculator:
    """技术指标计算器
    
    职责：
    - 计算移动平均线（MA5, MA10, MA20）
    - 识别前期高点
    - 计算筹码密集区
    - 计算距离百分比
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化技术指标计算器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        logger.info("技术指标计算器初始化完成")
    
    def calculate_moving_averages(
        self, 
        stock: Stock,
        price_history: List[float]
    ) -> Dict[str, float]:
        """计算移动平均线
        
        Args:
            stock: 个股对象
            price_history: 历史价格列表（从旧到新）
            
        Returns:
            Dict: 包含ma5, ma10, ma20的字典
        """
        logger.debug(f"计算移动平均线: {stock.code}")
        
        if not price_history:
            logger.warning(f"价格历史为空: {stock.code}")
            return {"ma5": 0.0, "ma10": 0.0, "ma20": 0.0}
        
        result = {}
        
        # 计算MA5
        if len(price_history) >= 5:
            result["ma5"] = sum(price_history[-5:]) / 5
        else:
            result["ma5"] = sum(price_history) / len(price_history)
        
        # 计算MA10
        if len(price_history) >= 10:
            result["ma10"] = sum(price_history[-10:]) / 10
        else:
            result["ma10"] = sum(price_history) / len(price_history)
        
        # 计算MA20
        if len(price_history) >= 20:
            result["ma20"] = sum(price_history[-20:]) / 20
        else:
            result["ma20"] = sum(price_history) / len(price_history)
        
        logger.debug(f"移动平均线计算完成: {stock.code}, MA5={result['ma5']:.2f}, MA10={result['ma10']:.2f}, MA20={result['ma20']:.2f}")
        return result
    
    def identify_previous_highs(
        self,
        stock: Stock,
        price_history: List[float],
        lookback_days: int = 60
    ) -> List[float]:
        """识别前期高点
        
        使用局部极大值方法识别前期高点：
        - 一个价格点如果比其前后各2个交易日的价格都高，则认为是局部高点
        - 在lookback_days范围内识别所有局部高点
        - 返回最高的那个作为前期高点
        
        Args:
            stock: 个股对象
            price_history: 历史价格列表
            lookback_days: 回溯天数
            
        Returns:
            List[float]: 前期高点列表（按价格降序）
        """
        logger.debug(f"识别前期高点: {stock.code}, 回溯{lookback_days}天")
        
        if not price_history or len(price_history) < 5:
            logger.warning(f"价格历史不足: {stock.code}, 长度={len(price_history)}")
            return []
        
        # 限制回溯范围
        lookback_range = min(lookback_days, len(price_history))
        recent_prices = price_history[-lookback_range:]
        
        # 识别局部极大值
        local_highs = []
        window = 2  # 前后各2个交易日
        
        for i in range(window, len(recent_prices) - window):
            current_price = recent_prices[i]
            
            # 检查是否为局部极大值
            is_local_high = True
            for j in range(i - window, i + window + 1):
                if j != i and recent_prices[j] >= current_price:
                    is_local_high = False
                    break
            
            if is_local_high:
                local_highs.append(current_price)
        
        # 如果没有找到局部高点，使用历史最高价
        if not local_highs:
            local_highs = [max(recent_prices)]
        
        # 按价格降序排序
        local_highs.sort(reverse=True)
        
        logger.debug(f"识别到{len(local_highs)}个前期高点: {stock.code}, 最高={local_highs[0]:.2f}")
        return local_highs
    
    def calculate_chip_concentration(
        self,
        stock: Stock,
        price_history: List[float],
        volume_history: List[float],
        lookback_days: int = 10
    ) -> Tuple[float, float]:
        """计算筹码密集区
        
        使用成交量加权价格方法计算筹码密集区：
        - 计算近N日的成交量加权平均价格（VWAP）
        - 计算价格的标准差
        - 筹码密集区 = VWAP ± 0.5 * 标准差
        
        Args:
            stock: 个股对象
            price_history: 历史价格列表
            volume_history: 历史成交量列表
            lookback_days: 回溯天数
            
        Returns:
            Tuple[float, float]: (筹码密集区下沿, 筹码密集区上沿)
        """
        logger.debug(f"计算筹码密集区: {stock.code}, 回溯{lookback_days}天")
        
        if not price_history or not volume_history:
            logger.warning(f"价格或成交量历史为空: {stock.code}")
            return (0.0, 0.0)
        
        if len(price_history) != len(volume_history):
            logger.warning(f"价格和成交量历史长度不匹配: {stock.code}")
            return (0.0, 0.0)
        
        # 限制回溯范围
        lookback_range = min(lookback_days, len(price_history))
        recent_prices = price_history[-lookback_range:]
        recent_volumes = volume_history[-lookback_range:]
        
        # 计算成交量加权平均价格（VWAP）
        total_volume = sum(recent_volumes)
        if total_volume == 0:
            logger.warning(f"总成交量为0: {stock.code}")
            avg_price = sum(recent_prices) / len(recent_prices)
            return (avg_price * 0.95, avg_price * 1.05)
        
        vwap = sum(p * v for p, v in zip(recent_prices, recent_volumes)) / total_volume
        
        # 计算价格标准差
        mean_price = sum(recent_prices) / len(recent_prices)
        variance = sum((p - mean_price) ** 2 for p in recent_prices) / len(recent_prices)
        std_dev = variance ** 0.5
        
        # 筹码密集区 = VWAP ± 0.5 * 标准差
        chip_zone_low = vwap - 0.5 * std_dev
        chip_zone_high = vwap + 0.5 * std_dev
        
        logger.debug(f"筹码密集区计算完成: {stock.code}, VWAP={vwap:.2f}, 区间=[{chip_zone_low:.2f}, {chip_zone_high:.2f}]")
        return (chip_zone_low, chip_zone_high)
    
    def calculate_distance_percentages(
        self,
        current_price: float,
        ma5: float,
        ma10: float,
        ma20: float,
        previous_high: float
    ) -> Dict[str, float]:
        """计算距离百分比
        
        计算当前价格与各技术位的距离百分比：
        - 距离百分比 = (当前价格 - 技术位) / 技术位 * 100
        - 正值表示在技术位上方，负值表示在技术位下方
        
        Args:
            current_price: 当前价格
            ma5: 5日均线
            ma10: 10日均线
            ma20: 20日均线
            previous_high: 前期高点
            
        Returns:
            Dict: 包含distance_to_ma5_pct, distance_to_ma10_pct等的字典
        """
        logger.debug(f"计算距离百分比: 当前价格={current_price:.2f}")
        
        result = {}
        
        # 计算距离MA5的百分比
        if ma5 > 0:
            result["distance_to_ma5_pct"] = (current_price - ma5) / ma5 * 100
        else:
            result["distance_to_ma5_pct"] = 0.0
        
        # 计算距离MA10的百分比
        if ma10 > 0:
            result["distance_to_ma10_pct"] = (current_price - ma10) / ma10 * 100
        else:
            result["distance_to_ma10_pct"] = 0.0
        
        # 计算距离MA20的百分比
        if ma20 > 0:
            result["distance_to_ma20_pct"] = (current_price - ma20) / ma20 * 100
        else:
            result["distance_to_ma20_pct"] = 0.0
        
        # 计算距离前期高点的百分比
        if previous_high > 0:
            result["distance_to_high_pct"] = (current_price - previous_high) / previous_high * 100
        else:
            result["distance_to_high_pct"] = 0.0
        
        logger.debug(f"距离百分比计算完成: MA5={result['distance_to_ma5_pct']:.2f}%, "
                    f"MA10={result['distance_to_ma10_pct']:.2f}%, "
                    f"MA20={result['distance_to_ma20_pct']:.2f}%, "
                    f"前高={result['distance_to_high_pct']:.2f}%")
        return result
    
    def calculate_technical_levels(
        self,
        stock: Stock,
        price_history: List[float],
        volume_history: List[float]
    ) -> TechnicalLevels:
        """计算完整的技术位数据
        
        Args:
            stock: 个股对象
            price_history: 历史价格列表
            volume_history: 历史成交量列表
            
        Returns:
            TechnicalLevels: 技术位对象
        """
        logger.info(f"计算技术位: {stock.code}")
        
        try:
            # 1. 计算移动平均线
            ma_dict = self.calculate_moving_averages(stock, price_history)
            ma5 = ma_dict["ma5"]
            ma10 = ma_dict["ma10"]
            ma20 = ma_dict["ma20"]
            
            # 2. 识别前期高点
            previous_highs = self.identify_previous_highs(stock, price_history)
            previous_high = previous_highs[0] if previous_highs else stock.price
            
            # 3. 计算筹码密集区
            chip_zone_low, chip_zone_high = self.calculate_chip_concentration(
                stock, price_history, volume_history
            )
            
            # 4. 计算距离百分比
            distance_dict = self.calculate_distance_percentages(
                stock.price, ma5, ma10, ma20, previous_high
            )
            
            # 5. 构建技术位对象
            technical_levels = TechnicalLevels(
                ma5=ma5,
                ma10=ma10,
                ma20=ma20,
                previous_high=previous_high,
                chip_zone_low=chip_zone_low,
                chip_zone_high=chip_zone_high,
                distance_to_ma5_pct=distance_dict["distance_to_ma5_pct"],
                distance_to_high_pct=distance_dict["distance_to_high_pct"]
            )
            
            logger.info(f"技术位计算完成: {stock.code}")
            return technical_levels
            
        except Exception as e:
            logger.error(f"计算技术位失败: {stock.code}, 错误: {e}")
            # 返回默认值
            return TechnicalLevels(
                ma5=0.0,
                ma10=0.0,
                ma20=0.0,
                previous_high=0.0,
                chip_zone_low=0.0,
                chip_zone_high=0.0,
                distance_to_ma5_pct=0.0,
                distance_to_high_pct=0.0
            )
