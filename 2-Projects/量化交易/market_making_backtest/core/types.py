"""
Core type definitions for the market making backtest framework.
All types use nanosecond precision timestamps and Decimal for prices/quantities.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum, IntEnum
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime
import time


class Side(Enum):
    """Trade side"""
    BUY = "buy"
    SELL = "sell"

    @property
    def opposite(self) -> "Side":
        return Side.SELL if self == Side.BUY else Side.BUY


class OrderType(Enum):
    """Order type"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order lifecycle status"""
    CREATED = "created"           # Order created but not submitted
    PENDING = "pending"           # Submitted, waiting for acceptance
    ACCEPTED = "accepted"         # Accepted by exchange/matching engine
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class EventType(Enum):
    """Event types for the event-driven system"""
    # System events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SYSTEM_ERROR = "system_error"

    # Market data events
    TICK = "tick"
    BAR_OPEN = "bar_open"
    BAR_CLOSE = "bar_close"
    ORDER_BOOK_UPDATE = "order_book_update"
    TRADE = "trade"

    # Order events
    ORDER_SUBMITTED = "order_submitted"
    ORDER_ACCEPTED = "order_accepted"
    ORDER_REJECTED = "order_rejected"
    ORDER_FILLED = "order_filled"
    ORDER_PARTIALLY_FILLED = "order_partially_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_EXPIRED = "order_expired"

    # Strategy events
    SIGNAL_GENERATED = "signal_generated"

    # Risk events
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"
    TAKE_PROFIT_TRIGGERED = "take_profit_triggered"
    RISK_LIMIT_BREACHED = "risk_limit_breached"
    MARGIN_CALL = "margin_call"

    # Timer events
    TIMER = "timer"


class AssetClass(Enum):
    """Asset class types"""
    STOCK = "stock"
    CRYPTO = "crypto"
    FUTURES = "futures"
    OPTIONS = "options"
    FOREX = "forex"
    ETF = "etf"


# ============== Data Classes ==============

@dataclass
class Symbol:
    """Trading symbol definition"""
    code: str                           # e.g., "AAPL", "BTC-USD"
    exchange: str                       # e.g., "NASDAQ", "BINANCE"
    asset_class: AssetClass
    tick_size: Decimal                  # Minimum price increment
    lot_size: Decimal                   # Minimum quantity increment
    currency: str = "USD"
    multiplier: Decimal = Decimal("1")  # For futures/options

    def __post_init__(self):
        self.tick_size = Decimal(str(self.tick_size))
        self.lot_size = Decimal(str(self.lot_size))


@dataclass
class Tick:
    """Market tick data"""
    symbol: str
    timestamp: int              # Nanoseconds
    price: Decimal
    size: Decimal
    side: Side                # Aggressor side
    exchange: str = ""

    def __post_init__(self):
        self.price = Decimal(str(self.price))
        self.size = Decimal(str(self.size))


@dataclass
class Bar:
    """OHLCV bar data"""
    symbol: str
    timestamp: int            # Start time in nanoseconds
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    trades: int = 0           # Number of trades

    def __post_init__(self):
        self.open = Decimal(str(self.open))
        self.high = Decimal(str(self.high))
        self.low = Decimal(str(self.low))
        self.close = Decimal(str(self.close))
        self.volume = Decimal(str(self.volume))


@dataclass
class OrderBookLevel:
    """Single price level in order book"""
    price: Decimal
    quantity: Decimal
    order_count: int = 0

    def __post_init__(self):
        self.price = Decimal(str(self.price))
        self.quantity = Decimal(str(self.quantity))


@dataclass
class OrderBook:
    """Full order book snapshot"""
    symbol: str
    timestamp: int
    bids: List[OrderBookLevel]      # Sorted descending by price
    asks: List[OrderBookLevel]      # Sorted ascending by price
    last_price: Optional[Decimal] = None
    last_size: Optional[Decimal] = None


@dataclass
class Trade:
    """Market trade record"""
    trade_id: str
    symbol: str
    timestamp: int
    price: Decimal
    size: Decimal
    side: Side                  # Aggressor side
    buyer_order_id: Optional[str] = None
    seller_order_id: Optional[str] = None

    def __post_init__(self):
        self.price = Decimal(str(self.price))
        self.size = Decimal(str(self.size))


# ============== Order Classes ==============

@dataclass
class OrderRequest:
    """Order creation request"""
    symbol: str
    side: Side
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None      # For limit orders
    stop_price: Optional[Decimal] = None  # For stop orders
    time_in_force: str = "GTC"            # GTC, IOC, FOK
    strategy_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.quantity = Decimal(str(self.quantity))
        if self.price:
            self.price = Decimal(str(self.price))


@dataclass
class Order:
    """Order instance"""
    order_id: str
    client_order_id: str
    request: OrderRequest
    status: OrderStatus
    filled_quantity: Decimal
    avg_price: Optional[Decimal]
    created_at: int                   # Nanosecond timestamp
    updated_at: int                   # Nanosecond timestamp
    queue_position: Optional[int] = None  # Position in order book queue

    def __post_init__(self):
        self.filled_quantity = Decimal(str(self.filled_quantity))
        if self.avg_price:
            self.avg_price = Decimal(str(self.avg_price))

    @property
    def remaining_quantity(self) -> Decimal:
        return self.request.quantity - self.filled_quantity

    @property
    def is_done(self) -> bool:
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]


@dataclass
class Fill:
    """Order fill record"""
    fill_id: str
    order_id: str
    symbol: str
    side: Side
    price: Decimal
    size: Decimal
    fee: Decimal
    timestamp: int                    # Nanosecond timestamp
    is_maker: bool = True             # True if maker, False if taker
    counterparty: Optional[str] = None

    def __post_init__(self):
        self.price = Decimal(str(self.price))
        self.size = Decimal(str(self.size))
        self.fee = Decimal(str(self.fee))


# ============== Position Classes ==============

@dataclass
class Position:
    """Position tracking"""
    symbol: str
    side: Side                        # NET_LONG, NET_SHORT, FLAT
    quantity: Decimal                 # Absolute quantity
    avg_entry_price: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    created_at: int
    updated_at: int

    def __post_init__(self):
        self.quantity = Decimal(str(self.quantity))
        self.avg_entry_price = Decimal(str(self.avg_entry_price))
        self.unrealized_pnl = Decimal(str(self.unrealized_pnl))
        self.realized_pnl = Decimal(str(self.realized_pnl))

    def update_with_fill(self, fill: Fill) -> None:
        """Update position with new fill"""
        # Implementation here
        pass

    @property
    def market_value(self) -> Decimal:
        """Current market value of position"""
        # Implementation here
        return Decimal('0')


# ============== Utility Functions ==============

def current_timestamp_ns() -> int:
    """Get current timestamp in nanoseconds"""
    return time.time_ns()


def datetime_to_ns(dt: datetime) -> int:
    """Convert datetime to nanoseconds timestamp"""
    return int(dt.timestamp() * 1_000_000_000)


def ns_to_datetime(ns: int) -> datetime:
    """Convert nanoseconds timestamp to datetime"""
    return datetime.fromtimestamp(ns / 1_000_000_000)


def format_ns(ns: int) -> str:
    """Format nanoseconds to human-readable string"""
    dt = ns_to_datetime(ns)
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
