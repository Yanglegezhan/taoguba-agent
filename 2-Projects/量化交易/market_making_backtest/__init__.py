"""
Market Making Backtest Framework

A comprehensive event-driven backtesting framework for market making and algorithmic trading strategies.

Key Features:
- Event-driven architecture with nanosecond precision
- L3 order book with queue position tracking
- Realistic time-priority matching
- Multi-asset support
- Built-in TWAP strategy example

Example Usage:
    from market_making_backtest import create_simulation_clock, EventBus, EventLoop
    from market_making_backtest import TWAPStrategy

    # Create components
    clock = create_simulation_clock()
    event_bus = EventBus()
    event_loop = EventLoop(event_bus=event_bus, clock=clock)

    # Create and run strategy
    twap = TWAPStrategy(
        strategy_id="twap_1",
        symbols=["BTC-USD"],
        params={
            "total_quantity": 1000,
            "duration_seconds": 120,
            "num_slices": 12,
            "side": "BUY"
        }
    )
"""

__version__ = "0.1.0"
__author__ = "Quant Team"

# Core exports
from .core import (
    # Enums
    Side, OrderType, OrderStatus, EventType, AssetClass,
    # Data classes
    Symbol, Tick, Bar, OrderBookLevel, OrderBook, Trade,
    OrderRequest, Order, Fill, Position,
    # Core classes
    EventBus, EventHandler, PrioritizedEvent,
    Clock, EventLoop, LoopStats,
    # Functions
    current_timestamp_ns, datetime_to_ns, ns_to_datetime, format_ns,
    create_simulation_clock, create_live_clock,
)

# Strategy exports
from .strategy.base import Strategy, StrategyContext

# Example strategies
from .examples.twap_strategy import (
    TWAPStrategy,
    TWAPSlice,
    TWAPStats,
    create_twap_strategy
)

__all__ = [
    # Version
    "__version__",

    # Core Enums
    "Side",
    "OrderType",
    "OrderStatus",
    "EventType",
    "AssetClass",

    # Core Data Classes
    "Symbol",
    "Tick",
    "Bar",
    "OrderBookLevel",
    "OrderBook",
    "Trade",
    "OrderRequest",
    "Order",
    "Fill",
    "Position",

    # Core Classes
    "EventBus",
    "EventHandler",
    "PrioritizedEvent",
    "Clock",
    "EventLoop",
    "LoopStats",

    # Core Functions
    "current_timestamp_ns",
    "datetime_to_ns",
    "ns_to_datetime",
    "format_ns",
    "create_simulation_clock",
    "create_live_clock",

    # Strategy
    "Strategy",
    "StrategyContext",

    # TWAP Strategy
    "TWAPStrategy",
    "TWAPSlice",
    "TWAPStats",
    "create_twap_strategy",
]


def get_version() -> str:
    """Get framework version"""
    return __version__


def get_info() -> dict:
    """Get framework information"""
    return {
        "version": __version__,
        "author": __author__,
        "description": "Event-driven market making backtest framework",
        "features": [
            "Nanosecond precision event loop",
            "L3 order book with queue tracking",
            "Time-priority matching",
            "Multi-asset support",
            "TWAP strategy example",
        ],
    }
