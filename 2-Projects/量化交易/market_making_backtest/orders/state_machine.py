"""
Order State Machine - Manages order lifecycle with state transitions.
Ensures valid state transitions and tracks order history.
"""

from typing import Dict, List, Optional, Callable, Set, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..core.types import Order, OrderStatus, current_timestamp_ns


class OrderStateError(Exception):
    """Raised when an invalid state transition is attempted"""
    pass


# Define valid state transitions as a directed graph
VALID_TRANSITIONS: Dict[OrderStatus, Set[OrderStatus]] = {
    OrderStatus.CREATED: {
        OrderStatus.PENDING,      # Submitted
        OrderStatus.CANCELLED,    # Cancelled before submission
    },
    OrderStatus.PENDING: {
        OrderStatus.ACCEPTED,     # Accepted by exchange
        OrderStatus.REJECTED,     # Rejected by exchange
        OrderStatus.CANCELLING,   # Cancel request sent
    },
    OrderStatus.ACCEPTED: {
        OrderStatus.PARTIALLY_FILLED,  # Some fills
        OrderStatus.FILLED,            # Fully filled
        OrderStatus.CANCELLING,        # Cancel request
        OrderStatus.CANCELLED,         # Cancelled
        OrderStatus.EXPIRED,           # Time limit expired
    },
    OrderStatus.PARTIALLY_FILLED: {
        OrderStatus.FILLED,       # Fully filled
        OrderStatus.CANCELLING,   # Cancel remaining
        OrderStatus.CANCELLED,    # Cancelled
        OrderStatus.EXPIRED,      # Expired
    },
    OrderStatus.CANCELLING: {
        OrderStatus.CANCELLED,    # Successfully cancelled
        OrderStatus.PARTIALLY_FILLED,  # Fill before cancel
        OrderStatus.FILLED,       # Fully filled
    },
    OrderStatus.FILLED: set(),        # Terminal state
    OrderStatus.CANCELLED: set(),     # Terminal state
    OrderStatus.REJECTED: set(),      # Terminal state
    OrderStatus.EXPIRED: set(),       # Terminal state
}


