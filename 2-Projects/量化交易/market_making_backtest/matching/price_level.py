"""
Price Level - Represents a single price level in the order book.
Maintains time-priority queue of orders.
"""

from typing import Dict, List, Optional, Iterator, Callable
from decimal import Decimal
from dataclasses import dataclass, field
from collections import deque
import time

from ..core.types import Order, Side, OrderStatus


@dataclass
class QueuedOrder:
    """Order with queue metadata"""
    order: Order
    queue_position: int          # Position in queue (0 = first)
    arrival_time_ns: int         # Arrival timestamp
    visible_quantity: Decimal    # Visible quantity (may differ from order)


class PriceLevel:
    """
    A single price level in the order book.
    Maintains time-priority queue for FIFO matching.
    """

    def __init__(self, price: Decimal, side: Side):
        self.price = price
        self.side = side

        # Time-priority queue (earliest first)
        self._orders: Dict[str, QueuedOrder] = {}
        self._queue: deque = deque()  # order_ids in arrival order

        # Aggregated quantities
        self.total_quantity = Decimal('0')
        self.visible_quantity = Decimal('0')
        self.hidden_quantity = Decimal('0')

        # Statistics
        self.arrival_count = 0
        self.match_count = 0
        self.cancel_count = 0

    # ========== Order Management ==========

    def add_order(self, order: Order, arrival_time_ns: Optional[int] = None) -> int:
        """
        Add an order to this price level.

        Returns:
            Queue position (0 = first in queue)
        """
        if order.order_id in self._orders:
            raise ValueError(f"Order {order.order_id} already exists at price level")

        if arrival_time_ns is None:
            arrival_time_ns = time.time_ns()

        # Determine visible quantity
        visible_qty = order.remaining_quantity

        # Create queued order
        queued = QueuedOrder(
            order=order,
            queue_position=len(self._queue),
            arrival_time_ns=arrival_time_ns,
            visible_quantity=visible_qty
        )

        # Add to structures
        self._orders[order.order_id] = queued
        self._queue.append(order.order_id)

        # Update aggregates
        self.total_quantity += order.remaining_quantity
        self.visible_quantity += visible_qty

        # Update queue positions
        self._update_queue_positions()

        self.arrival_count += 1

        return queued.queue_position

    def remove_order(self, order_id: str) -> Optional[Order]:
        """
        Remove an order from this price level (e.g., on cancel).

        Returns:
            The removed order, or None if not found
        """
        if order_id not in self._orders:
            return None

        queued = self._orders.pop(order_id)

        # Remove from queue
        try:
            self._queue.remove(order_id)
        except ValueError:
            pass

        # Update aggregates
        self.total_quantity -= queued.order.remaining_quantity
        self.visible_quantity -= queued.visible_quantity

        # Update queue positions
        self._update_queue_positions()

        self.cancel_count += 1

        return queued.order

    def reduce_order(self, order_id: str, reduction: Decimal) -> bool:
        """
        Reduce the quantity of an order (e.g., on partial fill).

        Args:
            order_id: Order to reduce
            reduction: Amount to reduce by

        Returns:
            True if successful
        """
        if order_id not in self._orders:
            return False

        queued = self._orders[order_id]

        # Update order
        queued.order.filled_quantity += reduction

        # Update aggregates
        self.total_quantity -= reduction
        # Note: visible_quantity may need separate logic for iceberg orders

        return True

    # ========== Matching ==========

    def match_against(self, quantity: Decimal, aggressive_side: Side) -> tuple:
        """
        Match an incoming order against this price level.

        Args:
            quantity: Quantity to match
            aggressive_side: Side of the aggressive order

        Returns:
            Tuple of (fills: list, remaining_quantity: Decimal)
            where fills is list of (order_id, filled_qty, price)
        """
        fills = []
        remaining = quantity

        # Determine match direction
        if aggressive_side == Side.BUY:
            # Buy order hits ask levels
            match_side = Side.SELL
        else:
            match_side = Side.BUY

        # Iterate through queue (time priority)
        for order_id in list(self._queue):
            if remaining <= 0:
                break

            if order_id not in self._orders:
                continue

            queued = self._orders[order_id]

            # Calculate fill quantity
            available = queued.order.remaining_quantity
            fill_qty = min(remaining, available)

            if fill_qty <= 0:
                continue

            # Record fill
            fills.append((
                order_id,
                fill_qty,
                self.price,
                queued.order
            ))

            remaining -= fill_qty

            self.match_count += 1

        return fills, remaining

    def is_empty(self) -> bool:
        """Check if price level has no orders"""
        return len(self._orders) == 0

    @property
    def order_count(self) -> int:
        """Number of orders at this price level"""
        return len(self._orders)

    # ========== Internal Helpers ==========

    def _update_queue_positions(self) -> None:
        """Update queue positions for all orders"""
        for i, order_id in enumerate(self._queue):
            if order_id in self._orders:
                self._orders[order_id].queue_position = i

    # ========== Iteration ==========

    def __iter__(self) -> iter:
        """Iterate over orders in time-priority order"""
        for order_id in self._queue:
            if order_id in self._orders:
                yield self._orders[order_id].order

    def __repr__(self) -> str:
        return f"PriceLevel(price={self.price}, side={self.side.value}, qty={self.total_quantity}, orders={self.order_count})"
