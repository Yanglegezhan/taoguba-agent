"""
TWAP Strategy Example - 2-minute Time-Weighted Average Price implementation.

This strategy demonstrates:
- Event-driven strategy architecture
- Timer-based execution
- Order management and tracking
- Statistics and reporting

Usage:
    python -m examples.twap_strategy
"""

from typing import Optional, Dict, Any, List
from decimal import Decimal
from dataclasses import dataclass, field
from datetime import datetime

from ..core.types import (
    Tick, Order, OrderType, OrderRequest, Side,
    OrderStatus, Fill, current_timestamp_ns, format_ns
)
from ..strategy.base import Strategy, Position


@dataclass
class TWAPSlice:
    """Represents a single slice in the TWAP execution"""
    index: int                    # Slice index (0-based)
    quantity: Decimal             # Target quantity for this slice
    sent: bool = False            # Whether slice has been sent
    filled: Decimal = Decimal('0')  # Amount filled
    order_id: Optional[str] = None  # Order ID if sent
    status: str = "pending"       # pending/sent/filled/cancelled


@dataclass
class TWAPStats:
    """Statistics for TWAP execution"""
    start_time_ns: int = 0
    end_time_ns: int = 0
    total_slices: int = 0
    slices_sent: int = 0
    slices_filled: int = 0
    total_quantity: Decimal = Decimal('0')
    total_filled: Decimal = Decimal('0')
    avg_fill_price: Decimal = Decimal('0')
    vwap: Decimal = Decimal('0')
    market_vwap: Decimal = Decimal('0')
    slippage_bps: Decimal = Decimal('0')


