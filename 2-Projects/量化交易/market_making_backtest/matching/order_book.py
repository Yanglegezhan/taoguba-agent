"""
Order Book - L3 order book with full depth tracking.
Maintains bid and ask sides with price-time priority.
"""

from typing import Dict, List, Optional, Tuple, Iterator
from decimal import Decimal
from collections import OrderedDict
from dataclasses import dataclass

from ..core.types import Order, Side, OrderStatus, OrderBookLevel, Trade
from .price_level import PriceLevel


@dataclass
class BookSnapshot:
    """Immutable order book snapshot"""
    symbol: str
    timestamp: int
    bids: List[OrderBookLevel]  # Sorted descending
    asks: List[OrderBookLevel]  # Sorted ascending
    last_price: Optional[Decimal] = None
    last_size: Optional[Decimal] = None


class OrderBook:
    """
    L3 Order Book with full depth tracking.

    Maintains two sides:
    - Bids: OrderedDict of price -> PriceLevel (descending)
    - Asks: OrderedDict of price -> PriceLevel (ascending)
    """

    def __init__(self, symbol: str, tick_size: Decimal = Decimal('0.01')):
        self.symbol = symbol
        self.tick_size = tickSize = Decimal(str(tick_size))

        # Price levels: price -> PriceLevel
        # Using OrderedDict to maintain price ordering
        self._bids: Dict[Decimal, PriceLevel] = {}  # Descending price
        self._asks: Dict[Decimal, PriceLevel] = {}  # Ascending price

        # Quick order lookup: order_id -> (side, price)
        self._order_index: Dict[str, Tuple[Side, Decimal]] = {}

        # Market data
        self.best_bid: Optional[Decimal] = None
        self.best_ask: Optional[Decimal] = None
        self.last_price: Optional[Decimal] = None
        self.last_size: Optional[Decimal] = None
        self.last_trade_time: Optional[int] = None

        # Statistics
        self.total_volume = Decimal('0')
        self.trade_count = 0
        self.add_count = 0
        self.cancel_count = 0

    # ========== Property Access ==========

    @property
    def spread(self) -> Optional[Decimal]:
        """Current bid-ask spread"""
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    @property
    def mid_price(self) -> Optional[Decimal]:
        """Mid price between best bid and ask"""
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2

    @property
    def has_bids(self) -> bool:
        return len(self._bids) > 0

    @property
    def has_asks(self) -> bool:
        return len(self._asks) > 0

    # ========== Order Management ==========

    def add_order(self, order: Order) -> int:
        """
        Add an order to the book.

        Returns:
            Queue position (0 = first in queue at that price)
        """
        if order.order_id in self._order_index:
            raise ValueError(f"Order {order.order_id} already exists in book")

        side = order.request.side
        price = order.request.price

        if price is None:
            raise ValueError("Price is required for book orders")

        # Round price to tick size
        price = self._round_price(price)

        # Get or create price level
        if side == Side.BUY:
            if price not in self._bids:
                self._bids[price] = PriceLevel(price, side)
            level = self._bids[price]
        else:
            if price not in self._asks:
                self._asks[price] = PriceLevel(price, side)
            level = self._asks[price]

        # Add order to level
        queue_position = level.add_order(order)

        # Index order
        self._order_index[order.order_id] = (side, price)

        # Update best prices
        self._update_best_prices()

        self.add_count += 1

        return queue_position

    def cancel_order(self, order_id: str) -> Optional[Order]:
        """
        Cancel an order in the book.

        Returns:
            The cancelled order, or None if not found
        """
        if order_id not in self._order_index:
            return None

        side, price = self._order_index[order_id]

        # Get price level
        if side == Side.BUY:
            level = self._bids.get(price)
        else:
            level = self._asks.get(price)

        if level is None:
            del self._order_index[order_id]
            return None

        # Remove order from level
        order = level.remove_order(order_id)

        if order:
            del self._order_index[order_id]

            # Clean up empty price levels
            if level.is_empty():
                if side == Side.BUY:
                    del self._bids[price]
                else:
                    del self._asks[price]

            # Update best prices
            self._update_best_prices()

            self.cancel_count += 1

        return order

    def modify_order(self, order_id: str, new_quantity: Decimal) -> bool:
        """
        Modify an order's quantity (only reduces allowed in most markets).

        Returns:
            True if successful
        """
        # For simplicity, we'll cancel and re-add
        # In a real system, this would be an atomic modify
        order = self.cancel_order(order_id)
        if order is None:
            return False

        # Create new order with modified quantity
        order.request.quantity = min(new_quantity, order.request.quantity)
        self.add_order(order)
        return True

    # ========== Matching ==========

    def match_market_order(self, side: Side, quantity: Decimal, aggressive_order_id: str) -> tuple:
        """
        Match a market order against the book.

        Args:
            side: Side of the aggressive order (what you're buying/selling)
            quantity: Quantity to match
            aggressive_order_id: ID of the aggressive order

        Returns:
            Tuple of (fills: list, remaining_quantity: Decimal)
            where fills is list of (maker_order_id, filled_qty, price, side)
        """
        fills = []
        remaining = quantity

        # Determine which side to match against
        if side == Side.BUY:
            # Buy order matches against asks
            opposite_levels = sorted(self._asks.items())  # Ascending
            fill_side = Side.SELL
        else:
            # Sell order matches against bids
            opposite_levels = sorted(self._bids.items(), reverse=True)  # Descending
            fill_side = Side.BUY

        for price, level in opposite_levels:
            if remaining <= 0:
                break

            # Match against this price level
            level_fills, remaining = level.match_against(remaining, side)

            for maker_order_id, fill_qty, price_matched, _ in level_fills:
                fills.append((maker_order_id, fill_qty, price, fill_side))

        return fills, remaining

    def match_limit_order(self, order: Order) -> tuple:
        """
        Try to match a limit order immediately upon submission.

        Returns:
            Tuple of (fills: list, remaining_quantity: Decimal)
        """
        side = order.request.side
        price = order.request.price
        quantity = order.request.quantity

        fills = []
        remaining = quantity

        # Check if order can match immediately
        if side == Side.BUY:
            # Buy limit can match if price >= best ask
            if self.best_ask is None or price < self.best_ask:
                return fills, remaining

            # Match against asks
            for ask_price, level in sorted(self._asks.items()):
                if remaining <= 0 or ask_price > price:
                    break

                level_fills, remaining = level.match_against(remaining, side)
                for maker_order_id, fill_qty, _, _ in level_fills:
                    fills.append((maker_order_id, fill_qty, ask_price, Side.SELL))

        else:  # SELL
            # Sell limit can match if price <= best bid
            if self.best_bid is None or price > self.best_bid:
                return fills, remaining

            # Match against bids
            for bid_price, level in sorted(self._bids.items(), reverse=True):
                if remaining <= 0 or bid_price < price:
                    break

                level_fills, remaining = level.match_against(remaining, side)
                for maker_order_id, fill_qty, _, _ in level_fills:
                    fills.append((maker_order_id, fill_qty, bid_price, Side.BUY))

        return fills, remaining

    # ========== Helper Methods ==========

    def _round_price(self, price: Decimal) -> Decimal:
        """Round price to tick size"""
        ticks = (price / self.tick_size).quantize(Decimal('1'))
        return ticks * self.tick_size

    def _update_best_prices(self) -> None:
        """Update best bid and ask prices"""
        # Best bid = highest price with orders
        if self._bids:
            self.best_bid = max(self._bids.keys())
        else:
            self.best_bid = None

        # Best ask = lowest price with orders
        if self._asks:
            self.best_ask = min(self._asks.keys())
        else:
            self.best_ask = None

    def get_price_level(self, price: Decimal, side: Side) -> Optional[PriceLevel]:
        """Get price level at specific price"""
        if side == Side.BUY:
            return self._bids.get(price)
        else:
            return self._asks.get(price)

    def get_order_position(self, order_id: str) -> Optional[Tuple[int, Decimal, Side]]:
        """
        Get queue position for an order.

        Returns:
            Tuple of (queue_position, price, side) or None
        """
        if order_id not in self._order_index:
            return None

        side, price = self._order_index[order_id]
        level = self._bids.get(price) if side == Side.BUY else self._asks.get(price)

        if level is None:
            return None

        # Find order in level
        for order in level:
            if order.order_id == order_id:
                # Find queue position
                pos = 0
                for q_order in level:
                    if q_order.order_id == order_id:
                        return (pos, price, side)
                    pos += 1

        return None

    # ========== Snapshot ==========

    def get_snapshot(self, max_depth: int = 10) -> dict:
        """
        Get current order book snapshot.

        Returns:
            Dictionary with bids, asks, and metadata
        """
        bids = []
        for price, level in sorted(self._bids.items(), reverse=True)[:max_depth]:
            bids.append({
                'price': float(price),
                'quantity': float(level.total_quantity),
                'order_count': level.order_count
            })

        asks = []
        for price, level in sorted(self._asks.items())[:max_depth]:
            asks.append({
                'price': float(price),
                'quantity': float(level.total_quantity),
                'order_count': level.order_count
            })

        return {
            'symbol': self.symbol,
            'best_bid': float(self.best_bid) if self.best_bid else None,
            'best_ask': float(self.best_ask) if self.best_ask else None,
            'spread': float(self.spread) if self.spread else None,
            'mid_price': float(self.mid_price) if self.mid_price else None,
            'bids': bids,
            'asks': asks,
            'total_bid_qty': float(sum(l.total_quantity for l in self._bids.values())),
            'total_ask_qty': float(sum(l.total_quantity for l in self._asks.values())),
        }

    def __repr__(self) -> str:
        return f"OrderBook({self.symbol}, bids={len(self._bids)}, asks={len(self._asks)})"
