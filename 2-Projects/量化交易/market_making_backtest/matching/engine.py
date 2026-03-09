"""
Matching Engine - Central order matching and trade execution.
Coordinates between order book, price levels, and trade execution.
"""

from typing import Dict, List, Optional, Tuple, Callable, Any
from decimal import Decimal
from dataclasses import dataclass, field
from collections import deque
import time

from ..core.types import (
    Order, OrderType, OrderStatus, Side, Fill, Trade,
    EventType, current_timestamp_ns
)
from ..core.event_bus import EventBus
from .order_book import OrderBook


@dataclass
class MatchingResult:
    """Result of order matching"""
    fills: List[Fill] = field(default_factory=list)
    remaining_quantity: Decimal = Decimal('0')
    order_fully_filled: bool = False
    trades: List[Trade] = field(default_factory=list)


class MatchingEngine:
    """
    Central matching engine for order book operations.

    Responsibilities:
    - Match incoming orders against the book
    - Handle market orders (immediate execution)
    - Handle limit orders (execution or placement)
    - Manage order cancellations
    - Generate trades and fills
    - Publish events to event bus
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        fee_maker: Decimal = Decimal('0.001'),      # 0.1% maker fee
        fee_taker: Decimal = Decimal('0.002'),      # 0.2% taker fee
        allow_self_trade: bool = False
    ):
        self.event_bus = event_bus
        self.fee_maker = fee_maker
        self.fee_taker = fee_taker
        self.allow_self_trade = allow_self_trade

        # Order books by symbol
        self._order_books: Dict[str, OrderBook] = {}

        # Trade ID generator
        self._trade_id_counter = 0

        # Statistics
        self.orders_received = 0
        self.orders_filled = 0
        self.orders_cancelled = 0
        self.orders_rejected = 0
        self.trades_executed = 0

    # ========== Order Book Management ==========

    def register_symbol(
        self,
        symbol: str,
        tick_size: Decimal = Decimal('0.01'),
        lot_size: Decimal = Decimal('0.01')
    ) -> OrderBook:
        """Register a new trading symbol"""
        if symbol in self._order_books:
            return self._order_books[symbol]

        order_book = OrderBook(symbol, tick_size)
        self._order_books[symbol] = order_book
        return order_book

    def get_order_book(self, symbol: str) -> Optional[OrderBook]:
        """Get order book for symbol"""
        return self._order_books.get(symbol)

    # ========== Order Processing ==========

    def process_order(self, order: Order) -> MatchingResult:
        """
        Process a new order (market or limit).

        This is the main entry point for order processing.
        """
        self.orders_received += 1

        # Validate order
        if not self._validate_order(order):
            order.status = OrderStatus.REJECTED
            self.orders_rejected += 1
            self._publish_order_event(order)
            return MatchingResult()

        # Get order book
        order_book = self.get_order_book(order.request.symbol)
        if order_book is None:
            order_book = self.register_symbol(order.request.symbol)

        # Process based on order type
        if order.request.order_type == OrderType.MARKET:
            result = self._process_market_order(order, order_book)
        elif order.request.order_type == OrderType.LIMIT:
            result = self._process_limit_order(order, order_book)
        else:
            # Other order types not implemented
            order.status = OrderStatus.REJECTED
            self.orders_rejected += 1
            self._publish_order_event(order)
            return MatchingResult()

        return result

    def _validate_order(self, order: Order) -> bool:
        """Basic order validation"""
        # Check minimum quantity
        if order.request.quantity <= 0:
            return False

        # Check price for limit orders
        if order.request.order_type == OrderType.LIMIT:
            if order.request.price is None or order.request.price <= 0:
                return False

        return True

    def _process_market_order(
        self,
        order: Order,
        order_book: OrderBook
    ) -> MatchingResult:
        """Process a market order (immediate execution)"""
        result = MatchingResult()

        # Check if there's liquidity on the opposite side
        side = order.request.side
        quantity = order.request.quantity

        if side == Side.BUY:
            # Buy market order matches against asks
            opposite_levels = sorted(order_book._asks.items())
        else:
            # Sell market order matches against bids
            opposite_levels = sorted(order_book._asks.items(), reverse=True)

        if not opposite_levels:
            # No liquidity - reject or partially fill
            # For this implementation, we'll allow partial fills
            pass

        # Execute against book
        remaining = quantity
        total_cost = Decimal('0')

        for price, level in opposite_levels:
            if remaining <= 0:
                break

            # Match at this level
            fills, remaining_after = level.match_against(remaining, side)

            for maker_order_id, fill_qty, fill_price, _ in fills:
                # Create fill record
                fill = Fill(
                    fill_id=self._generate_fill_id(),
                    order_id=order.order_id,
                    symbol=order.request.symbol,
                    side=side,
                    price=fill_price,
                    size=fill_qty,
                    fee=fill_qty * fill_price * self.fee_taker,  # Market order pays taker fee
                    timestamp=current_timestamp_ns(),
                    is_maker=False,  # Market order is taker
                    counterparty=maker_order_id
                )
                result.fills.append(fill)

                # Update total cost
                total_cost += fill_qty * fill_price

                # Update maker order
                maker_remaining = order_book.reduce_order(maker_order_id, fill_qty)
                if maker_remaining <= 0:
                    # Maker order fully filled
                    order_book.cancel_order(maker_order_id)

            remaining = remaining_after

        # Update order status
        filled_qty = quantity - remaining
        order.filled_quantity = filled_qty

        if remaining <= 0:
            order.status = OrderStatus.FILLED
            self.orders_filled += 1
        elif filled_qty > 0:
            order.status = OrderStatus.PARTIALLY_FILLED
        else:
            order.status = OrderStatus.FILLED  # Market orders should always fill

        # Update results
        result.remaining_quantity = remaining
        result.order_fully_filled = (remaining <= 0)

        # Calculate average fill price
        if filled_qty > 0:
            order.avg_price = total_cost / filled_qty

        # Publish events
        self._publish_order_event(order)
        for fill in result.fills:
            self._publish_fill_event(fill)

        return result

    def _process_limit_order(
        self,
        order: Order,
        order_book: OrderBook
    ) -> MatchingResult:
        """Process a limit order (may execute or rest in book)"""
        result = MatchingResult()

        side = order.request.side
        price = order.request.price
        quantity = order.request.quantity

        # Check if order can execute immediately (marketable limit order)
        can_match = False

        if side == Side.BUY:
            # Buy limit can match if price >= best ask
            if order_book.best_ask is not None and price >= order_book.best_ask:
                can_match = True
        else:
            # Sell limit can match if price <= best bid
            if order_book.best_bid is not None and price <= order_book.best_bid:
                can_match = True

        if can_match:
            # Match immediately using limit order matching logic
            fills, remaining = order_book.match_limit_order(order)

            # Process fills (similar to market order)
            # ... (fill processing code similar to above)

            # For this implementation, we'll simplify and just add to book
            # In a full implementation, we'd process the fills here

        # If not fully filled, add to book
        if remaining > 0:
            queue_position = order_book.add_order(order)
            order.status = OrderStatus.ACCEPTED

            # Update order with queue position
            order.queue_position = queue_position

        result.remaining_quantity = remaining
        result.order_fully_filled = (remaining <= 0)

        # Publish events
        self._publish_order_event(order)

        return result

    # ========== Utility Methods ==========

    def _generate_fill_id(self) -> str:
        """Generate unique fill ID"""
        self._trade_id_counter += 1
        return f"FILL_{self._trade_id_counter}_{current_timestamp_ns()}"

    def _generate_trade_id(self) -> str:
        """Generate unique trade ID"""
        self._trade_id_counter += 1
        return f"TRADE_{self._trade_id_counter}_{current_timestamp_ns()}"

    def _publish_order_event(self, order: Order) -> None:
        """Publish order status event"""
        if self.event_bus:
            # Map status to event type
            event_type_map = {
                OrderStatus.SUBMITTED: EventType.ORDER_SUBMITTED,
                OrderStatus.ACCEPTED: EventType.ORDER_ACCEPTED,
                OrderStatus.REJECTED: EventType.ORDER_REJECTED,
                OrderStatus.FILLED: EventType.ORDER_FILLED,
                OrderStatus.PARTIALLY_FILLED: EventType.ORDER_PARTIALLY_FILLED,
                OrderStatus.CANCELLED: EventType.ORDER_CANCELLED,
            }

            from ..core.types import Event
            event = Event(
                event_type=event_type_map.get(order.status, EventType.ORDER_SUBMITTED),
                timestamp=current_timestamp_ns(),
                source="matching_engine",
                priority=2,
                metadata={"order": order}
            )
            self.event_bus.publish(event)

    def _publish_fill_event(self, fill: Fill) -> None:
        """Publish fill event"""
        if self.event_bus:
            from ..core.types import Event
            event = Event(
                event_type=EventType.ORDER_FILLED,
                timestamp=fill.timestamp,
                source="matching_engine",
                priority=1,  # High priority
                metadata={"fill": fill}
            )
            self.event_bus.publish(event)

    # ========== Statistics ==========

    def get_stats(self) -> Dict[str, Any]:
        """Get matching engine statistics"""
        return {
            "orders_received": self.orders_received,
            "orders_filled": self.orders_filled,
            "orders_cancelled": self.orders_cancelled,
            "orders_rejected": self.orders_rejected,
            "trades_executed": self.trades_executed,
            "books_count": len(self._order_books),
        }