class TWAPStrategy(Strategy):
    """
    2-minute TWAP (Time-Weighted Average Price) strategy.

    Divides total quantity into slices and executes them evenly over time.

    Parameters:
        total_quantity: Total quantity to trade
        duration_seconds: Total duration (default 120 = 2 minutes)
        num_slices: Number of slices (default 12, one every 10 seconds)
        symbol: Trading symbol
        side: Side.BUY or Side.SELL
        order_type: OrderType.MARKET or OrderType.LIMIT
    """

    def __init__(self, strategy_id: str, symbols: List[str], params: Dict[str, Any]):
        super().__init__(strategy_id, symbols, params)

        # TWAP Parameters
        self.total_quantity = Decimal(str(params.get('total_quantity', 1000)))
        self.duration_seconds = params.get('duration_seconds', 120)  # 2 minutes
        self.num_slices = params.get('num_slices', 12)  # Every 10 seconds
        self.slice_interval_ns = (self.duration_seconds * 1_000_000_000) // self.num_slices

        # Trading parameters
        self.side = Side.BUY if params.get('side', 'BUY').upper() == 'BUY' else Side.SELL
        self.order_type = OrderType.MARKET if params.get('order_type', 'MARKET').upper() == 'MARKET' else OrderType.LIMIT

        # State
        self.slices: List[TWAPSlice] = []
        self.current_slice_index = 0
        self.is_complete = False
        self.timer_id: Optional[str] = None

        # Statistics
        self.stats = TWAPStats()

        # Market data for VWAP comparison
        self.trade_prices: List[Decimal] = []
        self.trade_volumes: List[Decimal] = []

    # ========== Lifecycle ==========

    def on_init(self) -> None:
        """Initialize TWAP slices"""
        # Calculate quantity per slice
        base_quantity = self.total_quantity // self.num_slices
        remainder = self.total_quantity % self.num_slices

        # Create slices
        for i in range(self.num_slices):
            # Distribute remainder to first slices
            slice_qty = base_quantity + (1 if i < remainder else 0)

            self.slices.append(TWAPSlice(
                index=i,
                quantity=slice_qty
            ))

        self.stats.total_slices = self.num_slices
        self.stats.total_quantity = self.total_quantity

        self.log("INFO", f"TWAP initialized: {self.num_slices} slices, "
                        f"{self.total_quantity} total, {self.duration_seconds}s duration")

    def on_start(self) -> None:
        """Start TWAP execution"""
        self.stats.start_time_ns = current_timestamp_ns()

        # Send first slice immediately
        self._execute_slice(0)

        # Set up timer for remaining slices
        if self.num_slices > 1:
            self._schedule_next_slice()

        self.log("INFO", "TWAP execution started")

    def on_stop(self) -> None:
        """Stop TWAP execution"""
        # Cancel timer
        if self.timer_id:
            self.cancel_timer(self.timer_id)
            self.timer_id = None

        # Cancel any remaining slices
        self._cancel_remaining()

        # Calculate statistics
        self._calculate_final_stats()

        self.log("INFO", "TWAP execution stopped")

    # ========== Slice Execution ==========

    def _execute_slice(self, index: int) -> None:
        """Execute a TWAP slice"""
        if index >= len(self.slices):
            return

        if index != self.current_slice_index:
            self.log("WARNING", f"Slice index mismatch: expected {self.current_slice_index}, got {index}")

        slice_data = self.slices[index]

        # Check if already complete
        if self.stats.total_filled >= self.stats.total_quantity:
            self.is_complete = True
            self.log("INFO", "TWAP execution complete")
            return

        # Calculate remaining to fill
        remaining = self.stats.total_quantity - self.stats.total_filled
        quantity = min(slice_data.quantity, remaining)

        if quantity <= 0:
            return

        # Get symbol
        symbol = self.symbols[0] if self.symbols else "UNKNOWN"

        # Send order
        order_req = OrderRequest(
            symbol=symbol,
            side=self.side,
            order_type=self.order_type,
            quantity=quantity,
            price=None,  # Market order
            strategy_id=self.strategy_id
        )

        order_id = self.send_order(order_req)

        if order_id:
            slice_data.sent = True
            slice_data.order_id = order_id
            slice_data.status = "sent"
            self.stats.slices_sent += 1

            self.log("INFO", f"Slice {index + 1}/{self.num_slices} sent: "
                            f"order_id={order_id}, qty={quantity}")
        else:
            self.log("ERROR", f"Failed to send slice {index + 1}")

        # Advance to next slice
        self.current_slice_index = index + 1

    def _schedule_next_slice(self) -> None:
        """Schedule the next slice execution"""
        if self.current_slice_index >= self.num_slices:
            return

        # Set timer for next slice
        self.timer_id = self.set_timer(
            delay_ns=self.slice_interval_ns,
            callback=self._on_timer,
            recurring=False
        )

    def _on_timer(self, timer_id: str) -> None:
        """Timer callback for next slice"""
        self.timer_id = None

        # Execute next slice
        self._execute_slice(self.current_slice_index)

        # Schedule next if not complete
        if not self.is_complete and self.current_slice_index < self.num_slices:
            self._schedule_next_slice()

    def _cancel_remaining(self) -> None:
        """Cancel any remaining unfilled slices"""
        for slice_data in self.slices:
            if slice_data.sent and slice_data.status in ("sent", "pending"):
                if slice_data.order_id:
                    self.cancel_order(slice_data.order_id)
                    slice_data.status = "cancelled"

    # ========== Event Handlers ==========

    def on_order_filled(self, fill: Fill) -> None:
        """Handle order fill"""
        # Find the slice this fill belongs to
        for slice_data in self.slices:
            if slice_data.order_id == fill.order_id:
                slice_data.filled += fill.size
                slice_data.status = "filled" if slice_data.filled >= slice_data.quantity else "partial"
                break

        # Update statistics
        self.stats.total_filled += fill.size

        # Track for VWAP calculation
        self.trade_prices.append(fill.price)
        self.trade_volumes.append(fill.size)

        self.log("INFO", f"Fill: order_id={fill.order_id}, "
                        f"qty={fill.size}, price={fill.price}, "
                        f"total_filled={self.stats.total_filled}/{self.stats.total_quantity}")

        # Check if complete
        if self.stats.total_filled >= self.stats.total_quantity:
            self.is_complete = True
            self.stats.slices_filled = sum(1 for s in self.slices if s.status == "filled")
            self._calculate_final_stats()
            self.log("INFO", "TWAP execution complete!")

    def on_order_cancelled(self, order: Order) -> None:
        """Handle order cancellation"""
        for slice_data in self.slices:
            if slice_data.order_id == order.order_id:
                slice_data.status = "cancelled"
                break

        self.log("INFO", f"Order cancelled: {order.order_id}")

    # ========== Statistics ==========

    def _calculate_final_stats(self) -> None:
        """Calculate final statistics"""
        self.stats.end_time_ns = current_timestamp_ns()

        # Calculate average fill price
        if self.trade_prices and self.trade_volumes:
            total_value = sum(
                p * v for p, v in zip(self.trade_prices, self.trade_volumes)
            )
            self.stats.avg_fill_price = total_value / sum(self.trade_volumes)

        # Calculate execution VWAP
        if self.stats.total_filled > 0:
            self.stats.vwap = self.stats.avg_fill_price

        # Calculate duration
        if self.stats.start_time_ns > 0:
            duration_ns = self.stats.end_time_ns - self.stats.start_time_ns
            duration_sec = duration_ns / 1_000_000_000

        self.log("INFO", f"\n{'='*50}")
        self.log("INFO", "TWAP Execution Summary:")
        self.log("INFO", f"  Total Quantity: {self.stats.total_quantity}")
        self.log("INFO", f"  Filled: {self.stats.total_filled}")
        self.log("INFO", f"  Fill Rate: {self.stats.total_filled/self.stats.total_quantity*100:.2f}%")
        self.log("INFO", f"  Slices: {self.stats.slices_sent}/{self.stats.total_slices}")
        self.log("INFO", f"  Avg Fill Price: {self.stats.avg_fill_price}")
        self.log("INFO", f"  Duration: {duration_sec:.1f}s")
        self.log("INFO", f"{'='*50}\n")

    def get_stats(self) -> dict:
        """Get current statistics"""
        return {
            'slices': {
                'total': self.num_slices,
                'sent': self.stats.slices_sent,
                'filled': self.stats.slices_filled,
            },
            'quantity': {
                'total': self.stats.total_quantity,
                'filled': self.stats.total_filled,
                'fill_rate': self.stats.total_filled / self.stats.total_quantity * 100
                            if self.stats.total_quantity > 0 else 0,
            },
            'price': {
                'avg_fill': self.stats.avg_fill_price,
                'vwap': self.stats.vwap,
            },
            'is_complete': self.is_complete,
        }


# Convenience function for creating TWAP strategy

def create_twap_strategy(
    strategy_id: str,
    symbol: str,
    side: str,  # 'BUY' or 'SELL'
    total_quantity: float,
    duration_seconds: int = 120,
    num_slices: int = 12,
    order_type: str = 'MARKET'
) -> TWAPStrategy:
    """
    Create a TWAP strategy with standard parameters.

    Args:
        strategy_id: Unique strategy ID
        symbol: Trading symbol
        side: 'BUY' or 'SELL'
        total_quantity: Total quantity to trade
        duration_seconds: Total execution time (default 120s = 2 minutes)
        num_slices: Number of slices (default 12, one every 10s)
        order_type: 'MARKET' or 'LIMIT'

    Returns:
        Configured TWAPStrategy instance
    """
    params = {
        'total_quantity': total_quantity,
        'duration_seconds': duration_seconds,
        'num_slices': num_slices,
        'side': side,
        'order_type': order_type,
    }

    return TWAPStrategy(
        strategy_id=strategy_id,
        symbols=[symbol],
        params=params
    )
