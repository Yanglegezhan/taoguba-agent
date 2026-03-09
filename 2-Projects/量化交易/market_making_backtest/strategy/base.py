"""
Strategy Base Class - Abstract base class for all trading strategies.
Provides lifecycle management, market data callbacks, and trading interfaces.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any, Callable
from decimal import Decimal
from dataclasses import dataclass

from ..core.types import (
    Order, OrderType, OrderRequest, Side,
    Tick, Bar, OrderBook, Fill,
    current_timestamp_ns
)


@dataclass
class Position:
    """Position information for a symbol"""
    symbol: str
    side: Side  # NET_LONG, NET_SHORT, or FLAT
    quantity: Decimal
    avg_entry_price: Decimal
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')


@dataclass
class StrategyContext:
    """Context passed to strategy with trading interfaces"""
    strategy_id: str
    event_bus: Any  # EventBus
    clock: Any  # Clock
    order_manager: Any  # OrderManager
    position_manager: Any  # PositionManager

    def send_order(self, order_req: OrderRequest) -> Optional[str]:
        """Send an order"""
        return self.order_manager.send_order(self.strategy_id, order_req)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        return self.order_manager.cancel_order(self.strategy_id, order_id)

    def cancel_all(self, symbol: Optional[str] = None) -> int:
        """Cancel all orders"""
        return self.order_manager.cancel_all(self.strategy_id, symbol)

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol"""
        return self.position_manager.get_position(self.strategy_id, symbol)

    def get_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get active orders"""
        return self.order_manager.get_orders(self.strategy_id, symbol)

    def get_balance(self) -> Decimal:
        """Get available balance"""
        return self.position_manager.get_balance(self.strategy_id)

    def log(self, level: str, message: str) -> None:
        """Log a message"""
        self.order_manager.log(level, self.strategy_id, message)

    def set_timer(
        self,
        delay_ns: int,
        callback: Callable,
        recurring: bool = False,
        interval_ns: Optional[int] = None
    ) -> str:
        """Set a timer"""
        return self.clock.set_timer(delay_ns, callback, recurring, interval_ns)

    def cancel_timer(self, timer_id: str) -> bool:
        """Cancel a timer"""
        return self.clock.cancel_timer(timer_id)


class Strategy(ABC):
    """
    Abstract base class for all trading strategies.

    To implement a strategy:
    1. Subclass Strategy
    2. Override on_init() for initialization
    3. Override on_tick(), on_bar(), or on_order_book() for data handling
    4. Use send_order(), cancel_order() for trading
    5. Override on_order_filled(), on_order_cancelled() for event handling
    """

    def __init__(self, strategy_id: str, symbols: List[str], params: Dict[str, Any]):
        """
        Initialize strategy.

        Args:
            strategy_id: Unique strategy identifier
            symbols: List of trading symbols
            params: Strategy parameters
        """
        self.strategy_id = strategy_id
        self.symbols = symbols
        self.params = params

        self.context: Optional[StrategyContext] = None
        self.is_running = False
        self.is_initialized = False

        # Callbacks for strategy to use
        self._callbacks: Dict[str, List[Callable]] = {
            'start': [],
            'stop': [],
            'fill': [],
            'cancel': [],
        }

    # ========== Lifecycle Methods ==========

    def initialize(self, context: StrategyContext) -> None:
        """
        Initialize strategy with context.
        Called before on_start().
        """
        self.context = context

        # Call strategy-specific initialization
        self.on_init()

        self.is_initialized = True
        self.log("INFO", f"Strategy {self.strategy_id} initialized")

    def start(self) -> None:
        """Start strategy"""
        if not self.is_initialized:
            raise RuntimeError("Strategy not initialized. Call initialize() first.")

        self.on_start()
        self.is_running = True
        self.log("INFO", f"Strategy {self.strategy_id} started")

        # Execute start callbacks
        for callback in self._callbacks['start']:
            try:
                callback()
            except Exception as e:
                self.log("ERROR", f"Start callback error: {e}")

    def stop(self) -> None:
        """Stop strategy"""
        if not self.is_running:
            return

        self.on_stop()
        self.is_running = False
        self.log("INFO", f"Strategy {self.strategy_id} stopped")

        # Execute stop callbacks
        for callback in self._callbacks['stop']:
            try:
                callback()
            except Exception as e:
                self.log("ERROR", f"Stop callback error: {e}")

    def on_init(self) -> None:
        """
        Override this method for strategy initialization.
        Called once when strategy is initialized.
        """
        pass

    def on_start(self) -> None:
        """
        Override this method for strategy start logic.
        Called when strategy starts running.
        """
        pass

    def on_stop(self) -> None:
        """
        Override this method for strategy stop logic.
        Called when strategy stops.
        """
        pass

    # ========== Market Data Callbacks ==========

    @abstractmethod
    def on_tick(self, tick: Tick) -> None:
        """
        Override this method to handle tick data.

        Args:
            tick: Market tick data
        """
        pass

    def on_bar(self, bar: Bar) -> None:
        """
        Override this method to handle bar (OHLCV) data.
        Optional - only override if using bar data.

        Args:
            bar: OHLCV bar data
        """
        pass

    def on_order_book(self, order_book: OrderBook) -> None:
        """
        Override this method to handle order book updates.
        Optional - only override if using order book data.

        Args:
            order_book: Full order book snapshot
        """
        pass

    def on_trade(self, trade: Trade) -> None:
        """
        Override this method to handle market trades.
        Optional - only override if tracking market trades.

        Args:
            trade: Market trade record
        """
        pass

    # ========== Order Event Callbacks ==========

    def on_order_filled(self, fill: Fill) -> None:
        """
        Called when one of our orders is filled.
        Override this to handle fill events.

        Args:
            fill: Fill details
        """
        pass

    def on_order_cancelled(self, order: Order) -> None:
        """
        Called when one of our orders is cancelled.
        Override this to handle cancel events.

        Args:
            order: The cancelled order
        """
        pass

    def on_order_rejected(self, order: Order, reason: str) -> None:
        """
        Called when one of our orders is rejected.
        Override this to handle rejection events.

        Args:
            order: The rejected order
            reason: Rejection reason
        """
        pass

    # ========== Trading Interface ==========

    def send_order(self, order_req: OrderRequest) -> Optional[str]:
        """
        Send an order to the market.

        Args:
            order_req: Order request details

        Returns:
            Order ID if successful, None otherwise
        """
        if not self.is_running:
            self.log("WARNING", "Cannot send order: strategy not running")
            return None

        if self.context is None:
            self.log("ERROR", "Cannot send order: no context")
            return None

        order_id = self.context.send_order(order_req)
        if order_id:
            self.log("INFO", f"Order sent: {order_id}")
        return order_id

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: ID of order to cancel

        Returns:
            True if cancellation was submitted
        """
        if not self.is_running:
            return False

        if self.context is None:
            return False

        result = self.context.cancel_order(order_id)
        if result:
            self.log("INFO", f"Cancel submitted: {order_id}")
        return result

    def cancel_all(self, symbol: Optional[str] = None) -> int:
        """
        Cancel all orders (optionally filtered by symbol).

        Args:
            symbol: If specified, only cancel orders for this symbol

        Returns:
            Number of orders cancelled
        """
        if not self.is_running:
            return 0

        if self.context is None:
            return 0

        count = self.context.cancel_all(symbol)
        self.log("INFO", f"Cancelled {count} orders")
        return count

    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get current position for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position object, or None if no position
        """
        if self.context is None:
            return None

        return self.context.get_position(symbol)

    def get_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Get active orders.

        Args:
            symbol: If specified, only return orders for this symbol

        Returns:
            List of active orders
        """
        if self.context is None:
            return []

        return self.context.get_orders(symbol)

    def get_balance(self) -> Decimal:
        """Get available balance"""
        if self.context is None:
            return Decimal('0')

        return self.context.get_balance()

    # ========== Utility Methods ==========

    def log(self, level: str, message: str) -> None:
        """
        Log a message.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            message: Log message
        """
        if self.context:
            self.context.log(level, message)
        else:
            print(f"[{level}] [{self.strategy_id}] {message}")

    def get_param(self, key: str, default: Any = None) -> Any:
        """
        Get a strategy parameter.

        Args:
            key: Parameter name
            default: Default value if not found

        Returns:
            Parameter value
        """
        return self.params.get(key, default)

    def set_timer(
        self,
        delay_ns: int,
        callback: Callable,
        recurring: bool = False,
        interval_ns: Optional[int] = None
    ) -> str:
        """
        Set a timer callback.

        Args:
            delay_ns: Delay before first trigger (nanoseconds)
            callback: Function to call when timer triggers
            recurring: If True, timer repeats
            interval_ns: Interval between recurring triggers

        Returns:
            Timer ID
        """
        if self.context is None:
            raise RuntimeError("Cannot set timer: no context")

        return self.context.set_timer(delay_ns, callback, recurring, interval_ns)

    def cancel_timer(self, timer_id: str) -> bool:
        """
        Cancel a timer.

        Args:
            timer_id: Timer ID to cancel

        Returns:
            True if timer was cancelled
        """
        if self.context is None:
            return False

        return self.context.cancel_timer(timer_id)

    def __repr__(self) -> str:
        return f"Strategy({self.strategy_id}, running={self.is_running})"