@dataclass
class StateTransition:
    """Record of a state transition"""
    from_status: OrderStatus
    to_status: OrderStatus
    timestamp_ns: int
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class OrderStateMachine:
    """
    State machine for managing order lifecycle.

    Ensures valid state transitions and maintains transition history.
    """

    def __init__(self, order: Order):
        self.order = order
        self._transitions: List[StateTransition] = []
        self._handlers: Dict[OrderStatus, List[Callable]] = {
            status: [] for status in OrderStatus
        }

        # Record initial state
        if self._transitions:
            self._record_transition(
                OrderStatus.CREATED,
                order.status,
                "Initial state"
            )

    # ========== State Queries ==========

    @property
    def current_state(self) -> OrderStatus:
        """Get current order state"""
        return self.order.status

    @property
    def is_terminal(self) -> bool:
        """Check if order is in terminal state"""
        return self.current_state in {
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        }

    @property
    def can_cancel(self) -> bool:
        """Check if order can be cancelled"""
        return self.current_state in {
            OrderStatus.PENDING,
            OrderStatus.ACCEPTED,
            OrderStatus.PARTIALLY_FILLED
        }

    @property
    def can_modify(self) -> bool:
        """Check if order can be modified"""
        return self.can_cancel

    def can_transition_to(self, new_state: OrderStatus) -> bool:
        """Check if transition to new_state is valid"""
        current = self.current_state

        if current == new_state:
            return True  # Already in this state

        valid_next = VALID_TRANSITIONS.get(current, set())
        return new_state in valid_next

    # ========== State Transitions ==========

    def transition_to(
        self,
        new_state: OrderStatus,
        reason: str = "",
        **metadata
    ) -> bool:
        """
        Attempt to transition to a new state.

        Args:
            new_state: Target state
            reason: Reason for transition
            **metadata: Additional metadata

        Returns:
            True if transition was successful

        Raises:
            OrderStateError: If transition is invalid
        """
        if not self.can_transition_to(new_state):
            current = self.current_state
            raise OrderStateError(
                f"Invalid state transition: {current.value} -> {new_state.value}"
            )

        old_state = self.current_state

        # Update order status
        self.order.status = new_state
        self.order.updated_at = current_timestamp_ns()

        # Record transition
        self._record_transition(old_state, new_state, reason, metadata)

        # Execute callbacks
        self._execute_state_callbacks(new_state)

        return True

    def submit(self) -> bool:
        """Submit order (CREATED -> PENDING)"""
        return self.transition_to(OrderStatus.PENDING, "Order submitted")

    def accept(self) -> bool:
        """Accept order (PENDING -> ACCEPTED)"""
        return self.transition_to(OrderStatus.ACCEPTED, "Order accepted")

    def reject(self, reason: str = "") -> bool:
        """Reject order (PENDING -> REJECTED)"""
        return self.transition_to(OrderStatus.REJECTED, f"Order rejected: {reason}")

    def fill(self, filled_qty: Decimal, fill_price: Decimal) -> bool:
        """
        Record a fill on this order.

        Args:
            filled_qty: Quantity filled in this event
            fill_price: Price at which filled
        """
        # Update order fill data
        self.order.filled_quantity += filled_qty

        if self.order.avg_price is None:
            self.order.avg_price = fill_price
        else:
            # VWAP calculation
            total_cost = (
                self.order.avg_price * (self.order.filled_quantity - filled_qty) +
                fill_price * filled_qty
            )
            self.order.avg_price = total_cost / self.order.filled_quantity

        # Determine new status
        if self.order.filled_quantity >= self.order.request.quantity:
            new_status = OrderStatus.FILLED
        else:
            new_status = OrderStatus.PARTIALLY_FILLED

        # Transition to new status
        return self.transition_to(
            new_status,
            f"Filled {filled_qty} @ {fill_price}",
            fill_qty=float(filled_qty),
            fill_price=float(fill_price)
        )

    def cancel(self) -> bool:
        """Request cancellation (ACCEPTED/PARTIALLY_FILLED -> CANCELLED)"""
        if self.can_cancel:
            return self.transition_to(OrderStatus.CANCELLING, "Cancel requested")
        return False

    def confirm_cancel(self) -> bool:
        """Confirm cancellation (CANCELLING -> CANCELLED)"""
        return self.transition_to(OrderStatus.CANCELLED, "Cancel confirmed")

    def expire(self) -> bool:
        """Expire order (ACCEPTED/PARTIALLY_FILLED -> EXPIRED)"""
        return self.transition_to(OrderStatus.EXPIRED, "Order expired")

    # ========== Callbacks ==========

    def on_state(self, state: OrderStatus, callback: Callable[['OrderStateMachine'], None]):
        """Register callback for specific state"""
        self._handlers[state].append(callback)

    def _execute_state_callbacks(self, state: OrderStatus) -> None:
        """Execute callbacks for a state"""
        for callback in self._handlers[state]:
            try:
                callback(self)
            except Exception as e:
                print(f"State callback error: {e}")

    # ========== History ==========

    def _record_transition(
        self,
        from_state: OrderStatus,
        to_state: OrderStatus,
        reason: str,
        metadata: dict
    ) -> None:
        """Record a state transition"""
        transition = StateTransition(
            from_status=from_state,
            to_status=to_state,
            timestamp_ns=current_timestamp_ns(),
            reason=reason,
            metadata=metadata
        )
        self._transitions.append(transition)

    def get_transitions(self) -> List[StateTransition]:
        """Get all state transitions"""
        return self._transitions.copy()

    def time_in_state(self, state: OrderStatus) -> float:
        """Get total time spent in a state (seconds)"""
        total_ns = 0
        current_start = None

        for t in self._transitions:
            if t.from_status == state and current_start is None:
                current_start = t.timestamp_ns
            elif t.to_status == state and current_start is not None:
                total_ns += t.timestamp_ns - current_start
                current_start = None

        # Handle case where we're currently in the state
        if current_start is not None and self.current_state == state:
            total_ns += current_timestamp_ns() - current_start

        return total_ns / 1e9

    def __repr__(self) -> str:
        return f"OrderStateMachine(order_id={self.order.order_id}, state={self.current_state.value}, fills={len(self._transitions)})"
